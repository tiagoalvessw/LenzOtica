from groq import Groq, RateLimitError, APIStatusError
from dotenv import load_dotenv
import os
import re
import sys
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import session
import context
import rag

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
print("[AI] Modo PRODUÇÃO — usando Groq")

session.load()


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


def _trim_history(history: list, system_tokens: int, max_total: int = 3000) -> list:
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


def get_response(sender: str, message: str) -> str:
    session.push(sender, "user", message)

    # Monta contexto completo: prompt do sistema + contexto dinâmico + RAG
    system_prompt = context.get_system_prompt()
    dynamic_ctx = context.build_dynamic_context(sender)
    system_ctx = system_prompt + dynamic_ctx

    rag_chunks = rag.retrieve(message, sender)
    if rag_chunks:
        rag_block = "\n\n[Conhecimento relevante]\n" + "\n---\n".join(rag_chunks)
        system_ctx += rag_block

    system_tokens = _count_tokens(system_ctx)
    print(f"[AI] Tokens estimados do system prompt: {system_tokens}")

    # Trim do histórico dentro do budget de tokens
    session.sessions[sender] = _trim_history(
        session.sessions[sender], system_tokens
    )

    MODELS = [
        "llama-3.3-70b-versatile",
    ]

    response = None
    last_error = None
    used_model = None
    for model in MODELS:
        try:
            print(f"[AI] Tentando modelo: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_ctx}]
                + session.sessions[sender],
                temperature=0.3,
                max_tokens=320,
            )
            used_model = model
            print(f"[AI] Sucesso com modelo: {model}")
            break
        except RateLimitError as e:
            print(f"[GROQ RATE LIMIT] {model}: {e}")
            last_error = e
            continue  # tenta próximo modelo
        except APIStatusError as e:
            print(f"[GROQ API ERROR] {model}: {e}")
            last_error = e
            continue
        except Exception as e:
            print(f"[AI ERROR] {model}: {e}")
            last_error = e
            break

    if response and response.usage:
        print(
            f"[AI] Modelo={used_model} | Tokens — "
            f"prompt: {response.usage.prompt_tokens} | "
            f"resposta: {response.usage.completion_tokens} | "
            f"total: {response.usage.total_tokens}"
        )

    if response is None:
        import re as _re
        session.pop_last(sender)
        session.save()

        # Rate limit: extrai o tempo de retry e dá mensagem útil ao cliente
        if isinstance(last_error, RateLimitError):
            err_str = str(last_error)
            m = _re.search(r'try again in ([\d]+m[\d\.]+s|[\d\.]+s|[\d]+ hour[s]?)', err_str, _re.I)
            raw_retry = m.group(1) if m else None
            # Formata de forma legível: "11m34.656s" → "11 minutos"
            if raw_retry:
                mins_m = _re.match(r'(\d+)m', raw_retry)
                hrs_m  = _re.match(r'(\d+)\s*hour', raw_retry)
                if hrs_m:
                    h = int(hrs_m.group(1))
                    retry_txt = f"{h} hora{'s' if h > 1 else ''}"
                elif mins_m:
                    mins = int(mins_m.group(1))
                    retry_txt = f"{mins + 1} minutos"  # arredonda pra cima
                else:
                    retry_txt = "1 minuto"
            else:
                retry_txt = "alguns minutos"
            print(f"[RATE LIMIT] Todos modelos esgotados. Retry: {retry_txt}")
            return (
                f"Um momento, por favor."
                f"[PENDENTE:Rate limit Groq — todos modelos atingiram o limite. "
                f"Retry estimado: {retry_txt}. Verificar console.groq.com.]"
            )

        # Outro erro
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
