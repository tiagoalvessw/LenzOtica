"""Remove do Google Calendar todos os eventos do bot que NÃO estejam referenciados
no painel (appointments.json com status != 'archived')."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from calendar_service import _get_service
from appointments import load as load_appointments


ACTIVE_STATUSES = {
    "scheduled", "day_reminder_sent", "reminder_sent",
    "response_received", "confirmed",
}


def sync_calendar():
    # Coleta event_ids válidos — apenas consultas ativas (não realizadas/canceladas)
    appointments = load_appointments()
    valid_ids = {
        a["event_id"]
        for a in appointments
        if a.get("status") in ACTIVE_STATUSES and a.get("event_id")
    }
    print(f"Event IDs válidos no painel: {len(valid_ids)}")

    service = _get_service()
    deleted = kept = skipped = 0
    page_token = None

    while True:
        kwargs = {
            "calendarId": "primary",
            "maxResults": 250,
            "singleEvents": True,
            "q": "Agendado via WhatsApp",
        }
        if page_token:
            kwargs["pageToken"] = page_token

        result = service.events().list(**kwargs).execute()
        items = result.get("items", [])

        for event in items:
            desc = event.get("description", "")
            if "Agendado via WhatsApp" not in desc:
                skipped += 1
                continue

            event_id = event["id"]
            summary = event.get("summary", "")
            start = event.get("start", {}).get("dateTime", "")

            if event_id in valid_ids:
                print(f"  MANTIDO : {summary} — {start}")
                kept += 1
            else:
                service.events().delete(calendarId="primary", eventId=event_id).execute()
                print(f"  REMOVIDO: {summary} — {start}")
                deleted += 1

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    print(f"\nResumo: {kept} mantido(s) | {deleted} removido(s) | {skipped} ignorado(s).")


if __name__ == "__main__":
    sync_calendar()
