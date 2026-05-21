"""Script único para apagar todos os eventos criados pelo bot (descrição contém 'Agendado via WhatsApp')."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from calendar_service import _get_service

def clear_bot_events():
    service = _get_service()
    deleted = 0
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
            if "Agendado via WhatsApp" in desc:
                service.events().delete(calendarId="primary", eventId=event["id"]).execute()
                print(f"Removido: {event.get('summary')} — {event.get('start', {}).get('dateTime', '')}")
                deleted += 1

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    print(f"\nTotal removido: {deleted} evento(s).")

if __name__ == "__main__":
    clear_bot_events()
