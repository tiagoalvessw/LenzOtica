import asyncio
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
import requests
import os
from ai import get_response, inject_assistant_message, is_new_sender, reset_session
from panel import render_panel
from calendar_service import create_event, cancel_event
from appointments import (
    load as load_appointments,
    add_appointment, get_appointments_for_reminder,
    get_appointments_for_day_reminder, mark_day_reminder_sent,
    get_appointments_to_cancel, mark_reminder_sent,
    mark_response_received, cancel_appointment,
    has_pending_reminder, confirm_appointment, cancel_pending_reminders,
    save as save_appointments,
    mark_attended, mark_completed, mark_no_show,
    get_appointments_for_no_show, reschedule_no_show,
    archive_appointment,
)
from pending import add_pending, dismiss_pending, load as load_pending

load_dotenv()

EVOLUTION_URL      = os.getenv("EVOLUTION_API_URL")
EVOLUTION_KEY      = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE")
CALENDAR_EMBED_URL = os.getenv("CALENDAR_EMBED_URL", "")
ADMIN_TOKEN        = os.getenv("ADMIN_TOKEN")

if not ADMIN_TOKEN:
    raise RuntimeError("ADMIN_TOKEN não definido no .env — servidor abortado.")

_api_key_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)

async def verify_token(key: str = Depends(_api_key_header)):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido ou ausente.")

_processed_msgs: dict = {}
_MSG_TTL = 30

def _is_duplicate(msg_id: str) -> bool:
    now = time.time()
    for mid in list(_processed_msgs):
        if now - _processed_msgs[mid] > _MSG_TTL:
            del _processed_msgs[mid]
    if msg_id in _processed_msgs:
        return True
    _processed_msgs[msg_id] = now
    return False

MARKER         = re.compile(r'\[AGENDAR:([^|]+)\|(\d{4}-\d{2}-\d{2})\|(\d{2}:\d{2})\]')
PENDING_MARKER = re.compile(r'\[PENDENTE:([^\]]+)\]')
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

_POSITIVE = {"sim", "s", "confirmo", "confirmado", "vou", "ok", "pode", "presente", "certo", "tá", "ta", "claro"}
_NEGATIVE = {"não", "nao", "n", "cancelar", "reagendar", "remarcar", "não posso", "nao posso"}

def _classify_reminder_response(text: str) -> str:
    normalized = text.lower().strip().rstrip(".")
    if any(w in normalized for w in _NEGATIVE):
        return "cancel"
    if normalized in _POSITIVE or any(w in normalized.split() for w in _POSITIVE):
        return "confirm"
    return "unknown"


def format_date_br(date_str: str) -> str:
    dt = datetime.fromisoformat(date_str)
    return f"{DIAS[dt.weekday()]}, {dt.day:02d}/{dt.month:02d}/{dt.year}"


def send_message(to: str, text: str):
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_KEY}
    payload = {"number": to, "text": text}
    r = requests.post(url, json=payload, headers=headers)
    print(f"[SEND] to={to} status={r.status_code}")


def _typing_delay(text: str) -> float:
    return min(0.4 + len(text) * 0.006, 1.5)


def send_welcome(to: str):
    lisa_intro = "Olá! Sou a Liza, atendente da LenzÓtica. Como posso ajudar você hoje? Qual o seu nome, por favor?"
    send_message(to, lisa_intro)
    inject_assistant_message(to, lisa_intro)


async def check_day_reminders():
    for apt in get_appointments_for_day_reminder():
        phone = apt["phone"]
        name = apt["name"]
        date_br = format_date_br(apt["date"])

        text = (
            f"Olá, {name}! Aqui é a Liza da LenzÓtica 👓\n\n"
            f"Passando para lembrar que *amanhã* você tem consulta marcada para as *{apt['time']}h* ({date_br}).\n\n"
            f"Qualquer dúvida é só nos chamar. Te esperamos!"
        )
        send_message(phone, text)
        inject_assistant_message(phone, text)
        mark_day_reminder_sent(phone, apt["date"], apt["time"])
        print(f"[LEMBRETE 1 DIA] Enviado para {phone}")


