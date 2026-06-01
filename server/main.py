import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import asyncio
import re
import time
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

_LOG_PATH      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")
_LOG_MAX_LINES = 5000
_log_write_cnt = 0

# Palavras-chave para auto-detecção de nível
_KW_ERROR = ("ERROR", "EXCEPTION", "TRACEBACK", "FAILED", " ERRO ", "[ERRO]")
_KW_WARN  = ("WARN", "WARNING", "TIMEOUT", "AVISO")

def _log(msg: str, level: str = ""):
    global _log_write_cnt
    if not level:
        mu = msg.upper()
        if any(k in mu for k in _KW_ERROR):
            level = "ERROR"
        elif any(k in mu for k in _KW_WARN):
            level = "WARN"
        else:
            level = "INFO"
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as _f:
            _f.write(line + "\n")
        _log_write_cnt += 1
        if _log_write_cnt % 100 == 0:
            _trim_log()
    except Exception:
        pass

def _trim_log():
    """Mantém o arquivo dentro de _LOG_MAX_LINES linhas (descarta as mais antigas)."""
    try:
        with open(_LOG_PATH, "r", encoding="utf-8", errors="replace") as _f:
            lines = _f.readlines()
        if len(lines) > _LOG_MAX_LINES:
            with open(_LOG_PATH, "w", encoding="utf-8") as _f:
                _f.writelines(lines[-_LOG_MAX_LINES:])
    except Exception:
        pass

import json
from typing import AsyncGenerator
from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv
import requests
import db
import context as ctx_mod
import rag as rag_mod
import prompt_builder as pb
from ai import get_response, inject_assistant_message, is_new_sender, has_empty_session, reset_session
from panel import render_panel
from calendar_service import create_event, cancel_event
from sync_calendar import sync_calendar
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
import clients as clients_mod

load_dotenv()

_SERVER_START = time.time()

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

async def verify_token_sse(
    key: str = Depends(_api_key_header),
    token: str = Query(default=""),
):
    """Autenticação para SSE: aceita header X-Admin-Token ou query param ?token=."""
    if key == ADMIN_TOKEN or token == ADMIN_TOKEN:
        return
    raise HTTPException(status_code=401, detail="Token inválido ou ausente.")

# ── SSE broadcast ──────────────────────────────────────────────────────────────
_sse_queues: list[asyncio.Queue] = []

async def _sse_broadcast(event_type: str, data: dict) -> None:
    if not _sse_queues:
        return
    msg = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    dead = []
    for q in _sse_queues:
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _sse_queues.remove(q)
        except ValueError:
            pass

_processed_msgs: dict = {}
_MSG_TTL = 30
_orcamento_state: dict = {}  # phone → {"step": "name"|"image", "name": str}

def _is_duplicate(msg_id: str) -> bool:
    now = time.time()
    for mid in list(_processed_msgs):
        if now - _processed_msgs[mid] > _MSG_TTL:
            del _processed_msgs[mid]
    if msg_id in _processed_msgs:
        return True
    _processed_msgs[msg_id] = now
    return False

MARKER         = re.compile(r'\[AGENDAR:([^|]*)\|(\d{4}-\d{2}-\d{2})\|(\d{2}:\d{2})\]')
PENDING_MARKER = re.compile(r'\[PENDENTE:([^\]]+)\]')
SLOT_MARKER    = re.compile(r'\[SLOT:(\d{4}-\d{2}-\d{2})\|(\d{2}:\d{2})\]')
# Detecta seleção de horário: "11", "11h", "11hrs", "11:00", "às 11", "as 11h30"
_TIME_PICK     = re.compile(r'(?:^|às?\s+|as\s+)(\d{1,2})(?::(\d{2}))?\s*(?:h(?:rs?)?)?\s*$', re.I)
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

_POSITIVE = {"sim", "s", "confirmo", "confirmado", "vou", "ok", "pode", "presente", "certo", "tá", "ta", "claro"}
_NEGATIVE = {"não", "nao", "n", "cancelar", "reagendar", "remarcar", "não posso", "nao posso"}

# _CAMPAIGN_MSG foi movido para bot_config (campos campaign_enabled + campaign_message)

def _is_campaign_response(text: str) -> bool:
    t = text.strip().lower()
    if "interesse" in t:
        return True
    keywords = ("quero agendar", "quero marcar", "sim quero", "sim, quero",
                "pode ser", "gostaria", "quero sim", "tenho interesse")
    return any(k in t for k in keywords)

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
    return min(1.5 + len(text) * 0.070, 5.0)


def _send_appointment_confirmation(phone: str, name: str, date: str, time: str) -> None:
    """Envia mensagem de confirmação de agendamento ao cliente via WhatsApp."""
    dt = datetime.fromisoformat(date)
    date_display = f"{DIAS[dt.weekday()]} {dt.day:02d}/{dt.month:02d}/{dt.year}"
    time_display = time.replace(":", "h")
    parts = [
        (
            f"Olá, {name}! Aqui é a {_get_bot_cfg_str('store_name') or 'LenzÓtica'} 👓\n\n"
            f"Seu agendamento foi confirmado! 📝\n"
            f"Tipo: {_get_bot_cfg_str('confirmation_appointment_type')}\n"
            f"➡️ {date_display} às {time_display}"
        ),
        f"📍 Nosso endereço: {_get_bot_cfg_str('confirmation_address')}",
        f"📣 {_get_bot_cfg_str('confirmation_footer')}",
    ]
    for part in parts:
        try:
            send_message(phone, part)
            inject_assistant_message(phone, part)
        except Exception as e:
            _log(f"[ADMIN NOTIF ERROR] {phone} — {e}")


def _send_reschedule_notification(phone: str, name: str, date: str, time: str) -> None:
    """Envia mensagem de remarcação ao cliente via WhatsApp."""
    dt = datetime.fromisoformat(date)
    date_display = f"{DIAS[dt.weekday()]} {dt.day:02d}/{dt.month:02d}/{dt.year}"
    time_display = time.replace(":", "h")
    text = (
        f"Olá, {name}! Aqui é a {_get_bot_cfg_str('store_name') or 'LenzÓtica'} 👓\n\n"
        f"Seu agendamento foi remarcado para *{date_display}* às *{time_display}*.\n\n"
        f"Qualquer dúvida, é só nos chamar. Te esperamos!"
    )
    try:
        send_message(phone, text)
        inject_assistant_message(phone, text)
    except Exception as e:
        _log(f"[ADMIN NOTIF ERROR] {phone} — {e}")


_DEFAULT_NOTIF: dict[str, str] = {
    "msg_lembrete_dia": (
        "Olá, {nome}! Aqui é a Liza da LenzÓtica 👓\n\n"
        "Passando para lembrar que *amanhã* você tem consulta marcada para as *{hora}h* ({data}).\n\n"
        "Qualquer dúvida é só nos chamar. Te esperamos!"
    ),
    "msg_lembrete_hora": (
        "Olá, {nome}! Aqui é a Liza da LenzÓtica 👓\n\n"
        "Sua consulta está marcada para *{data}* às *{hora}h*.\n\n"
        "Você confirma sua presença? Responda *SIM* para confirmar ou *NÃO* caso precise reagendar."
    ),
    "msg_cancelamento": (
        "Olá, {nome}. Seu agendamento para *{data}* às *{hora}h* "
        "foi cancelado pois não recebemos confirmação de presença.\n\n"
        "Deseja reagendar? É só nos enviar uma mensagem 😊"
    ),
    "msg_retorno": (
        "Olá, {nome}! Aqui é a Liza da LenzÓtica 👓\n\n"
        "Passando para lembrar que está na hora do seu retorno na ótica! "
        "Que tal agendarmos uma consulta? É só responder *SIM* que eu marco para você 😊"
    ),
}


def _get_notif_template(key: str) -> str:
    """Retorna o template customizado do DB ou o padrão se estiver vazio."""
    try:
        row = db.fetchone(f"SELECT {key} FROM bot_config LIMIT 1")
        if row and row[key] and str(row[key]).strip():
            return str(row[key])
    except Exception:
        pass
    return _DEFAULT_NOTIF.get(key, "")


