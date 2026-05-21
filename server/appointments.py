import json
import os
from datetime import datetime

APPOINTMENTS_FILE = os.path.join(os.path.dirname(__file__), "appointments.json")

def load():
    if not os.path.exists(APPOINTMENTS_FILE):
        return []
    with open(APPOINTMENTS_FILE, encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_appointment(phone: str, name: str, date_str: str, time_str: str, event_id: str = ""):
    data = load()
    data.append({
        "phone": phone,
        "name": name,
        "date": date_str,
        "time": time_str,
        "status": "scheduled",
        "event_id": event_id,
        "created_at": datetime.now().isoformat(),
        "confirmed_at": None,
        "attended_at": None,
        "completed_at": None,
        "notes": "",
    })
    save(data)

def get_appointments_for_day_reminder():
    data = load()
    now = datetime.now()
    result = []
    for apt in data:
        if apt["status"] == "scheduled":
            try:
                apt_dt = datetime.fromisoformat(f"{apt['date']}T{apt['time']}:00")
                diff = (apt_dt - now).total_seconds() / 60
                if 23 * 60 - 5 <= diff <= 24 * 60 + 5:
                    result.append(apt)
            except Exception:
                pass
    return result

def mark_day_reminder_sent(phone: str, date_str: str, time_str: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] == "scheduled":
            apt["status"] = "day_reminder_sent"
    save(data)

def get_appointments_for_reminder():
    data = load()
    now = datetime.now()
    result = []
    for apt in data:
        if apt["status"] in ("scheduled", "day_reminder_sent"):
            try:
                apt_dt = datetime.fromisoformat(f"{apt['date']}T{apt['time']}:00")
                diff = (apt_dt - now).total_seconds() / 60
                if 55 <= diff <= 65:
                    result.append(apt)
            except Exception:
                pass
    return result

def get_appointments_to_cancel():
    data = load()
    now = datetime.now()
    result = []
    for apt in data:
        if apt["status"] == "reminder_sent":
            try:
                apt_dt = datetime.fromisoformat(f"{apt['date']}T{apt['time']}:00")
                if now >= apt_dt:
                    result.append(apt)
            except Exception:
                pass
    return result

def mark_reminder_sent(phone: str, date_str: str, time_str: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] in ("scheduled", "day_reminder_sent"):
            apt["status"] = "reminder_sent"
    save(data)

def mark_response_received(phone: str):
    data = load()
    changed = False
    for apt in data:
        if apt["phone"] == phone and apt["status"] == "reminder_sent":
            apt["status"] = "response_received"
            changed = True
    if changed:
        save(data)

def cancel_appointment(phone: str, date_str: str, time_str: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str:
            apt["status"] = "cancelled"
    save(data)

def has_pending_reminder(phone: str) -> bool:
    data = load()
    return any(apt["phone"] == phone and apt["status"] == "reminder_sent" for apt in data)

def confirm_appointment(phone: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["status"] == "reminder_sent":
            apt["status"] = "confirmed"
    save(data)

def cancel_pending_reminders(phone: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["status"] == "reminder_sent":
            apt["status"] = "cancelled"
    save(data)


def mark_confirmed_at(phone: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["status"] == "confirmed":
            apt.setdefault("confirmed_at", datetime.now().isoformat())
    save(data)


def mark_attended(phone: str, date_str: str, time_str: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] == "confirmed":
            apt["status"] = "attended"
            apt["attended_at"] = datetime.now().isoformat()
    save(data)


def mark_completed(phone: str, date_str: str, time_str: str, notes: str = ""):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] == "attended":
            apt["status"] = "completed"
            apt["completed_at"] = datetime.now().isoformat()
            apt["notes"] = notes
    save(data)


def mark_no_show(phone: str, date_str: str, time_str: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] == "confirmed":
            apt["status"] = "no_show"
    save(data)


def get_appointments_for_no_show():
    """Retorna confirmados cujo horário passou há 30+ minutos sem comparecimento marcado."""
    data = load()
    now = datetime.now()
    result = []
    for apt in data:
        if apt["status"] == "confirmed":
            try:
                apt_dt = datetime.fromisoformat(f"{apt['date']}T{apt['time']}:00")
                if (now - apt_dt).total_seconds() >= 30 * 60:
                    result.append(apt)
            except Exception:
                pass
    return result


def reschedule_no_show(phone: str, date_str: str, time_str: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] == "no_show":
            apt["status"] = "scheduled"
            apt["attended_at"] = None
            apt["completed_at"] = None
            apt["notes"] = ""
    save(data)


def archive_appointment(phone: str, date_str: str, time_str: str):
    data = load()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date_str and apt["time"] == time_str and apt["status"] in ("completed", "cancelled", "no_show", "attended", "confirmed"):
            apt["status"] = "archived"
            apt["archived_at"] = datetime.now().isoformat()
    save(data)
