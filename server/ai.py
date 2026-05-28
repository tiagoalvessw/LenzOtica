from groq import Groq, RateLimitError, APIStatusError
from dotenv import load_dotenv
import os
import re
import sys
import time
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import session
import context
import rag

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
print("[AI] Modo PRODUÇÃO — usando Groq")

session.load()

# Modelos em ordem de preferência; cada um tem cota independente no Groq.
# Se o principal atingir rate limit, o bot tenta os seguintes automaticamente.
_MODELS = [
    "llama-3.3-70b-versatile",   # principal — melhor qualidade
    "llama-3.1-8b-instant",      # fallback — cota separada e maior RPM
]

# Compatibilidade com main.py (sem alterar imports lá)
def is_new_sender(phone: str) -> bool:
    return session.is_new_sender(phone)


def has_empty_session(phone: str) -> bool:
    return session.has_empty_session(phone)


def reset_session(phone: str) -> None:
    session.reset_session(phone)


def inject_assistant_message(phone: str, message: str) -> None:
    session.inject_assistant_message(phone, message)


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _trim_history(history: list, system_tokens: int, max_total: int = 2500) -> list:
    budget = max_total - system_tokens
    if budget <= 0:
        return history[-2:] if len(history) >= 2 else history
    total = sum(_count_tokens(m["content"]) for m in history)
    while total > budget and len(history) > 2:
        removed = history.pop(0)
        total -= _count_tokens(removed["content"])
        if history and history[0]["role"] == "assistant":
            removed = history.pop(0)
            total -= _count_tokens(removed["content"])
    return history


def _extract_retry_seconds(err_str: str) -> int:
    """Extrai segundos de espera da mensagem de rate limit do Groq."""
    m = re.search(r'try again in ([\d]+)m([\d\.]+)s', err_str, re.I)
    if m:
        return int(m.group(1)) * 60 + int(float(m.group(2))) + 1
    m = re.search(r'try again in ([\d\.]+)s', err_str, re.I)
    if m:
        return int(float(m.group(1))) + 1
    m = re.search(r'try again in ([\d]+)\s*hour', err_str, re.I)
    if m:
        return int(m.group(1)) * 3600
    return 0


def _format_retry_txt(err_str: str) -> str:
    secs = _extract_retry_seconds(err_str)
    if secs >= 3600:
        h = secs // 3600
        return f"{h} hora{'s' if h > 1 else ''}"
    if secs >= 60:
        mins = (secs // 60) + 1
        return f"{mins} minutos"
    if secs > 0:
        return f"{secs} segundos"
    return "alguns minutos"


def get_response(sender: str, message: str) -> str:
    session.push(sender, "user", message)

    system_prompt = context.get_system_prompt()
    dynamic_ctx = context.build_dynamic_context(sender)
    system_ctx = system_prompt + dynamic_ctx

    rag_chunks = rag.retrieve(message, sender)
    if rag_chunks:
        rag_block = "\n\n[Conhecimento relevante]\n" + "\n---\n".join(rag_chunks)
        system_ctx += rag_block

    system_tokens = _count_tokens(system_ctx)
    print(f"[AI] Tokens estimados do system prompt: {system_tokens}")

    session.sessions[sender] = _trim_history(
        session.sessions[sender], system_tokens
    )

    response = None
    last_error = None
    used_model = None

    for model in _MODELS:
        # Tenta o modelo com até 1 retry após rate limit de curta duração
        for attempt in range(2):
            try:
                print(f"[AI] Tentando modelo: {model} (tentativa {attempt + 1})")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_ctx}]
                    + [{"role": m["role"], "content": m["content"]} for m in session.sessions[sender]],
                    temperature=0.3,
                    max_tokens=320,
                )
                used_model = model
                print(f"[AI] Sucesso com modelo: {model}")
                break
            except RateLimitError as e:
                last_error = e
                print(f"[GROQ RATE LIMIT] {model}: {e}")
                wait = _extract_retry_seconds(str(e))
                # Só faz retry automático se o tempo de espera for curto (≤ 8 s)
                if attempt == 0 and 0 < wait <= 8:
                    print(f"[AI] Aguardando {wait}s antes de retry no mesmo modelo...")
                    time.sleep(wait)
                    continue
                break  # rate limit longo → tenta próximo modelo
            except APIStatusError as e:
                print(f"[GROQ API ERROR] {model}: {e}")
                last_error = e
                break
            except Exception as e:
                print(f"[AI ERROR] {model}: {e}")
                last_error = e
                break  # erro inesperado → não tenta outros modelos

        if response is not None:
            break

    if response and response.usage:
        print(
            f"[AI] Modelo={used_model} | Tokens — "
            f"prompt: {response.usage.prompt_tokens} | "
            f"resposta: {response.usage.completion_tokens} | "
            f"total: {response.usage.total_tokens}"
        )

    if response is None:
        session.pop_last(sender)
        session.save()

        if isinstance(last_error, RateLimitError):
            retry_txt = _format_retry_txt(str(last_error))
            print(f"[RATE LIMIT] Todos modelos esgotados. Retry: {retry_txt}")
            return (
                "Um momento, por favor."
                f"[PENDENTE:Rate limit Groq — todos modelos atingiram o limite. "
                f"Retry estimado: {retry_txt}. Verificar console.groq.com.]"
            )

        error_info = f"{type(last_error).__name__}: {last_error}"
        print(f"[AI FALHOU] {error_info}")
        return f"Um momento, por favor.[PENDENTE:Erro no modelo de IA — {error_info}]"

    reply = response.choices[0].message.content

    reply_for_history = re.sub(r'\[AGENDAR:[^\]]*\]|\[PENDENTE:[^\]]*\]', "", reply)
    reply_for_history = reply_for_history.replace("[BREAK]", " ")
    reply_for_history = re.sub(r'\s{2,}', " ", reply_for_history).strip()

    session.push(sender, "assistant", reply_for_history)
    session.save()
    return reply
