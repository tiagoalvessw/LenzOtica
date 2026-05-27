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

    MODELS = ["llama-3.3-70b-versatile"]

    response = None
    last_error = None
    for model in MODELS:
        try:
            print(f"[AI] Tentando modelo: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_ctx}]
                + session.sessions[sender],
                temperature=0.3,
                max_tokens=280,
            )
            print(f"[AI] Sucesso com modelo: {model}")
            break
        except RateLimitError as e:
            print(f"[GROQ RATE LIMIT] {model}: {e}")
            last_error = e
            continue
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
            f"[AI] Tokens reais — prompt: {response.usage.prompt_tokens} | "
            f"resposta: {response.usage.completion_tokens} | "
            f"total: {response.usage.total_tokens}"
        )

    if response is None:
        error_info = f"{type(last_error).__name__}: {last_error}"
        session.pop_last(sender)
        session.save()
        return f"Um momento, por favor.[PENDENTE:Todos os modelos falharam — {error_info}]"

    reply = response.choices[0].message.content

    reply_for_history = re.sub(r'\[AGENDAR:[^\]]*\]|\[PENDENTE:[^\]]*\]', "", reply)
    reply_for_history = reply_for_history.replace("[BREAK]", " ")
    reply_for_history = re.sub(r'\s{2,}', " ", reply_for_history).strip()

    session.push(sender, "assistant", reply_for_history)
    session.save()
    return reply
