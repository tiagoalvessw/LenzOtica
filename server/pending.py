import db


def load() -> list[dict]:
    rows = db.fetchall(
        "SELECT id, phone, description, created_at FROM pending_items WHERE dismissed = false ORDER BY created_at DESC"
    )
    return [
        {
            "id": str(row["id"]),
            "phone": row["phone"],
            "note": row["description"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


def add_pending(phone: str, note: str) -> None:
    db.execute(
        "INSERT INTO pending_items (phone, description) VALUES (%s, %s)",
        (phone, note),
    )


def dismiss_pending(item_id: str) -> None:
    db.execute(
        "UPDATE pending_items SET dismissed = true, dismissed_at = now() WHERE id = %s",
        (int(item_id),),
    )