# ── Helpers para campos de bot_config que saíram do código hardcoded ──────────

_DEFAULT_BOT_CFG: dict[str, str] = {
    "confirmation_appointment_type": "Exame de vista",
    "confirmation_address": "Rua Vereador Arthur Manoel Mariano, 362, Forquilhinhas, São José - SC (ao lado do cartório)",
    "confirmation_footer": "Caso precise reagendar, avisar com antecedência!!!",
    "campaign_message": (
        "Essa semana estamos com uma campanha de exame de vista completo gratuito para nossos clientes! "
        "Você teria interesse em agendar uma consulta?"
    ),
    "msg_media_audio":    "Nao consigo ouvir audios, mas fico feliz em te ajudar por texto! Como posso te atender?",
    "msg_media_image":    "Nao consigo visualizar imagens, mas pode me descrever o que precisa! Como posso te ajudar?",
    "msg_media_video":    "Nao consigo assistir videos, mas pode me escrever o que precisa! Como posso te ajudar?",
    "msg_media_document": "Nao consigo abrir documentos, mas pode me descrever o que precisa! Como posso te ajudar?",
    "msg_media_sticker":  "Que simpatico! Posso te ajudar com alguma coisa?",
}


def _get_bot_cfg_str(key: str) -> str:
    """Retorna campo texto de bot_config ou o default embutido."""
    try:
        row = db.fetchone(f"SELECT {key} FROM bot_config LIMIT 1")
        if row and row[key] and str(row[key]).strip():
            return str(row[key])
    except Exception:
        pass
    return _DEFAULT_BOT_CFG.get(key, "")


def _get_bot_cfg_bool(key: str, default: bool = True) -> bool:
    """Retorna campo booleano de bot_config."""
    try:
        row = db.fetchone(f"SELECT {key} FROM bot_config LIMIT 1")
        if row and row[key] is not None:
            return bool(row[key])
    except Exception:
        pass
    return default


def _render_notif(template: str, nome: str = "", data: str = "", hora: str = "") -> str:
    """Substitui {nome}, {data} e {hora} no template."""
    return (template
            .replace("{nome}", nome)
            .replace("{data}", data)
            .replace("{hora}", hora))


def _load_notif_templates() -> dict:
    """Carrega todos os templates de notificação em uma única query."""
    keys = ["msg_lembrete_dia", "msg_lembrete_hora", "msg_cancelamento", "msg_retorno"]
    try:
        cols = ", ".join(keys)
        row = db.fetchone(f"SELECT {cols} FROM bot_config LIMIT 1")
        if row:
            return {k: str(row[k]).strip() if row[k] and str(row[k]).strip() else _DEFAULT_NOTIF.get(k, "") for k in keys}
    except Exception:
        pass
    return {k: _DEFAULT_NOTIF.get(k, "") for k in keys}


async def check_day_reminders(templates: dict):
    for apt in get_appointments_for_day_reminder():
        phone = apt["phone"]
        name = apt["name"]
        date_br = format_date_br(apt["date"])
        text = _render_notif(templates["msg_lembrete_dia"], nome=name, data=date_br, hora=apt["time"])
        send_message(phone, text)
        inject_assistant_message(phone, text)
        mark_day_reminder_sent(phone, apt["date"], apt["time"])
        print(f"[LEMBRETE 1 DIA] Enviado para {phone}")


async def check_reminders(templates: dict):
    for apt in get_appointments_for_reminder():
        phone = apt["phone"]
        name = apt["name"]
        date_br = format_date_br(apt["date"])
        text = _render_notif(templates["msg_lembrete_hora"], nome=name, data=date_br, hora=apt["time"])
        send_message(phone, text)
        inject_assistant_message(phone, text)
        mark_reminder_sent(phone, apt["date"], apt["time"])
        print(f"[LEMBRETE] Enviado para {phone}")


async def check_cancellations(templates: dict):
    for apt in get_appointments_to_cancel():
        phone = apt["phone"]
        name = apt["name"]
        date_br = format_date_br(apt["date"])
        text = _render_notif(templates["msg_cancelamento"], nome=name, data=date_br, hora=apt["time"])
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


_sync_counter = 0