async def check_reminders():
    for apt in get_appointments_for_reminder():
        phone = apt["phone"]
        name = apt["name"]
        date_br = format_date_br(apt["date"])

        text = (
            f"Olá, {name}! Aqui é a Liza da LenzÓtica 👓\n\n"
            f"Sua consulta está marcada para *{date_br}* às *{apt['time']}h*.\n\n"
            f"Você confirma sua presença? Responda *SIM* para confirmar ou *NÃO* caso precise reagendar."
        )
        send_message(phone, text)
        inject_assistant_message(phone, text)
        mark_reminder_sent(phone, apt["date"], apt["time"])
        print(f"[LEMBRETE] Enviado para {phone}")


async def check_cancellations():
    for apt in get_appointments_to_cancel():
        phone = apt["phone"]
        name = apt["name"]
        date_br = format_date_br(apt["date"])

        text = (
            f"Olá, {name}. Seu agendamento para *{date_br}* às *{apt['time']}h* "
            f"foi cancelado pois não recebemos confirmação de presença.\n\n"
            f"Deseja reagendar? É só nos enviar uma mensagem 😊"
        )
        send_message(phone, text)
        inject_assistant_message(phone, text)
        cancel_appointment(phone, apt["date"], apt["time"])
        print(f"[CANCELAMENTO] {phone}")


async def check_no_shows():
    for apt in get_appointments_for_no_show():
        try:
            cancel_event(apt.get("event_id", ""))
        except Exception as e:
            print(f"[CALENDAR ERROR] no_show cancel_event: {e}")
        mark_no_show(apt["phone"], apt["date"], apt["time"])
        print(f"[NO-SHOW] {apt['phone']} — {apt['date']} {apt['time']}")


async def scheduler_loop():
    while True:
        try:
            await check_day_reminders()
            await check_reminders()
            await check_cancellations()
            await check_no_shows()
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scheduler_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "imagens", "logo lenzótica.PNG")

@app.get("/painel/logo")
async def painel_logo():
    return FileResponse(_LOGO_PATH, media_type="image/png")

@app.get("/painel", response_class=HTMLResponse)
async def painel():
    from appointments import load
    agendamentos = sorted(
        [a for a in load() if a.get("status") != "archived"],
        key=lambda a: (a["date"], a["time"]),
        reverse=True,
    )
    pending_items = load_pending()
    return render_panel(agendamentos, CALENDAR_EMBED_URL, ADMIN_TOKEN, pending_items)


@app.post("/admin/cancel", dependencies=[Depends(verify_token)])
async def admin_cancel(request: Request):
    body = await request.json()
    phone, date, time = body["phone"], body["date"], body["time"]
    for apt in load_appointments():
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time:
            try:
                cancel_event(apt.get("event_id", ""))
            except Exception as e:
                print(f"[CALENDAR ERROR] {e}")
            break
    cancel_appointment(phone, date, time)
    return {"status": "ok"}


@app.post("/admin/remind", dependencies=[Depends(verify_token)])
async def admin_remind(request: Request):
    body = await request.json()
    phone, date, time = body["phone"], body["date"], body["time"]
    for apt in load_appointments():
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time:
            name    = apt["name"]
            date_br = format_date_br(date)
            text = (
                f"Olá, {name}! Aqui é a Liza da LenzÓtica 👓\n\n"
                f"Sua consulta está marcada para *{date_br}* às *{time}h*.\n\n"
                f"Você confirma sua presença? Responda *SIM* para confirmar ou *NÃO* caso precise reagendar."
            )
            send_message(phone, text)
            inject_assistant_message(phone, text)
            mark_reminder_sent(phone, date, time)
            return {"status": "ok"}
    return {"status": "not_found"}


