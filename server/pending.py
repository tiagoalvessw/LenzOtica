import json
import os
from datetime import datetime

PENDING_FILE = os.path.join(os.path.dirname(__file__), "pending.json")


def load():
    if not os.path.exists(PENDING_FILE):
        return []
    with open(PENDING_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_pending(phone: str, note: str):
    data = load()
    item_id = datetime.now().isoformat()
    data.append({
        "id": item_id,
        "phone": phone,
        "note": note,
        "created_at": item_id,
    })
    save(data)


def dismiss_pending(item_id: str):
    data = load()
    data = [p for p in data if p.get("id") != item_id]
    save(data)