async def scheduler_loop():
    global _sync_counter
    while True:
        try:
            templates = _load_notif_templates()
            await check_day_reminders(templates)
            await check_reminders(templates)
            await check_cancellations(templates)
            await check_no_shows()

            # Sync do Google Calendar a cada 30 ciclos (~30 min)
            _sync_counter += 1
            if _sync_counter >= 30:
                _sync_counter = 0
                try:
                    await asyncio.to_thread(sync_calendar)
                    print("[CALENDAR SYNC] Limpeza automática concluída")
                except Exception as e:
                    print(f"[CALENDAR SYNC ERROR] {e}")
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante colunas de slot e templates de notificação
    _migrations = [
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS slot_duration_minutes INT  NOT NULL DEFAULT 30",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS slot_interval_minutes  INT  NOT NULL DEFAULT 0",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_lembrete_dia       TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_lembrete_hora      TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_cancelamento       TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_retorno            TEXT NOT NULL DEFAULT ''",
        # Toggle global da IA
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS ia_global_enabled BOOLEAN NOT NULL DEFAULT TRUE",
        # Campos de confirmação de agendamento (saíram do hardcoded)
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS confirmation_appointment_type TEXT NOT NULL DEFAULT 'Exame de vista'",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS confirmation_address TEXT NOT NULL DEFAULT 'Rua Vereador Arthur Manoel Mariano, 362, Forquilhinhas, São José - SC (ao lado do cartório)'",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS confirmation_footer TEXT NOT NULL DEFAULT 'Caso precise reagendar, avisar com antecedência!!!'",
        # Campanha (toggle + mensagem)
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS campaign_enabled BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS campaign_message TEXT NOT NULL DEFAULT 'Essa semana estamos com uma campanha de exame de vista completo gratuito para nossos clientes! Você teria interesse em agendar uma consulta?'",
        # Respostas a mídias
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_media_audio    TEXT NOT NULL DEFAULT 'Nao consigo ouvir audios, mas fico feliz em te ajudar por texto! Como posso te atender?'",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_media_image    TEXT NOT NULL DEFAULT 'Nao consigo visualizar imagens, mas pode me descrever o que precisa! Como posso te ajudar?'",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_media_video    TEXT NOT NULL DEFAULT 'Nao consigo assistir videos, mas pode me escrever o que precisa! Como posso te ajudar?'",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_media_document TEXT NOT NULL DEFAULT 'Nao consigo abrir documentos, mas pode me descrever o que precisa! Como posso te ajudar?'",
        "ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS msg_media_sticker  TEXT NOT NULL DEFAULT 'Que simpatico! Posso te ajudar com alguma coisa?'",
        # Templates personalizados do operador
        """CREATE TABLE IF NOT EXISTS custom_templates (
            id         SERIAL PRIMARY KEY,
            name       TEXT        NOT NULL,
            content    TEXT        NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
    ]
    for _sql in _migrations:
        try:
            db.execute(_sql)
        except Exception as _e:
            _log(f"[lifespan] migration: {_e}")
    task = asyncio.create_task(scheduler_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "imagens", "logo lenzótica.PNG")

@app.get("/debug", response_class=HTMLResponse, dependencies=[Depends(verify_token)])
async def debug_log():
    try:
        with open(_LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()[-200:]
    except FileNotFoundError:
        lines = ["(nenhum log ainda)\n"]
    content = "".join(lines)
    return HTMLResponse(f"<html><body style='font-family:monospace;white-space:pre;font-size:13px;padding:16px'>{content}</body></html>")

@app.post("/debug/clear", dependencies=[Depends(verify_token)])
async def debug_clear():
    open(_LOG_PATH, "w").close()
    return {"status": "ok"}

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
    clients_stats = clients_mod.get_return_stats()
    return render_panel(agendamentos, CALENDAR_EMBED_URL, ADMIN_TOKEN, pending_items, clients_count=clients_stats.get("total", 0), overdue_count=clients_stats.get("overdue", 0))


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
            text = _render_notif(
                _get_notif_template("msg_lembrete_hora"),
                nome=name, data=date_br, hora=time,
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
    notify = bool(body.get("notify", True))
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
    clients_mod.upsert_from_appointment(phone, name, date)
    if notify:
        await asyncio.to_thread(_send_appointment_confirmation, phone, name, date, time)
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
    notify    = bool(body.get("notify", True))
    data = load_appointments()
    changed = False
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
            changed = True
            break
    save_appointments(data)
    if changed and notify:
        date_changed = new_date != old_date or new_time != old_time
        if date_changed:
            await asyncio.to_thread(_send_reschedule_notification, new_phone, new_name, new_date, new_time)
    return {"status": "ok"}


@app.post("/admin/attended", dependencies=[Depends(verify_token)])
async def admin_attended(request: Request):
    body = await request.json()
    phone, date, time = body["phone"], body["date"], body["time"]
    for apt in load_appointments():
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time:
            try:
                cancel_event(apt.get("event_id", ""))
            except Exception as e:
                print(f"[CALENDAR ERROR] attended: {e}")
            break
    mark_attended(phone, date, time)
    return {"status": "ok"}


@app.post("/admin/completed", dependencies=[Depends(verify_token)])
async def admin_completed(request: Request):
    body = await request.json()
    phone, date, time = body["phone"], body["date"], body["time"]
    for apt in load_appointments():
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time:
            try:
                cancel_event(apt.get("event_id", ""))
            except Exception as e:
                print(f"[CALENDAR ERROR] completed: {e}")
            break
    mark_completed(phone, date, time, body.get("notes", ""))
    # Atualiza cadastro do cliente
    for apt in load_appointments():
        if apt["phone"] == phone and apt["date"] == date and apt["time"] == time:
            clients_mod.upsert_from_appointment(phone, apt["name"], date)
            break
    return {"status": "ok"}


@app.post("/admin/completed_by_phone", dependencies=[Depends(verify_token)])
async def admin_completed_by_phone(request: Request):
    try:
        body = await request.json()
        phone = body["phone"]
        notes = body.get("notes", "")
        data = load_appointments()
        for apt in data:
            if apt["phone"] == phone and apt["status"] not in ("archived", "completed"):
                try:
                    cancel_event(apt.get("event_id", ""))
                except Exception as e:
                    _log(f"[CALENDAR ERROR] completed_by_phone: {e}")
                apt["status"] = "completed"
                apt["completed_at"] = datetime.now().isoformat()
                apt["notes"] = notes
                save_appointments(data)
                _log(f"[ADMIN] completed_by_phone: {phone}")
                clients_mod.upsert_from_appointment(phone, apt["name"], apt["date"])
                break
        return {"status": "ok"}
    except Exception as e:
        _log(f"[ADMIN ERROR] completed_by_phone: {e}")
        raise


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
    archive_appointment(phone, date, time)
    reset_session(phone)
    return {"status": "ok"}


@app.post("/admin/close_by_phone", dependencies=[Depends(verify_token)])
async def admin_close_by_phone(request: Request):
    body = await request.json()
    phone = body["phone"]
    data = load_appointments()
    changed = False
    for apt in data:
        if apt["phone"] == phone and apt["status"] != "archived":
            try:
                cancel_event(apt.get("event_id", ""))
            except Exception as e:
                print(f"[CALENDAR ERROR] close_by_phone: {e}")
            apt["status"] = "archived"
            apt["archived_at"] = datetime.now().isoformat()
            changed = True
    if changed:
        save_appointments(data)
    reset_session(phone)
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


# ─── Business Hours ───────────────────────────────────────────────────────────

@app.get("/admin/business-hours", dependencies=[Depends(verify_token)])
async def get_business_hours():
    rows = db.fetchall(
        "SELECT day_of_week, is_open, is_flexible, open_time, close_time FROM business_hours ORDER BY day_of_week"
    )
    return [
        {
            "day_of_week": r["day_of_week"],
            "is_open": r["is_open"],
            "is_flexible": r["is_flexible"],
            "open_time": str(r["open_time"])[:5] if r["open_time"] else None,
            "close_time": str(r["close_time"])[:5] if r["close_time"] else None,
        }
        for r in rows
    ]


@app.post("/admin/business-hours", dependencies=[Depends(verify_token)])
async def save_business_hours(request: Request):
    rows = await request.json()
    for row in rows:
        day = row["day_of_week"]
        db.execute(
            """
            UPDATE business_hours
            SET is_open=%s, is_flexible=%s, open_time=%s, close_time=%s
            WHERE day_of_week=%s
            """,
            (
                row.get("is_open", False),
                row.get("is_flexible", False),
                row.get("open_time") or None,
                row.get("close_time") or None,
                day,
            ),
        )
    return {"status": "ok"}


# ─── System Prompt ─────────────────────────────────────────────────────────────

@app.get("/admin/system-prompt", dependencies=[Depends(verify_token)])
async def get_system_prompt():
    return {"prompt": ctx_mod.get_system_prompt()}


@app.post("/admin/system-prompt", dependencies=[Depends(verify_token)])
async def save_system_prompt(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "").strip()
    db.execute(
        "UPDATE rag_config SET system_prompt=%s WHERE is_active=true", (prompt,)
    )
    return {"status": "ok"}


# ─── RAG Config ────────────────────────────────────────────────────────────────

@app.get("/admin/rag/config", dependencies=[Depends(verify_token)])
async def get_rag_config():
    cfg = rag_mod.get_config()
    return {k: v for k, v in cfg.items() if k != "system_prompt"}


@app.post("/admin/rag/config", dependencies=[Depends(verify_token)])
async def save_rag_config(request: Request):
    body = await request.json()
    fields = []
    values = []
    allowed = {
        "enabled": bool,
        "top_k": int,
        "min_similarity": float,
        "max_context_tokens": int,
        "chunk_size": int,
        "chunk_overlap": int,
    }
    for key, cast in allowed.items():
        if key in body:
            fields.append(f"{key}=%s")
            values.append(cast(body[key]))
    if not fields:
        return {"status": "nothing_to_update"}
    values.append(True)  # WHERE is_active=true
    db.execute(
        f"UPDATE rag_config SET {', '.join(fields)} WHERE is_active=%s", tuple(values)
    )
    return {"status": "ok"}


# ─── RAG Documents ─────────────────────────────────────────────────────────────

@app.get("/admin/rag/documents", dependencies=[Depends(verify_token)])
async def list_rag_documents():
    rows = db.fetchall(
        """
        SELECT d.id, d.title, d.source_type, d.is_active, d.created_at,
               COUNT(c.id) AS chunk_count
        FROM rag_documents d
        LEFT JOIN rag_chunks c ON c.document_id = d.id
        GROUP BY d.id
        ORDER BY d.created_at DESC
        """
    )
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "source_type": r["source_type"],
            "is_active": r["is_active"],
            "chunk_count": r["chunk_count"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@app.post("/admin/rag/documents", dependencies=[Depends(verify_token)])
async def create_rag_document(request: Request):
    body = await request.json()
    title = body.get("title", "").strip()
    source_type = body.get("source_type", "manual")
    content = body.get("content", "").strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="title e content sao obrigatorios")
    doc_id = db.fetchval(
        "INSERT INTO rag_documents (title, source_type, content) VALUES (%s,%s,%s) RETURNING id",
        (title, source_type, content),
    )
    try:
        chunk_count = rag_mod.index_document(doc_id)
    except Exception as e:
        _log(f"[RAG] Erro ao indexar documento {doc_id}: {e}")
        chunk_count = 0
    return {"status": "ok", "doc_id": doc_id, "chunk_count": chunk_count}


@app.patch("/admin/rag/documents/{doc_id}/toggle", dependencies=[Depends(verify_token)])
async def toggle_rag_document(doc_id: int, request: Request):
    body = await request.json()
    is_active = bool(body.get("is_active", True))
    db.execute(
        "UPDATE rag_documents SET is_active=%s WHERE id=%s", (is_active, doc_id)
    )
    return {"status": "ok"}


@app.delete("/admin/rag/documents/{doc_id}", dependencies=[Depends(verify_token)])
async def delete_rag_document(doc_id: int):
    db.execute("DELETE FROM rag_documents WHERE id=%s", (doc_id,))
    return {"status": "ok"}


# ─── RAG Logs ──────────────────────────────────────────────────────────────────

@app.get("/admin/rag/logs", dependencies=[Depends(verify_token)])
async def get_rag_logs():
    rows = db.fetchall(
        """
        SELECT phone, query_text, chunks_returned, top_similarity, latency_ms, created_at
        FROM rag_query_log
        ORDER BY created_at DESC
        LIMIT 50
        """
    )
    return [
        {
            "phone": r["phone"],
            "query_text": r["query_text"],
            "chunks_returned": r["chunks_returned"],
            "top_similarity": float(r["top_similarity"]) if r["top_similarity"] is not None else None,
            "latency_ms": r["latency_ms"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


# ─── Bot Config ────────────────────────────────────────────────────────────────

@app.get("/admin/bot-config", dependencies=[Depends(verify_token)])
async def get_bot_config():
    row = db.fetchone("SELECT * FROM bot_config LIMIT 1")
    if not row:
        return {}
    d = dict(row)
    d.pop("id", None)
    d.pop("updated_at", None)
    return d


@app.post("/admin/bot-config", dependencies=[Depends(verify_token)])
async def save_bot_config(request: Request):
    body = await request.json()
    allowed = [
        "store_name", "store_address", "store_phone", "store_services",
        "store_notes", "bot_name", "bot_tone", "bot_personality",
        "bot_greeting", "bot_extra_rules",
        "msg_lembrete_dia", "msg_lembrete_hora", "msg_cancelamento", "msg_retorno",
        # Confirmação de agendamento
        "confirmation_appointment_type", "confirmation_address", "confirmation_footer",
        # Campanha
        "campaign_message",
        # Respostas a mídias
        "msg_media_audio", "msg_media_image", "msg_media_video",
        "msg_media_document", "msg_media_sticker",
    ]
    allowed_int  = ["slot_duration_minutes", "slot_interval_minutes"]
    allowed_bool = ["campaign_enabled"]
    fields = []
    values = []
    for key in allowed:
        if key in body:
            fields.append(f"{key}=%s")
            values.append(str(body[key]))
    for key in allowed_int:
        if key in body:
            fields.append(f"{key}=%s")
            values.append(int(body[key]))
    for key in allowed_bool:
        if key in body:
            fields.append(f"{key}=%s")
            values.append(bool(body[key]))
    if not fields:
        return {"status": "nothing_to_update"}
    fields.append("updated_at=now()")
    db.execute(f"UPDATE bot_config SET {', '.join(fields)}", tuple(values))
    pb.build_and_save_prompt()
    return {"status": "ok"}


# ─── Custom Templates ──────────────────────────────────────────────────────────

@app.get("/admin/custom-templates", dependencies=[Depends(verify_token)])
async def list_custom_templates():
    rows = db.fetchall(
        "SELECT id, name, content, created_at, updated_at FROM custom_templates ORDER BY id"
    )
    return [
        {
            "id":         r["id"],
            "name":       r["name"],
            "content":    r["content"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]


@app.post("/admin/custom-templates", dependencies=[Depends(verify_token)])
async def create_custom_template(request: Request):
    body = await request.json()
    name    = body.get("name", "").strip()
    content = body.get("content", "").strip()
    if not name or not content:
        raise HTTPException(status_code=400, detail="name e content são obrigatórios")
    tpl_id = db.fetchval(
        "INSERT INTO custom_templates (name, content) VALUES (%s, %s) RETURNING id",
        (name, content),
    )
    _log(f"[ADMIN] custom template criado: id={tpl_id} name={name!r}")
    return {"status": "ok", "id": tpl_id}


@app.put("/admin/custom-templates/{tpl_id}", dependencies=[Depends(verify_token)])
async def update_custom_template(tpl_id: int, request: Request):
    body = await request.json()
    name    = body.get("name", "").strip()
    content = body.get("content", "").strip()
    if not name or not content:
        raise HTTPException(status_code=400, detail="name e content são obrigatórios")
    rows = db.fetchval(
        "UPDATE custom_templates SET name=%s, content=%s, updated_at=NOW() WHERE id=%s RETURNING id",
        (name, content, tpl_id),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    _log(f"[ADMIN] custom template atualizado: id={tpl_id}")
    return {"status": "ok"}


@app.delete("/admin/custom-templates/{tpl_id}", dependencies=[Depends(verify_token)])
async def delete_custom_template(tpl_id: int):
    db.execute("DELETE FROM custom_templates WHERE id=%s", (tpl_id,))
    _log(f"[ADMIN] custom template excluido: id={tpl_id}")
    return {"status": "ok"}


# ─── FAQ ───────────────────────────────────────────────────────────────────────

@app.get("/admin/faq", dependencies=[Depends(verify_token)])
async def list_faq():
    rows = db.fetchall(
        "SELECT id, question, answer, is_active, sort_order FROM faq_items ORDER BY sort_order, id"
    )
    return [dict(r) for r in rows]


@app.post("/admin/faq", dependencies=[Depends(verify_token)])
async def create_faq(request: Request):
    body = await request.json()
    question = body.get("question", "").strip()
    answer = body.get("answer", "").strip()
    sort_order = int(body.get("sort_order", 0))
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question e answer são obrigatórios")
    faq_id = db.fetchval(
        "INSERT INTO faq_items (question, answer, sort_order) VALUES (%s,%s,%s) RETURNING id",
        (question, answer, sort_order),
    )
    pb.build_and_save_prompt()
    return {"status": "ok", "id": faq_id}


@app.put("/admin/faq/{faq_id}", dependencies=[Depends(verify_token)])
async def update_faq(faq_id: int, request: Request):
    body = await request.json()
    question = body.get("question", "").strip()
    answer = body.get("answer", "").strip()
    sort_order = int(body.get("sort_order", 0))
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question e answer são obrigatórios")
    db.execute(
        "UPDATE faq_items SET question=%s, answer=%s, sort_order=%s WHERE id=%s",
        (question, answer, sort_order, faq_id),
    )
    pb.build_and_save_prompt()
    return {"status": "ok"}


@app.patch("/admin/faq/{faq_id}/toggle", dependencies=[Depends(verify_token)])
async def toggle_faq(faq_id: int, request: Request):
    body = await request.json()
    is_active = bool(body.get("is_active", True))
    db.execute("UPDATE faq_items SET is_active=%s WHERE id=%s", (is_active, faq_id))
    pb.build_and_save_prompt()
    return {"status": "ok"}


@app.delete("/admin/faq/{faq_id}", dependencies=[Depends(verify_token)])
async def delete_faq(faq_id: int):
    db.execute("DELETE FROM faq_items WHERE id=%s", (faq_id,))
    pb.build_and_save_prompt()
    return {"status": "ok"}


# ─── Clients ───────────────────────────────────────────────────────────────────

@app.get("/admin/clients", dependencies=[Depends(verify_token)])
async def list_clients():
    return clients_mod.load()


@app.post("/admin/clients", dependencies=[Depends(verify_token)])
async def create_client(request: Request):
    body = await request.json()
    first_name = body.get("first_name", "").strip()
    if not first_name:
        raise HTTPException(status_code=400, detail="first_name é obrigatório")
    client_id = clients_mod.add_client(
        first_name=first_name,
        last_name=body.get("last_name", "").strip(),
        phone=body.get("phone", "").strip(),
        last_appointment_date=body.get("last_appointment_date") or None,
        notes=body.get("notes", "").strip(),
        return_date=body.get("return_date") or None,
        return_period_months=int(body["return_period_months"]) if body.get("return_period_months") else None,
        birth_date=body.get("birth_date") or None,
    )
    return {"status": "ok", "id": client_id}


@app.put("/admin/clients/{client_id}", dependencies=[Depends(verify_token)])
async def update_client(client_id: int, request: Request):
    body = await request.json()
    first_name = body.get("first_name", "").strip()
    if not first_name:
        raise HTTPException(status_code=400, detail="first_name é obrigatório")
    clients_mod.update_client(
        client_id=client_id,
        first_name=first_name,
        last_name=body.get("last_name", "").strip(),
        phone=body.get("phone", "").strip(),
        last_appointment_date=body.get("last_appointment_date") or None,
        notes=body.get("notes", "").strip(),
        return_date=body.get("return_date") or None,
        return_period_months=int(body["return_period_months"]) if body.get("return_period_months") else None,
        birth_date=body.get("birth_date") or None,
    )
    return {"status": "ok"}


@app.delete("/admin/clients/{client_id}", dependencies=[Depends(verify_token)])
async def delete_client(client_id: int):
    clients_mod.delete_client(client_id)
    return {"status": "ok"}


@app.post("/admin/clients/{client_id}/notify-return", dependencies=[Depends(verify_token)])
async def notify_client_return(client_id: int, request: Request):
    client = clients_mod.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    phone_raw = client.get("phone", "").strip()
    if not phone_raw:
        raise HTTPException(status_code=400, detail="Cliente sem telefone cadastrado")
    # Garante formato WhatsApp
    if not phone_raw.endswith("@s.whatsapp.net") and not phone_raw.endswith("@lid"):
        phone = phone_raw.lstrip("+") + "@s.whatsapp.net"
    else:
        phone = phone_raw
    name = client.get("first_name", "")
    text = _render_notif(
        _get_notif_template("msg_retorno"),
        nome=name,
    )
    try:
        send_message(phone, text)
        inject_assistant_message(phone, text)
    except Exception as e:
        _log(f"[NOTIFY RETURN ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar mensagem: {e}")
    return {"status": "ok"}


@app.get("/admin/clients/stats", dependencies=[Depends(verify_token)])
async def clients_stats():
    return clients_mod.get_return_stats()


@app.post("/admin/build-prompt", dependencies=[Depends(verify_token)])
async def build_prompt_endpoint():
    prompt = pb.build_and_save_prompt()
    return {"status": "ok", "length": len(prompt)}


# ─── Chat Cliente ───────────────────────────────────────────────────────────────

def _is_ia_enabled(phone: str) -> bool:
    """Retorna True se a IA está habilitada para este número (padrão True)."""
    try:
        row = db.fetchone("SELECT ia_enabled FROM chat_ia_mode WHERE phone = %s", (phone,))
        return row["ia_enabled"] if row else True
    except Exception:
        return True


@app.get("/admin/chat/contacts", dependencies=[Depends(verify_token)])
async def chat_contacts():
    """Lista contatos com última mensagem, contagem não lida e modo IA."""
    rows = db.fetchall("""
        WITH last_msg AS (
            SELECT DISTINCT ON (phone)
                phone, role, content, created_at
            FROM conversation_history
            ORDER BY phone, created_at DESC
        ),
        unread_counts AS (
            SELECT ch.phone,
                COUNT(*) FILTER (
                    WHERE ch.role = 'user'
                    AND (crs.last_read_at IS NULL OR ch.created_at > crs.last_read_at)
                ) AS unread
            FROM conversation_history ch
            LEFT JOIN chat_read_status crs ON crs.phone = ch.phone
            GROUP BY ch.phone
        ),
        apt_names AS (
            SELECT DISTINCT ON (phone) phone, name
            FROM appointments
            ORDER BY phone, created_at DESC
        ),
        client_names AS (
            SELECT
                REPLACE(REPLACE(phone, '@s.whatsapp.net', ''), '@lid', '') AS phone_raw,
                TRIM(first_name || ' ' || COALESCE(last_name, '')) AS name
            FROM clients
        )
        SELECT
            lm.phone,
            lm.role,
            lm.content,
            lm.created_at,
            COALESCE(uc.unread, 0)                          AS unread_count,
            COALESCE(an.name, cn.name)                      AS resolved_name,
            COALESCE(im.ia_enabled, TRUE)                   AS ia_enabled
        FROM last_msg lm
        LEFT JOIN unread_counts uc ON uc.phone = lm.phone
        LEFT JOIN apt_names     an ON an.phone = lm.phone
        LEFT JOIN client_names  cn ON cn.phone_raw =
            REPLACE(REPLACE(lm.phone, '@s.whatsapp.net', ''), '@lid', '')
        LEFT JOIN chat_ia_mode  im ON im.phone = lm.phone
        ORDER BY lm.created_at DESC
    """)

    contacts = []
    for row in rows:
        phone = row["phone"]
        display_phone = phone.replace("@s.whatsapp.net", "").replace("@lid", "")
        name = (row["resolved_name"] or "").strip() or display_phone
        contacts.append({
            "phone": phone,
            "display_phone": display_phone,
            "name": name,
            "last_message": (row["content"] or "")[:80],
            "last_message_at": row["created_at"].isoformat() if row["created_at"] else None,
            "last_message_role": row["role"],
            "unread_count": int(row["unread_count"]),
            "ia_enabled": bool(row["ia_enabled"]),
        })

    return contacts


@app.get("/admin/chat/messages/{phone:path}", dependencies=[Depends(verify_token)])
async def chat_messages(phone: str):
    """Retorna histórico completo de mensagens de um contato."""
    rows = db.fetchall(
        "SELECT id, role, content, COALESCE(sent_by_operator, FALSE) AS sent_by_operator, created_at"
        " FROM conversation_history WHERE phone = %s ORDER BY created_at ASC",
        (phone,),
    )
    return [
        {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "sent_by_operator": bool(r.get("sent_by_operator", False)),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@app.get("/admin/chat/stream", dependencies=[Depends(verify_token_sse)])
async def chat_stream(request: Request):
    """SSE — transmite eventos de novas mensagens para o painel de chat."""
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _sse_queues.append(q)

    async def generator() -> AsyncGenerator[str, None]:
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            try:
                _sse_queues.remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/admin/chat/send", dependencies=[Depends(verify_token)])
async def chat_send(request: Request):
    """Envia mensagem do operador para um contato via WhatsApp."""
    body = await request.json()
    phone = body.get("phone", "").strip()
    text = body.get("text", "").strip()
    if not phone or not text:
        raise HTTPException(status_code=400, detail="phone e text são obrigatórios")
    try:
        send_message(phone, text)
    except Exception as e:
        _log(f"[CHAT SEND ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar: {e}")
    import session as _sess
    _sess.push(phone, "assistant", text, sent_by_operator=True)
    _sess.save()
    await _sse_broadcast("new_message", {
        "phone": phone,
        "content": text[:80],
        "role": "assistant",
        "sent_by_operator": True,
    })
    return {"status": "ok"}


@app.post("/admin/chat/read/{phone:path}", dependencies=[Depends(verify_token)])
async def chat_mark_read(phone: str):
    """Marca conversa de um contato como lida."""
    db.execute(
        "INSERT INTO chat_read_status (phone, last_read_at) VALUES (%s, NOW())"
        " ON CONFLICT (phone) DO UPDATE SET last_read_at = NOW()",
        (phone,),
    )
    return {"status": "ok"}


@app.get("/admin/chat/ia-mode/{phone:path}", dependencies=[Depends(verify_token)])
async def get_ia_mode(phone: str):
    row = db.fetchone("SELECT ia_enabled FROM chat_ia_mode WHERE phone = %s", (phone,))
    return {"ia_enabled": row["ia_enabled"] if row else True}


@app.post("/admin/chat/ia-mode/{phone:path}", dependencies=[Depends(verify_token)])
async def set_ia_mode(phone: str, request: Request):
    body = await request.json()
    enabled = bool(body.get("ia_enabled", True))
    db.execute(
        "INSERT INTO chat_ia_mode (phone, ia_enabled, updated_at) VALUES (%s, %s, NOW())"
        " ON CONFLICT (phone) DO UPDATE SET ia_enabled = %s, updated_at = NOW()",
        (phone, enabled, enabled),
    )
    return {"status": "ok", "ia_enabled": enabled}


@app.get("/admin/chat/contact-info/{phone:path}", dependencies=[Depends(verify_token)])
async def chat_contact_info(phone: str):
    """Retorna dados do cliente + agendamentos para o painel lateral do chat."""
    display_phone = phone.replace("@s.whatsapp.net", "").replace("@lid", "")

    client = db.fetchone(
        """
        SELECT first_name, last_name, notes,
               return_date::text AS return_date,
               visit_count,
               last_appointment_date::text AS last_appointment_date
        FROM clients
        WHERE REPLACE(REPLACE(phone,'@s.whatsapp.net',''),'@lid','') = %s
           OR phone = %s
        LIMIT 1
        """,
        (display_phone, phone),
    )

    appointments = db.fetchall(
        "SELECT name, date::text AS date, time, status"
        " FROM appointments WHERE phone = %s ORDER BY created_at DESC LIMIT 8",
        (phone,),
    )

    return {
        "client": dict(client) if client else None,
        "appointments": [dict(a) for a in appointments],
    }


@app.post("/admin/chat/note/{phone:path}", dependencies=[Depends(verify_token)])
async def chat_save_note(phone: str, request: Request):
    """Salva nota interna do operador sobre o cliente."""
    body = await request.json()
    note = body.get("note", "").strip()
    display_phone = phone.replace("@s.whatsapp.net", "").replace("@lid", "")
    db.execute(
        "UPDATE clients SET notes = %s"
        " WHERE REPLACE(REPLACE(phone,'@s.whatsapp.net',''),'@lid','') = %s OR phone = %s",
        (note, display_phone, phone),
    )
    return {"status": "ok"}


# Pares (texto_sem_break, texto_com_break) para casos onde o modelo
# omite o token [BREAK] mesmo quando instruído. A verificação é
# case-insensitive e tolerante a variações de espaçamento.
_BREAK_FIXES: list[tuple[str, str]] = [
    (
        "pode passar direto com o oftalmologista. Por favor entre em contato",
        "pode passar direto com o oftalmologista.[BREAK]Por favor entre em contato",
    ),
    (
        "pode passar direto com o oftalmologista. Por favor, entre em contato",
        "pode passar direto com o oftalmologista.[BREAK]Por favor, entre em contato",
    ),
    # Fluxo de agendamento: campanha → verificação → horários
    (
        "clientes. Vou verificar",
        "clientes.[BREAK]Vou verificar",
    ),
    (
        "clientes! Vou verificar",
        "clientes![BREAK]Vou verificar",
    ),
    (
        "momento. Ok, para",
        "momento.[BREAK]Ok, para",
    ),
    (
        "momento. Temos disponível",
        "momento.[BREAK]Temos disponível",
    ),
]


def _restore_breaks(reply: str) -> str:
    """Injeta [BREAK] em respostas onde o modelo omitiu o token obrigatório.
    Aplica todos os padrões correspondentes (não para no primeiro)."""
    for pattern, replacement in _BREAK_FIXES:
        reply_lower = reply.lower()
        if pattern.lower() in reply_lower:
            idx = reply_lower.find(pattern.lower())
            reply = reply[:idx] + replacement + reply[idx + len(pattern):]
    return reply


def _detect_slot_selection(sender: str, user_text: str) -> None:
    """Detecta seleção de horário na mensagem do usuário e salva em pending_slot."""
    import session as _sess_det
    m = _TIME_PICK.search(user_text.strip())
    if not m:
        return
    hour = int(m.group(1))
    minutes = m.group(2) or "00"
    target = f"{hour:02d}:{minutes}"
    offered = _sess_det.get_offered_slots(sender)
    if not offered:
        return
    if target not in offered:
        return
    _sess_det.set_pending_slot(sender, offered[target], target)
    _log(f"[SLOT-AUTO] {sender} selecionou {target} em {offered[target]} (input: {user_text!r})")


def _ia_global_enabled() -> bool:
    """Retorna o estado do toggle global da IA."""
    try:
        row = db.fetchone("SELECT ia_global_enabled FROM bot_config LIMIT 1")
        return bool(row["ia_global_enabled"]) if row else True
    except Exception:
        return True


@app.get("/admin/ia-global", dependencies=[Depends(verify_token)])
async def get_ia_global():
    return {"ia_enabled": _ia_global_enabled()}


@app.post("/admin/ia-global", dependencies=[Depends(verify_token)])
async def set_ia_global(request: Request):
    body    = await request.json()
    enabled = bool(body.get("ia_enabled", True))
    db.execute("UPDATE bot_config SET ia_global_enabled = %s", (enabled,))
    estado  = "ATIVADA" if enabled else "PAUSADA"
    _log(f"[ADMIN] IA global {estado} via painel.")
    return {"status": "ok", "ia_enabled": enabled}


# ─── System Status ─────────────────────────────────────────────────────────────

@app.get("/admin/system-status", dependencies=[Depends(verify_token)])
async def system_status():
    checks = []

    # 1 · Servidor / uptime
    uptime_secs = int(time.time() - _SERVER_START)
    h, rem  = divmod(uptime_secs, 3600)
    m, s    = divmod(rem, 60)
    uptime_str = (f"{h}h {m:02d}min" if h else f"{m}min {s:02d}s" if m else f"{s}s")
    checks.append({"key": "server", "label": "Servidor",
                   "status": "ok", "detail": f"Uptime: {uptime_str}", "latency_ms": None})

    # 2 · PostgreSQL
    t0 = time.time()
    try:
        db.fetchval("SELECT 1")
        lat = int((time.time() - t0) * 1000)
        checks.append({"key": "postgres", "label": "PostgreSQL",
                        "status": "ok", "detail": f"OK — {lat} ms", "latency_ms": lat})
    except Exception as exc:
        checks.append({"key": "postgres", "label": "PostgreSQL",
                        "status": "error", "detail": str(exc)[:80], "latency_ms": None})

    # 3 · pgvector / RAG
    try:
        t0 = time.time()
        has_pgv  = db.fetchval("SELECT COUNT(*) FROM pg_extension WHERE extname='vector'")
        n_docs   = db.fetchval("SELECT COUNT(*) FROM rag_documents WHERE is_active = true") or 0
        n_chunks = db.fetchval("SELECT COUNT(*) FROM rag_chunks") or 0
        lat = int((time.time() - t0) * 1000)
        if not has_pgv:
            checks.append({"key": "pgvector", "label": "pgvector (RAG)",
                            "status": "warn", "detail": "Extensão não instalada no Postgres", "latency_ms": lat})
        else:
            d_lbl = f"{n_docs} doc{'s' if n_docs != 1 else ''} ativo{'s' if n_docs != 1 else ''}"
            c_lbl = f"{n_chunks} chunk{'s' if n_chunks != 1 else ''}"
            checks.append({"key": "pgvector", "label": "pgvector (RAG)",
                            "status": "ok", "detail": f"{d_lbl} · {c_lbl}", "latency_ms": lat})
    except Exception as exc:
        checks.append({"key": "pgvector", "label": "pgvector (RAG)",
                        "status": "error", "detail": str(exc)[:80], "latency_ms": None})

    # 4 · Google Calendar
    if CALENDAR_EMBED_URL:
        checks.append({"key": "calendar", "label": "Google Calendar",
                        "status": "ok", "detail": "Configurado", "latency_ms": None})
    else:
        checks.append({"key": "calendar", "label": "Google Calendar",
                        "status": "warn", "detail": "Não configurado — defina CALENDAR_EMBED_URL no .env",
                        "latency_ms": None})

    # 5 · WhatsApp (Evolution API)
    if not EVOLUTION_URL or not EVOLUTION_KEY or not EVOLUTION_INSTANCE:
        checks.append({"key": "whatsapp", "label": "WhatsApp (Evolution)",
                        "status": "warn", "detail": "Variáveis EVOLUTION_URL / EVOLUTION_KEY / EVOLUTION_INSTANCE não definidas",
                        "latency_ms": None})
    else:
        try:
            t0 = time.time()
            resp = requests.get(
                f"{EVOLUTION_URL}/instance/connectionState/{EVOLUTION_INSTANCE}",
                headers={"apikey": EVOLUTION_KEY},
                timeout=4,
            )
            lat = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                payload = resp.json()
                state = (payload.get("instance", {}).get("state")
                         or payload.get("state")
                         or "unknown")
                if state == "open":
                    checks.append({"key": "whatsapp", "label": "WhatsApp (Evolution)",
                                    "status": "ok", "detail": f"Conectado — {lat} ms", "latency_ms": lat})
                elif state in ("connecting", "connecting..."):
                    checks.append({"key": "whatsapp", "label": "WhatsApp (Evolution)",
                                    "status": "warn", "detail": f"Conectando... ({lat} ms)", "latency_ms": lat})
                else:
                    checks.append({"key": "whatsapp", "label": "WhatsApp (Evolution)",
                                    "status": "error", "detail": f"Desconectado — state: {state}", "latency_ms": lat})
            else:
                checks.append({"key": "whatsapp", "label": "WhatsApp (Evolution)",
                                "status": "error", "detail": f"Evolution API retornou HTTP {resp.status_code}",
                                "latency_ms": None})
        except requests.exceptions.Timeout:
            checks.append({"key": "whatsapp", "label": "WhatsApp (Evolution)",
                            "status": "error", "detail": "Timeout ao conectar à Evolution API (>4 s)", "latency_ms": None})
        except Exception as exc:
            checks.append({"key": "whatsapp", "label": "WhatsApp (Evolution)",
                            "status": "error", "detail": str(exc)[:80], "latency_ms": None})

    return {
        "uptime_seconds": uptime_secs,
        "checks": checks,
        "checked_at": datetime.now().isoformat(),
    }


# ─── Error Logs ────────────────────────────────────────────────────────────────

_RE_LOG_NEW = re.compile(r"^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\] \[(\w+)\] (.+)$")
_RE_LOG_OLD = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\] (.+)$")
_MOD_KEYS   = ("WEBHOOK", "CALENDAR", "ADMIN", "AI", "SCHEDULER", "LIFESPAN", "RAG", "CHAT")

def _detect_module(msg: str) -> str:
    mu = msg.upper()
    for m in _MOD_KEYS:
        if f"[{m}" in mu or mu.lstrip().startswith(m):
            return m
    return "SYSTEM"

def _detect_level(msg: str) -> str:
    mu = msg.upper()
    if any(k in mu for k in _KW_ERROR):
        return "ERROR"
    if any(k in mu for k in _KW_WARN):
        return "WARN"
    return "INFO"

@app.get("/admin/error-logs", dependencies=[Depends(verify_token)])
async def get_error_logs(
    level: str = "all",
    limit: int = 200,
    search: str = "",
    since_hours: int = 0,
):
    """Retorna entradas do debug.log com filtro de nível, busca e janela temporal."""
    try:
        with open(_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        raw_lines = []

    today_str = datetime.now().strftime("%Y-%m-%d")
    since_dt  = datetime.now() - timedelta(hours=since_hours) if since_hours > 0 else None

    entries: list[dict] = []
    count_error = count_warn = count_info = 0

    # Totais globais (percorre todas as linhas)
    for raw in raw_lines:
        if   "[ERROR]" in raw: count_error += 1
        elif "[WARN]"  in raw: count_warn  += 1
        elif "[INFO]"  in raw: count_info  += 1

    # Monta entradas filtradas (ordem reversa = mais recentes primeiro)
    search_l = search.lower()
    for raw in reversed(raw_lines):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue

        m = _RE_LOG_NEW.match(raw)
        if m:
            date_str, time_str, lvl, msg = m.groups()
        else:
            m2 = _RE_LOG_OLD.match(raw)
            if m2:
                time_str, msg = m2.groups()
                date_str = today_str
                lvl = _detect_level(msg)
            else:
                continue

        # Filtro de nível
        if level != "all" and lvl.lower() != level.lower():
            continue

        # Filtro de janela temporal
        if since_dt:
            try:
                if datetime.fromisoformat(f"{date_str}T{time_str}") < since_dt:
                    break  # ordem reversa → tudo abaixo é mais antigo
            except Exception:
                pass

        # Filtro de busca
        if search_l and search_l not in msg.lower() and search_l not in raw.lower():
            continue

        entries.append({
            "date":    date_str,
            "time":    time_str,
            "level":   lvl,
            "module":  _detect_module(msg),
            "message": msg[:400],
            "raw":     raw[:500],
        })

        if len(entries) >= limit:
            break

    last_error = next((e for e in entries if e["level"] == "ERROR"), None)

    try:
        log_size_kb = os.path.getsize(_LOG_PATH) // 1024
    except Exception:
        log_size_kb = 0

    return {
        "entries":      entries,
        "total_lines":  len(raw_lines),
        "count_error":  count_error,
        "count_warn":   count_warn,
        "count_info":   count_info,
        "last_error_at": f"{last_error['date']} {last_error['time']}" if last_error else None,
        "log_size_kb":  log_size_kb,
        "checked_at":   datetime.now().isoformat(),
    }


@app.post("/admin/error-logs/clear", dependencies=[Depends(verify_token)])
async def clear_error_logs():
    """Apaga o conteúdo do debug.log."""
    try:
        open(_LOG_PATH, "w").close()
        _log("Log limpo pelo operador via painel.", level="INFO")
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Webhook ───────────────────────────────────────────────────────────────────

@app.post("/webhook")
@app.post("/webhook/{event_path:path}")
async def webhook(request: Request, event_path: str = ""):
    data = await request.json()
    if "event" not in data and event_path:
        data["event"] = event_path.replace("-", ".").replace("/", ".").lower()
    event = data.get("event", "")
    _log(f"[EVENTO] {event}")

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
            # Passo 2 → 3: cliente em fluxo de orçamento enviou a imagem da receita
            if _orcamento_state.get(sender, {}).get("step") == "image" and "imageMessage" in message:
                _name = _orcamento_state.pop(sender)["name"]
                add_pending(sender, f"Orcamento solicitado — Nome: {_name}. Cliente enviou imagem da receita. Verificar no chat.")
                _msg_final = "Estamos avaliando e em breve daremos um retorno."
                await asyncio.sleep(_typing_delay(_msg_final))
                await asyncio.to_thread(send_message, sender, _msg_final)
                inject_assistant_message(sender, _msg_final)
                _log(f"[ORCAMENTO] Receita recebida de {_name} ({sender}), pendencia criada.")
                return {"status": "ok"}

            MEDIA_RESPONSES = {
                "audioMessage":    _get_bot_cfg_str("msg_media_audio"),
                "imageMessage":    _get_bot_cfg_str("msg_media_image"),
                "videoMessage":    _get_bot_cfg_str("msg_media_video"),
                "documentMessage": _get_bot_cfg_str("msg_media_document"),
                "stickerMessage":  _get_bot_cfg_str("msg_media_sticker"),
            }
            for media_type, response in MEDIA_RESPONSES.items():
                if media_type in message:
                    send_message(sender, response)
                    inject_assistant_message(sender, response)
                    print(f"[MIDIA] {media_type} recebida de {sender}")
                    return {"status": "ok"}
            return {"status": "ignored"}

        _log(f"MSG de {sender}: {repr(text)}")

        if "/reset" in text.lower():
            _log(f"[RESET] Acionado para {sender}")
            reset_session(sender)
            msg = "✅ Conversa reiniciada. Como posso ajudar?"
            send_message(sender, msg)
            inject_assistant_message(sender, msg)
            return {"status": "ok"}

        # Verifica toggle global da IA (pausa geral via painel)
        if not _ia_global_enabled():
            import session as _sess_wh
            _sess_wh.push(sender, "user", text)
            _sess_wh.save()
            _log(f"[IA GLOBAL PAUSADA] Mensagem de {sender} salva sem resposta (IA desligada globalmente)")
            return {"status": "ok"}

        # Verifica se a IA está pausada para este contato (modo manual do operador)
        if not _is_ia_enabled(sender):
            import session as _sess_wh
            _sess_wh.push(sender, "user", text)
            _sess_wh.save()
            _log(f"[IA PAUSADA] Mensagem de {sender} salva sem resposta automática")
            return {"status": "ok"}

        # Passo 1 → 2: cliente enviou o nome, agora pedir a imagem da receita
        if _orcamento_state.get(sender, {}).get("step") == "name":
            _orcamento_state[sender] = {"step": "image", "name": text.strip()}
            _ask_img = "Obrigada! Agora pode enviar a foto da sua receita para que possamos avaliar."
            await asyncio.to_thread(send_message, sender, _ask_img)
            inject_assistant_message(sender, _ask_img)
            _log(f"[ORCAMENTO] Nome recebido: {text.strip()} — aguardando imagem ({sender})")
            return {"status": "ok"}

        # Passo 0 → 1: cliente pediu orçamento → perguntar o nome completo
        _ORCAMENTO_KEYWORDS = ("orçamento", "orcamento")
        if any(k in text.lower() for k in _ORCAMENTO_KEYWORDS):
            _orcamento_state[sender] = {"step": "name"}
            _ask_name = "Claro! Para te fazer um orçamento, preciso primeiro do seu nome completo. Como devo registrar?"
            await asyncio.to_thread(send_message, sender, _ask_name)
            inject_assistant_message(sender, _ask_name)
            _log(f"[ORCAMENTO] Aguardando nome do cliente — {sender}")
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
                msg = (
                    "Não consegui entender sua resposta.\n"
                    "Por favor, responda apenas:\n"
                    "*SIM* para confirmar sua presença\n"
                    "*NÃO* caso precise reagendar"
                )
                send_message(sender, msg)
                inject_assistant_message(sender, msg)
                return {"status": "ok"}

        text_clean = ''.join(c for c in text if c.isprintable()).strip().lower()
        _log(f"[DEBUG] repr={repr(text)} | clean={repr(text_clean)}")
        if text_clean == "/reset":
            _log(f"[RESET-CLEAN] Acionado para {sender}")
            reset_session(sender)
            msg = "✅ Conversa reiniciada. Como posso ajudar?"
            send_message(sender, msg)
            inject_assistant_message(sender, msg)
            return {"status": "ok"}

        mark_response_received(sender)
        await _sse_broadcast("new_message", {
            "phone": sender,
            "content": text[:80],
            "role": "user",
            "sent_by_operator": False,
        })

        if has_empty_session(sender) and _is_campaign_response(text_clean):
            if _get_bot_cfg_bool("campaign_enabled", True):
                campaign_msg = _get_bot_cfg_str("campaign_message")
                inject_assistant_message(sender, campaign_msg)
                _log(f"[CAMPANHA] Contexto injetado para {sender}")

        try:
            _detect_slot_selection(sender, text)
            reply = await asyncio.to_thread(get_response, sender, text)

            pending_match = PENDING_MARKER.search(reply)
            if pending_match:
                add_pending(sender, pending_match.group(1).strip())
                reply = PENDING_MARKER.sub("", reply).strip()

            slot_match = SLOT_MARKER.search(reply)
            if slot_match:
                import session as _sess_slot
                _sess_slot.set_pending_slot(sender, slot_match.group(1), slot_match.group(2))
                reply = SLOT_MARKER.sub("", reply).strip()
                _log(f"[SLOT] {sender} selecionou {slot_match.group(2)} em {slot_match.group(1)}")

            reply = _restore_breaks(reply)

            parts = [p.strip() for p in reply.split("[BREAK]") if p.strip()]

            await asyncio.sleep(1.8)

            for i, part in enumerate(parts):
                if i > 0:
                    await asyncio.sleep(_typing_delay(parts[i]))

                match = MARKER.search(part)
                if match:
                    name = match.group(1).strip()
                    date_str = match.group(2)
                    time_str = match.group(3)

                    # ── Marcador sem nome: pedir o nome ao cliente ────────────
                    if not name:
                        _log(f"[AGENDAR SEM NOME] {sender} escolheu {date_str} {time_str} mas nome vazio")
                        pre_text = MARKER.sub("", part).strip()
                        if pre_text:
                            await asyncio.to_thread(send_message, sender, pre_text)
                        ask_msg = "Para finalizar o agendamento, preciso do seu nome completo. Como devo registrar?"
                        await asyncio.to_thread(send_message, sender, ask_msg)
                        inject_assistant_message(sender, ask_msg)
                        inject_assistant_message(
                            sender,
                            f"[Sistema: nome ainda não informado. "
                            f"Quando o cliente fornecer o nome, confirme os dados e gere "
                            f"[AGENDAR:NOME|{date_str}|{time_str}].]"
                        )
                        continue

                    try:
                        hour, minute = map(int, time_str.split(":"))
                        dt = datetime.fromisoformat(date_str).replace(hour=hour, minute=minute)
                    except ValueError as e:
                        print(f"[VALIDACAO] Data/hora invalida no marcador: {date_str} {time_str} — {e}")
                        send_message(sender, part.split("[AGENDAR:")[0].strip())
                        continue

                    # Cliente já confirmou via Liza — salva o agendamento diretamente
                    pre_text = MARKER.sub("", part).strip()
                    if pre_text:
                        await asyncio.to_thread(send_message, sender, pre_text)
                    _auto_cancel_st = ("scheduled", "day_reminder_sent", "reminder_sent", "response_received")
                    for _prev in [a for a in load_appointments() if a["phone"] == sender and a["status"] in _auto_cancel_st]:
                        try:
                            cancel_event(_prev.get("event_id", ""))
                        except Exception as _ce:
                            _log(f"[CALENDAR ERROR] cancel prev: {_ce}")
                        cancel_appointment(sender, _prev["date"], _prev["time"])
                    try:
                        _eid = await asyncio.to_thread(create_event, name, date_str, time_str, sender)
                    except Exception as _ce:
                        _log(f"[CALENDAR ERROR] create_event: {_ce}")
                        _eid = ""
                    add_appointment(sender, name, date_str, time_str, _eid)
                    clients_mod.upsert_from_appointment(sender, name, date_str)
                    _dt_conf = datetime.fromisoformat(date_str)
                    _ddisplay = f"{DIAS[_dt_conf.weekday()]} {_dt_conf.day:02d}/{_dt_conf.month:02d}/{_dt_conf.year}"
                    _tdisplay = time_str.replace(":", "h")
                    _conf_parts = [
                        (
                            f"Agendamento confirmado! 📝\n"
                            f"Tipo: {_get_bot_cfg_str('confirmation_appointment_type')}\n"
                            f"➡️ {_ddisplay} às {_tdisplay}\nCliente: {name}"
                        ),
                        f"📍 Nosso endereço: {_get_bot_cfg_str('confirmation_address')}",
                        f"📣 {_get_bot_cfg_str('confirmation_footer')}",
                    ]
                    for _ci, _cp in enumerate(_conf_parts):
                        if _ci > 0:
                            await asyncio.sleep(_typing_delay(_cp))
                        await asyncio.to_thread(send_message, sender, _cp)
                        inject_assistant_message(sender, _cp)
                    inject_assistant_message(
                        sender,
                        f"Agendamento de {name} em {date_str} às {time_str} registrado no sistema. "
                        f"Não vou gerar [AGENDAR:...] novamente nesta conversa."
                    )
                    _log(f"[AGENDADO] {name} | {date_str} {time_str} — {sender}")
                    import session as _sess_clr
                    _sess_clr.clear_pending_slot(sender)
                else:
                    clean = MARKER.sub("", part).strip()
                    if clean:
                        await asyncio.to_thread(send_message, sender, clean)

            print(f"LenzÓtica respondeu: {reply[:100]}")

        except Exception as e:
            error_info = f"{type(e).__name__}: {e}"
            _log(f"[WEBHOOK ERROR] {sender} — {error_info}")
            send_message(sender, "Um momento, por favor.")
            add_pending(sender, f"Erro no processamento da mensagem — {error_info}")

    return {"status": "ok"}
