"""
fix_missing_events.py
─────────────────────
Percorre todos os agendamentos ATIVOS que estão sem event_id no Google Calendar
e cria os eventos retroativamente.

Status considerados ativos (devem ter evento no Calendar):
  scheduled, day_reminder_sent, reminder_sent, response_received, confirmed

Uso:
  python fix_missing_events.py           → modo real (cria eventos)
  python fix_missing_events.py --dry-run → só exibe o que seria feito
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from appointments import load as load_appointments
from calendar_service import create_event
import db

ACTIVE_STATUSES = {
    "scheduled",
    "day_reminder_sent",
    "reminder_sent",
    "response_received",
    "confirmed",
}

DRY_RUN = "--dry-run" in sys.argv


def fix_missing_events():
    appointments = load_appointments()

    targets = [
        a for a in appointments
        if a.get("status") in ACTIVE_STATUSES
        and not a.get("event_id")
    ]

    print(f"{'[DRY-RUN] ' if DRY_RUN else ''}Agendamentos ativos sem event_id: {len(targets)}")

    if not targets:
        print("Nenhum agendamento para corrigir. Tudo certo!")
        return

    created = 0
    failed  = 0

    for apt in targets:
        name  = apt["name"]
        date  = apt["date"]
        time  = apt["time"]
        phone = apt["phone"]

        label = f"  {name} — {date} {time} ({apt['status']})"

        if DRY_RUN:
            print(f"[SERIA CRIADO] {label}")
            continue

        try:
            event_id = create_event(name, date, time, phone)
            db.execute(
                "UPDATE appointments SET event_id = %s WHERE phone = %s AND date = %s AND time = %s",
                (event_id, phone, date, time),
            )
            print(f"  ✓ CRIADO    {label}  →  event_id: {event_id[:20]}...")
            created += 1
        except Exception as e:
            print(f"  ✗ FALHOU    {label}  →  {e}")
            failed += 1

    if not DRY_RUN:
        print(f"\nResumo: {created} criado(s) | {failed} falhou(ram).")


if __name__ == "__main__":
    fix_missing_events()
