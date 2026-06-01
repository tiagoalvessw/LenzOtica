import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import db

sessions: dict = {}
_dirty: set = set()
_pending_slots: dict = {}   # {phone: {"date": "AAAA-MM-DD", "time": "HH:MM"}}
_offered_slots: dict = {}   # {phone: {"HH:MM": "AAAA-MM-DD", ...}} — slots exibidos ao cliente


def load() -> None:
    global sessions
    rows = db.fetchall(
        "SELECT phone, role, content, COALESCE(sent_by_operator, FALSE) as sent_by_operator"
        " FROM conversation_history ORDER BY phone, created_at ASC"
    )
    sessions = {}
    for row in rows:
        sessions.setdefault(row["phone"], []).append(
            {"role": row["role"], "content": row["content"],
             "sent_by_operator": bool(row.get("sent_by_operator", False))}
        )


def save() -> None:
    for phone in list(_dirty):
        messages = sessions.get(phone, [])
        db.execute("DELETE FROM conversation_history WHERE phone = %s", (phone,))
        for msg in messages:
            db.execute(
                "INSERT INTO conversation_history (phone, role, content, token_count, sent_by_operator)"
                " VALUES (%s,%s,%s,%s,%s)",
                (phone, msg["role"], msg["content"],
                 max(1, len(msg["content"]) // 4),
                 bool(msg.get("sent_by_operator", False))),
            )
    _dirty.clear()


def is_new_sender(phone: str) -> bool:
    return phone not in sessions


def has_empty_session(phone: str) -> bool:
    return phone not in sessions or not sessions[phone]


def get_history(phone: str) -> list:
    return sessions.get(phone, [])


def push(phone: str, role: str, content: str, sent_by_operator: bool = False) -> None:
    sessions.setdefault(phone, [])
    sessions[phone].append({"role": role, "content": content, "sent_by_operator": sent_by_operator})
    _dirty.add(phone)


def pop_last(phone: str) -> None:
    if phone in sessions and sessions[phone]:
        msg = sessions[phone].pop()
        _dirty.add(phone)
        return msg


def set_pending_slot(phone: str, date: str, time: str) -> None:
    _pending_slots[phone] = {"date": date, "time": time}


def get_pending_slot(phone: str):
    return _pending_slots.get(phone)


def clear_pending_slot(phone: str) -> None:
    _pending_slots.pop(phone, None)


def set_offered_slots(phone: str, slots: dict) -> None:
    _offered_slots[phone] = slots


def get_offered_slots(phone: str) -> dict:
    return _offered_slots.get(phone, {})


def reset_session(phone: str) -> None:
    sessions.pop(phone, None)
    _pending_slots.pop(phone, None)
    _offered_slots.pop(phone, None)
    _dirty.discard(phone)
    db.execute("DELETE FROM conversation_history WHERE phone = %s", (phone,))


def inject_assistant_message(phone: str, content: str) -> None:
    push(phone, "assistant", content)
    save()