@app.post("/admin/appointments", dependencies=[Depends(verify_token)])
async def admin_new_appointment(request: Request):
    body  = await request.json()
    name  = body["name"].strip()
    phone = body["phone"].strip().lstrip("+") + "@s.whatsapp.net"
    date  = body["date"]
    time  = body["time"]
    try:
        datetime.fromisoformat(f"{date}T{time}:00")
    except ValueError:
        return {"status": "invalid_date"}
    try:
        event_id = create_event(name, date, time, phone)
    except Exception as e:
        print(f"[CALENDAR ERROR] {e}")
        event_id = ""
    add_appointment(phone, name, date, time, event_id)
    return {"status": "ok"}


@app.post("/admin/recover", dependencies=[Depends(verify_token)])
async def admin_recover(request: Request):
    body = await request.json()
    phone, date, time = body["phone"], body["date"], body["time"]
    data = load_appointments()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time and apt["status"] == "cancelled":
            try:
                apt["event_id"] = create_event(apt["name"], date, time, phone)
            except Exception as e:
                print(f"[CALENDAR ERROR] {e}")
            apt["status"] = "scheduled"
            break
    save_appointments(data)
    return {"status": "ok"}


@app.post("/admin/edit", dependencies=[Depends(verify_token)])
async def admin_edit(request: Request):
    body      = await request.json()
    old_phone = body["old_phone"]
    old_date  = body["old_date"]
    old_time  = body["old_time"]
    new_name  = body["name"].strip()
    new_phone = body["phone"].strip().lstrip("+") + "@s.whatsapp.net"
    new_date  = body["date"]
    new_time  = body["time"]
    data = load_appointments()
    for apt in data:
        if apt["phone"] == old_phone and apt["date"] == old_date and apt["time"] == old_time:
            try:
                cancel_event(apt.get("event_id", ""))
            except Exception as e:
                print(f"[CALENDAR ERROR] {e}")
            try:
                apt["event_id"] = create_event(new_name, new_date, new_time, new_phone)
            except Exception as e:
                print(f"[CALENDAR ERROR] {e}")
                apt["event_id"] = ""
            apt["name"]  = new_name
            apt["phone"] = new_phone
            apt["date"]  = new_date
            apt["time"]  = new_time
            break
    save_appointments(data)
    return {"status": "ok"}


@app.post("/admin/attended", dependencies=[Depends(verify_token)])
async def admin_attended(request: Request):
    body = await request.json()
    mark_attended(body["phone"], body["date"], body["time"])
    return {"status": "ok"}


@app.post("/admin/completed", dependencies=[Depends(verify_token)])
async def admin_completed(request: Request):
    body = await request.json()
    mark_completed(body["phone"], body["date"], body["time"], body.get("notes", ""))
    return {"status": "ok"}


@app.post("/admin/close_protocol", dependencies=[Depends(verify_token)])
async def admin_close_protocol(request: Request):
    body = await request.json()
    phone, date, time = body["phone"], body["date"], body["time"]
    for apt in load_appointments():
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time:
            try:
                cancel_event(apt.get("event_id", ""))
            except Exception as e:
                print(f"[CALENDAR ERROR] {e}")
            break
    archive_appointment(phone, date, time)
    return {"status": "ok"}


@app.post("/admin/reset_session", dependencies=[Depends(verify_token)])
async def admin_reset_session(request: Request):
    body = await request.json()
    phone = body.get("phone", "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")
    if not phone.endswith("@s.whatsapp.net") and not phone.endswith("@lid"):
        phone = phone.lstrip("+") + "@s.whatsapp.net"
    reset_session(phone)
    return {"status": "ok"}


@app.post("/admin/pending/dismiss", dependencies=[Depends(verify_token)])
async def admin_pending_dismiss(request: Request):
    body = await request.json()
    dismiss_pending(body["id"])
    return {"status": "ok"}


