from datetime import datetime
import db


def _row(row: dict) -> dict:
    if row is None:
        return None
    r = dict(row)
    r["date"] = str(r["date"])        # date  → "YYYY-MM-DD"
    r["time"] = str(r["time"])[:5]    # time  → "HH:MM"
    for f in ("created_at", "confirmed_at", "attended_at", "completed_at", "archived_at"):
        if r.get(f) is not None:
            r[f] = r[f].isoformat()
    return r


def load() -> list[dict]:
    return [_row(r) for r in db.fetchall("SELECT * FROM appointments ORDER BY date, time")]


def save(data: list[dict]) -> None:
    for apt in data:
        if "id" not in apt:
            continue
        db.execute(
            """
            UPDATE appointments SET
                phone = %s, name = %s, date = %s, time = %s,
                status = %s, event_id = %s, notes = %s,
                confirmed_at = %s, attended_at = %s, completed_at = %s, archived_at = %s
            WHERE id = %s
            """,
            (
                apt["phone"], apt["name"], apt["date"], apt["time"],
                apt["status"], apt.get("event_id", ""), apt.get("notes", ""),
                apt.get("confirmed_at"), apt.get("attended_at"),
                apt.get("completed_at"), apt.get("archived_at"),
                apt["id"],
            ),
        )


def add_appointment(phone: str, name: str, date_str: str, time_str: str, event_id: str = "") -> None:
    db.execute(
        "INSERT INTO appointments (phone, name, date, time, status, event_id) VALUES (%s, %s, %s, %s, 'scheduled', %s)",
        (phone, name, date_str, time_str, event_id),
    )


def get_appointments_for_day_reminder() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT * FROM appointments
        WHERE status = 'scheduled'
          AND (date + time)::timestamp
              BETWEEN (now() + interval '22 hours 55 minutes')::timestamp
                  AND (now() + interval '24 hours 5 minutes')::timestamp
        """
    )
    return [_row(r) for r in rows]


def mark_day_reminder_sent(phone: str, date_str: str, time_str: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'day_reminder_sent' WHERE phone = %s AND date = %s AND time = %s AND status = 'scheduled'",
        (phone, date_str, time_str),
    )


def get_appointments_for_reminder() -> list[dict]:
    rows = db.fetchall(
        """
        SELECT * FROM appointments
        WHERE status IN ('scheduled', 'day_reminder_sent')
          AND (date + time)::timestamp
              BETWEEN (now() + interval '55 minutes')::timestamp
                  AND (now() + interval '65 minutes')::timestamp
        """
    )
    return [_row(r) for r in rows]


def mark_reminder_sent(phone: str, date_str: str, time_str: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'reminder_sent' WHERE phone = %s AND date = %s AND time = %s AND status IN ('scheduled', 'day_reminder_sent')",
        (phone, date_str, time_str),
    )


def get_appointments_to_cancel() -> list[dict]:
    rows = db.fetchall(
        "SELECT * FROM appointments WHERE status = 'reminder_sent' AND (date + time)::timestamp <= now()::timestamp"
    )
    return [_row(r) for r in rows]


def mark_response_received(phone: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'response_received' WHERE phone = %s AND status = 'reminder_sent'",
        (phone,),
    )


def cancel_appointment(phone: str, date_str: str, time_str: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'cancelled' WHERE phone = %s AND date = %s AND time = %s",
        (phone, date_str, time_str),
    )


def has_pending_reminder(phone: str) -> bool:
    return (db.fetchval("SELECT count(*) FROM appointments WHERE phone = %s AND status = 'reminder_sent'", (phone,)) or 0) > 0


def confirm_appointment(phone: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'confirmed', confirmed_at = now() WHERE phone = %s AND status = 'reminder_sent'",
        (phone,),
    )


def cancel_pending_reminders(phone: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'cancelled' WHERE phone = %s AND status = 'reminder_sent'",
        (phone,),
    )


def mark_confirmed_at(phone: str) -> None:
    db.execute(
        "UPDATE appointments SET confirmed_at = now() WHERE phone = %s AND status = 'confirmed' AND confirmed_at IS NULL",
        (phone,),
    )


def mark_attended(phone: str, date_str: str, time_str: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'attended', attended_at = now() WHERE phone = %s AND date = %s AND time = %s AND status = 'confirmed'",
        (phone, date_str, time_str),
    )


def mark_completed(phone: str, date_str: str, time_str: str, notes: str = "") -> None:
    db.execute(
        "UPDATE appointments SET status = 'completed', completed_at = now(), notes = %s WHERE phone = %s AND date = %s AND time = %s AND status = 'attended'",
        (notes, phone, date_str, time_str),
    )


def mark_no_show(phone: str, date_str: str, time_str: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'no_show' WHERE phone = %s AND date = %s AND time = %s AND status = 'confirmed'",
        (phone, date_str, time_str),
    )


def get_appointments_for_no_show() -> list[dict]:
    rows = db.fetchall(
        "SELECT * FROM appointments WHERE status = 'confirmed' AND (date + time)::timestamp <= (now() - interval '30 minutes')::timestamp"
    )
    return [_row(r) for r in rows]


def reschedule_no_show(phone: str, date_str: str, time_str: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'scheduled', attended_at = NULL, completed_at = NULL, notes = '' WHERE phone = %s AND date = %s AND time = %s AND status = 'no_show'",
        (phone, date_str, time_str),
    )


def archive_appointment(phone: str, date_str: str, time_str: str) -> None:
    db.execute(
        "UPDATE appointments SET status = 'archived', archived_at = now() WHERE phone = %s AND date = %s AND time = %s AND status IN ('completed', 'cancelled', 'no_show', 'attended', 'confirmed')",
        (phone, date_str, time_str),
    )
