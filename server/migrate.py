"""
Migração única: appointments.json + sessions.json + pending.json → PostgreSQL.
Execute uma vez: python migrate.py
Registros já existentes no banco são ignorados (idempotente).
"""
import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")
DIR = os.path.dirname(__file__)


# ---------------------------------------------------------------------------
# appointments
# ---------------------------------------------------------------------------

def migrate_appointments(conn):
    path = os.path.join(DIR, "appointments.json")
    if not os.path.exists(path):
        print("[appointments] arquivo não encontrado, pulando.")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("[appointments] vazio.")
        return

    inserted = skipped = 0
    for apt in data:
        exists = conn.execute(
            "SELECT 1 FROM appointments WHERE phone = %s AND date = %s AND time = %s",
            (apt["phone"], apt["date"], apt["time"]),
        ).fetchone()
        if exists:
            skipped += 1
            continue

        conn.execute(
            """
            INSERT INTO appointments
                (phone, name, date, time, status, event_id, notes,
                 created_at, confirmed_at, attended_at, completed_at, archived_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                apt["phone"],
                apt["name"],
                apt["date"],
                apt["time"],
                apt["status"],
                apt.get("event_id", ""),
                apt.get("notes", ""),
                apt.get("created_at"),
                apt.get("confirmed_at"),
                apt.get("attended_at"),
                apt.get("completed_at"),
                apt.get("archived_at"),
            ),
        )
        inserted += 1

    conn.commit()
    print(f"[appointments] {inserted} inseridos, {skipped} já existiam.")


# ---------------------------------------------------------------------------
# sessions → conversation_history
# ---------------------------------------------------------------------------

def migrate_sessions(conn):
    path = os.path.join(DIR, "sessions.json")
    if not os.path.exists(path):
        print("[sessions] arquivo não encontrado, pulando.")
        return

    with open(path, encoding="utf-8") as f:
        sessions = json.load(f)

    if not sessions:
        print("[sessions] vazio.")
        return

    total = skipped = 0
    for phone, messages in sessions.items():
        existing = conn.execute(
            "SELECT count(*) FROM conversation_history WHERE phone = %s",
            (phone,),
        ).fetchone()[0]
        if existing:
            print(f"  [sessions] {phone}: {existing} msgs já no banco, pulando.")
            skipped += len(messages)
            continue

        # timestamps sintéticos — 1 min de intervalo, terminando agora
        base = datetime.now() - timedelta(minutes=len(messages))
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            conn.execute(
                """
                INSERT INTO conversation_history (phone, role, content, token_count, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (phone, msg["role"], content, max(1, len(content) // 4), base + timedelta(minutes=i)),
            )
            total += 1

    conn.commit()
    print(f"[sessions] {total} mensagens inseridas, {skipped} puladas.")


# ---------------------------------------------------------------------------
# pending
# ---------------------------------------------------------------------------

def migrate_pending(conn):
    path = os.path.join(DIR, "pending.json")
    if not os.path.exists(path):
        print("[pending] arquivo não encontrado, pulando.")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("[pending] vazio.")
        return

    inserted = 0
    for item in data:
        conn.execute(
            """
            INSERT INTO pending_items (phone, description, dismissed, created_at)
            VALUES (%s, %s, false, %s)
            """,
            (
                item["phone"],
                item.get("note", item.get("description", "")),
                item.get("created_at"),
            ),
        )
        inserted += 1

    conn.commit()
    print(f"[pending] {inserted} inseridos.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Conectando em: {DATABASE_URL}\n")
    with psycopg.connect(DATABASE_URL) as conn:
        migrate_appointments(conn)
        migrate_sessions(conn)
        migrate_pending(conn)
    print("\nMigração concluída.")
