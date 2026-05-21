import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
BASE_DIR = os.path.dirname(__file__)
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


def _get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def create_event(name: str, date_str: str, time_str: str, phone: str = "") -> str:
    service = _get_service()

    start_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    end_dt = start_dt + timedelta(minutes=30)

    phone_clean = phone.replace("@s.whatsapp.net", "").replace("@lid", "")

    event = {
        "summary": f"Consulta — {name}",
        "location": "Rua Vereador Arthur Manoel Mariano, 362, Forquilhinhas, São José - SC",
        "description": f"Agendado via WhatsApp\nTelefone: {phone_clean}" if phone_clean else "Agendado via WhatsApp",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "America/Sao_Paulo"},
    }

    created = service.events().insert(calendarId="primary", body=event).execute()
    print(f"[CALENDAR] Evento criado: {created.get('htmlLink')}")
    return created.get("id", "")


def cancel_event(event_id: str):
    if not event_id:
        return
    service = _get_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    print(f"[CALENDAR] Evento removido: {event_id}")
