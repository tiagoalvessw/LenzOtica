import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import db

sessions: dict = {}
_dirty: set = set()


def load() -> None:
    global sessions
    rows = db.fetchall(
        "SELECT phone, role, content FROM conversation_history ORDER BY phone, created_at ASC"
    )
    sessions = {}
    for row in rows:
        sessions.setdefault(row["phone"], []).append(
            {"role": row["role"], "content": row["content"]}
        )


def save() -> None:
    for phone in list(_dirty):
        messages = sessions.get(phone, [])
        db.execute("DELETE FROM conversation_history WHERE phone = %s", (phone,))
        for msg in messages:
            db.execute(
                "INSERT INTO conversation_history (phone, role, content, token_count) VALUES (%s,%s,%s,%s)",
                (phone, msg["role"], msg["content"], max(1, len(msg["content"]) // 4)),
            )
    _dirty.clear()


def is_new_sender(phone: str) -> bool:
    return phone not in sessions


def has_empty_session(phone: str) -> bool:
    return phone not in sessions or not sessions[phone]


def get_history(phone: str) -> list:
    return sessions.get(phone, [])


def push(phone: str, role: str, content: str) -> None:
    sessions.setdefault(phone, [])
    sessions[phone].append({"role": role, "content": content})
    _dirty.add(phone)


def pop_last(phone: str) -> None:
    if phone in sessions and sessions[phone]:
        msg = sessions[phone].pop()
        _dirty.add(phone)
        return msg


def reset_session(phone: str) -> None:
    sessions.pop(phone, None)
    _dirty.discard(phone)
    db.execute("DELETE FROM conversation_history WHERE phone = %s", (phone,))


def inject_assistant_message(phone: str, content: str) -> None:
    push(phone, "assistant", content)
    save()