@app.post("/admin/reschedule", dependencies=[Depends(verify_token)])
async def admin_reschedule(request: Request):
    body = await request.json()
    phone, date, time = body["phone"], body["date"], body["time"]
    data = load_appointments()
    for apt in data:
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time and apt["status"] == "no_show":
            try:
                apt["event_id"] = create_event(apt["name"], date, time, phone)
            except Exception as e:
                print(f"[CALENDAR ERROR] {e}")
            apt["status"] = "scheduled"
            apt["attended_at"] = None
            apt["completed_at"] = None
            apt["notes"] = ""
            break
    save_appointments(data)
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    event = data.get("event", "")
    print(f"[EVENTO] {event}")

    if event == "qrcode.updated":
        base64_img = data.get("data", {}).get("qrcode", {}).get("base64", "")
        if base64_img:
            qr_path = os.path.join(os.path.dirname(__file__), "qrcode.html")
            with open(qr_path, "w") as f:
                f.write(f'<html><body style="background:#fff;display:flex;justify-content:center;align-items:center;height:100vh"><img src="{base64_img}" style="width:300px;height:300px"></body></html>')
            print(f"QR code salvo em: {qr_path}")

    if event == "messages.upsert":
        message_data = data.get("data", {})
        key = message_data.get("key", {})

        if key.get("fromMe"):
            return {"status": "ignored"}

        msg_id = key.get("id", "")
        if msg_id and _is_duplicate(msg_id):
            print(f"[DEDUP] Webhook duplicado ignorado: {msg_id}")
            return {"status": "ignored"}

        sender = key.get("remoteJid", "")
        message = message_data.get("message", {})

        text = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text") or
            message.get("buttonsResponseMessage", {}).get("selectedDisplayText") or
            ""
        )

        if not text:
            MEDIA_RESPONSES = {
                "audioMessage":    "Nao consigo ouvir audios, mas fico feliz em te ajudar por texto! Como posso te atender?",
                "imageMessage":    "Nao consigo visualizar imagens, mas pode me descrever o que precisa! Como posso te ajudar?",
                "videoMessage":    "Nao consigo assistir videos, mas pode me escrever o que precisa! Como posso te ajudar?",
                "documentMessage": "Nao consigo abrir documentos, mas pode me descrever o que precisa! Como posso te ajudar?",
                "stickerMessage":  "Que simpatico! Posso te ajudar com alguma coisa?",
            }
            for media_type, response in MEDIA_RESPONSES.items():
                if media_type in message:
                    send_message(sender, response)
                    inject_assistant_message(sender, response)
                    print(f"[MIDIA] {media_type} recebida de {sender}")
                    return {"status": "ok"}
            return {"status": "ignored"}

        print(f"Mensagem de {sender}: {text}")

        new_sender = is_new_sender(sender)
        if new_sender:
            send_welcome(sender)
            return {"status": "ok"}

        if has_pending_reminder(sender):
            intent = _classify_reminder_response(text)
            if intent == "confirm":
                confirm_appointment(sender)
                msg = "Ótimo! Presença confirmada. Te esperamos!"
                send_message(sender, msg)
                inject_assistant_message(sender, msg)
                return {"status": "ok"}
            elif intent == "cancel":
                for apt in [a for a in load_appointments() if a["phone"] == sender and a["status"] == "reminder_sent"]:
                    try:
                        cancel_event(apt.get("event_id", ""))
                    except Exception as e:
                        print(f"[CALENDAR ERROR] {e}")
                cancel_pending_reminders(sender)
                msg = "Tudo bem! Agendamento cancelado. Quando quiser remarcar, é só nos chamar!"
                send_message(sender, msg)
                inject_assistant_message(sender, msg)
                return {"status": "ok"}
            else:
                name = next(
                    (a["name"] for a in load_appointments() if a["phone"] == sender and a["status"] == "reminder_sent"),
                    ""
                )
                for apt in [a for a in load_appointments() if a["phone"] == sender and a["status"] == "reminder_sent"]:
                    try:
                        cancel_event(apt.get("event_id", ""))
                    except Exception as e:
                        print(f"[CALENDAR ERROR] {e}")
                cancel_pending_reminders(sender)
                name_txt = f" {name}," if name else ","
                msg = (
                    f"Oi{name_txt} não consegui finalizar seu atendimento. "
                    f"Gostaria de remarcar sua consulta? "
                    f"Responda *SIM* para reagendar ou *NÃO* para encerrar por aqui."
                )
                send_message(sender, msg)
                inject_assistant_message(sender, msg)
                return {"status": "ok"}

        mark_response_received(sender)

        try:
            reply = await asyncio.to_thread(get_response, sender, text)

            pending_match = PENDING_MARKER.search(reply)
            if pending_match:
                add_pending(sender, pending_match.group(1).strip())
                reply = PENDING_MARKER.sub("", reply).strip()

            parts = [p.strip() for p in reply.split("[BREAK]") if p.strip()]

            await asyncio.sleep(0.5)

            for i, part in enumerate(parts):
                if i > 0:
                    await asyncio.sleep(_typing_delay(parts[i - 1]))

                match = MARKER.search(part)
                if match:
                    name = match.group(1).strip()
                    date_str = match.group(2)
                    time_str = match.group(3)

                    try:
                        hour, minute = map(int, time_str.split(":"))
                        dt = datetime.fromisoformat(date_str).replace(hour=hour, minute=minute)
                    except ValueError as e:
                        print(f"[VALIDACAO] Data/hora invalida no marcador: {date_str} {time_str} — {e}")
                        send_message(sender, part.split("[AGENDAR:")[0].strip())
                        continue

                    _active = ("scheduled", "day_reminder_sent", "reminder_sent", "response_received", "confirmed")
                    for _prev in [a for a in load_appointments() if a["phone"] == sender and a["status"] in _active]:
                        try:
                            cancel_event(_prev.get("event_id", ""))
                        except Exception as e:
                            print(f"[CALENDAR ERROR] cancel prev: {e}")
                        cancel_appointment(sender, _prev["date"], _prev["time"])
                        print(f"[REAGENDAMENTO] Anterior cancelado: {_prev['date']} {_prev['time']}")

                    try:
                        event_id = await asyncio.to_thread(create_event, name, date_str, time_str, sender)
                    except Exception as e:
                        print(f"[CALENDAR ERROR] {e}")
                        event_id = ""
                    add_appointment(sender, name, date_str, time_str, event_id)
                    date_display = f"{DIAS[dt.weekday()]} {dt.day:02d}/{dt.month:02d}/{dt.year}"
                    time_display = time_str.replace(":", "h")

                    confirmation = (
                        f"Agendamento confirmado! 📝\n"
                        f"Tipo de agendamento: Consulta - Exame de vista\n"
                        f"➡️ {date_display} às {time_display}\n\n"
                        f"Cliente: {name}\n\n"
                        f"📍 Nosso endereço: Rua Vereador Arthur Manoel Mariano, 362, Forquilhinhas, São José - SC (ao lado do cartório)\n\n"
                        f"📣 1hr antes da consulta iremos enviar uma mensagem de confirmação, caso precise reagendar, avisar com antecedência!!!"
                    )
                    await asyncio.to_thread(send_message, sender, confirmation)
                else:
                    clean = MARKER.sub("", part).strip()
                    if clean:
                        await asyncio.to_thread(send_message, sender, clean)

            print(f"LenzÓtica respondeu: {reply[:100]}")

        except Exception as e:
            error_info = f"{type(e).__name__}: {e}"
            print(f"[WEBHOOK ERROR] {error_info}")
            send_message(sender, "Um momento, por favor.")
            add_pending(sender, f"Erro no processamento da mensagem — {error_info}")

    return {"status": "ok"}
