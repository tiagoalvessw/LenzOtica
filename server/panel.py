from datetime import datetime
import json

_STATUS = {
    "scheduled":          ("scheduled",          "Aguardando"),
    "day_reminder_sent":  ("day_reminder_sent",  "Lembrete 1 dia"),
    "reminder_sent":      ("reminder_sent",       "Lembrete 1h"),
    "response_received":  ("response_received",   "Respondeu"),
    "confirmed":          ("confirmed",           "Confirmado"),
    "attended":           ("attended",            "Compareceu"),
    "no_show":            ("no_show",             "Não veio"),
    "completed":          ("completed",           "Concluído"),
    "cancelled":          ("cancelled",           "Cancelado"),
}


def _faltam(date_str: str, time_str: str, status: str):
    if status in ("cancelled", "no_show", "completed"):
        return "—", ""
    try:
        apt_dt = datetime.fromisoformat(f"{date_str}T{time_str}:00")
        secs = (apt_dt - datetime.now()).total_seconds()
        if secs < 0:
            return "Passou", "time-past"
        mins = int(secs / 60)
        if mins < 60:
            return f"em {mins}min", "time-soon"
        hours = mins // 60
        rem = mins % 60
        if hours < 24:
            label = f"em {hours}h" + (f" {rem}min" if rem else "")
            return label, "time-soon" if hours < 2 else "time-ok"
        days = hours // 24
        return f"em {days} dia{'s' if days > 1 else ''}", "time-ok"
    except Exception:
        return "—", ""


def render_panel(agendamentos: list, calendar_embed_url: str = "", admin_token: str = "", pending_items: list = None) -> str:
    today = datetime.now().date().isoformat()
    rows = ""

    for a in agendamentos:
        try:
            dt = datetime.fromisoformat(a["date"])
            data_br = f"{dt.day:02d}/{dt.month:02d}/{dt.year}"
        except Exception:
            data_br = a["date"]

        is_today = a["date"] == today
        hoje_badge = '<span class="hoje-tag">HOJE</span>' if is_today else ""
        row_cls = "row-today" if is_today else ""
        status_cls, status_label = _STATUS.get(a["status"], (a["status"], a["status"]))
        phone = a["phone"].replace("@s.whatsapp.net", "").replace("@lid", "")
        faltam_txt, faltam_cls = _faltam(a["date"], a["time"], a["status"])

        safe_name = a["name"].replace('"', "&quot;")
        actions = ""
        st = a["status"]
        if st == "cancelled":
            actions += '<button class="action-btn recover-btn" onclick="recoverApt(this)" title="Recuperar agendamento"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar</button>'
            actions += '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)" title="Encerrar protocolo"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>'
        elif st == "completed":
            actions = '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)" title="Encerrar protocolo"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>'
        elif st == "no_show":
            actions += '<button class="action-btn recover-btn" onclick="rescheduleApt(this)" title="Remarcar"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> Remarcar</button>'
            actions += '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)" title="Encerrar protocolo"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>'
        elif st == "attended":
            actions += '<button class="action-btn confirm-btn" onclick="openCompleteModal(this)" title="Concluir atendimento"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Concluir</button>'
        elif st == "confirmed":
            actions += '<button class="action-btn confirm-btn" onclick="markAttended(this)" title="Marcar comparecimento"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="23 11 20 14 18 12"/></svg> Compareceu</button>'
            actions += '<button class="action-btn cancel-btn" onclick="openConfirmCancel(this)" title="Cancelar agendamento"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>'
        else:
            if st in ("scheduled", "day_reminder_sent"):
                actions += '<button class="action-btn remind-btn" onclick="sendRemind(this)" title="Enviar lembrete"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button>'
            actions += '<button class="action-btn edit-btn" onclick="openEditModal(this)" title="Editar agendamento"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button>'
            actions += '<button class="action-btn cancel-btn" onclick="openConfirmCancel(this)" title="Cancelar agendamento"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>'

        actions += '<button class="action-btn reset-session-btn" onclick="resetSession(this)" title="Resetar historico da IA"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Resetar IA</button>'

        rows += (
            f'<tr data-status="{a["status"]}" data-phone="{a["phone"]}" data-date="{a["date"]}" data-time="{a["time"]}" data-name="{safe_name}" class="{row_cls}">'
            f'<td><span class="client-name">{a["name"]}</span></td>'
            f'<td><span class="phone-num">{phone}</span></td>'
            f'<td><div class="date-cell">{data_br}{hoje_badge}</div></td>'
            f'<td><span class="time-chip">{a["time"]}</span></td>'
            f'<td><span class="faltam {faltam_cls}">{faltam_txt}</span></td>'
            f'<td><span class="badge {status_cls}">{status_label}</span></td>'
            f'<td><div class="actions-cell">{actions}</div></td>'
            f"</tr>\n"
        )

    if pending_items is None:
        pending_items = []
    total           = len(agendamentos)
    hoje_dia_count  = sum(1 for a in agendamentos if a["date"] == today and a["status"] not in ("cancelled", "no_show", "completed"))
    confirmados_tab = sum(1 for a in agendamentos if a["status"] in ("confirmed", "attended"))
    cancelados_tab  = sum(1 for a in agendamentos if a["status"] in ("cancelled", "no_show"))
    concluidos_tab  = sum(1 for a in agendamentos if a["status"] == "completed")
    pendente_tab    = len(pending_items)
    pending_json    = json.dumps(pending_items).replace("</", "<\\/")

    body = rows if agendamentos else '<tr><td colspan="7" class="empty-row"><div class="empty-state"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:.3;margin-bottom:.75rem"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg><div>Nenhum agendamento encontrado.</div></div></td></tr>'

    if calendar_embed_url:
        if "mode=" not in calendar_embed_url:
            sep = "&" if "?" in calendar_embed_url else "?"
            _embed_url = calendar_embed_url + sep + "mode=WEEK"
        else:
            import re as _re
            _embed_url = _re.sub(r"mode=[^&]*", "mode=WEEK", calendar_embed_url)
        calendar_content = (
            f'<iframe src="{_embed_url}" style="border:0;width:100%;height:680px;display:block;"'
            ' frameborder="0" scrolling="no" allowfullscreen></iframe>'
        )
    else:
        calendar_content = """\
      <div class="cal-empty">
        <div class="cal-empty-icon">&#128197;</div>
        <strong>Agenda nao configurada</strong>
        <p>Adicione ao <code>server/.env</code>:</p>
        <code>CALENDAR_EMBED_URL=https://calendar.google.com/calendar/embed?src=...</code>
      </div>"""

    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LenzOtica — Painel</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script>document.documentElement.setAttribute("data-theme",localStorage.getItem("theme")||"light");</script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --primary:      #2563eb;
      --primary-dark: #1d4ed8;
      --primary-glow: rgba(37,99,235,.15);
      --bg:           #f1f5f9;
      --surface:      #ffffff;
      --surface2:     #f8fafc;
      --text:         #0f172a;
      --text2:        #475569;
      --muted:        #94a3b8;
      --border:       #e2e8f0;
      --border2:      #cbd5e1;
      --shadow-sm:    0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
      --shadow:       0 4px 16px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.04);
      --shadow-lg:    0 10px 40px rgba(0,0,0,.14), 0 2px 8px rgba(0,0,0,.06);
      --radius:       12px;
      --radius-sm:    8px;
    }}

    [data-theme="dark"] {{
      --bg:        #0f172a;
      --surface:   #1e293b;
      --surface2:  #162032;
      --text:      #f1f5f9;
      --text2:     #94a3b8;
      --muted:     #64748b;
      --border:    #334155;
      --border2:   #475569;
      --shadow-sm: 0 1px 3px rgba(0,0,0,.3);
      --shadow:    0 4px 16px rgba(0,0,0,.35);
      --shadow-lg: 0 10px 40px rgba(0,0,0,.5);
    }}

    body {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      font-size: 14px;
      line-height: 1.5;
    }}

    /* ── HEADER ── */
    header {{
      background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
      color: #fff;
      padding: 0 2rem;
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 12px rgba(37,99,235,.35);
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .header-left  {{ display: flex; align-items: center; gap: .9rem; }}
    .header-right {{ display: flex; align-items: center; gap: 1rem; }}
    .logo-wrap img {{ height: 40px; width: auto; border-radius: 6px; }}
    .brand      {{ font-size: 1.05rem; font-weight: 700; letter-spacing: -.02em; }}
    .brand-sub  {{ font-size: .7rem; opacity: .65; margin-top: 1px; letter-spacing: .02em; }}
    .header-sep {{ width: 1px; height: 28px; background: rgba(255,255,255,.2); margin: 0 .25rem; }}

    .refresh-wrap {{ text-align: right; font-size: .72rem; opacity: .75; line-height: 1.7; }}

    #theme-btn {{
      background: rgba(255,255,255,.12);
      border: 1px solid rgba(255,255,255,.2);
      color: #fff;
      cursor: pointer;
      padding: .38rem .5rem;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background .15s;
    }}
    #theme-btn:hover {{ background: rgba(255,255,255,.22); }}

    /* ── MAIN LAYOUT ── */
    main {{ padding: 1.5rem 2rem; max-width: 1600px; margin: 0 auto; }}

    .layout {{
      display: flex;
      align-items: start;
      gap: 0;
    }}
    .layout-left {{
      flex: 1;
      min-width: 0;
      padding-right: 1.5rem;
    }}
    .resize-handle {{
      width: 10px;
      flex-shrink: 0;
      cursor: col-resize;
      position: relative;
      align-self: stretch;
      border-radius: 4px;
      transition: background .15s;
      margin: 0 .1rem;
    }}
    .resize-handle:hover, .resize-handle.dragging {{
      background: var(--border2);
    }}
    .resize-handle::after {{
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 3px;
      height: 36px;
      border-radius: 99px;
      background: var(--border2);
      transition: background .15s;
    }}
    .resize-handle:hover::after, .resize-handle.dragging::after {{
      background: var(--primary);
    }}
    .layout-right {{
      width: 400px;
      min-width: 260px;
      max-width: 900px;
      flex-shrink: 0;
      position: sticky;
      top: 80px;
    }}

    /* ── TAB NAV (substitui os cards de resumo) ── */
    .tab-nav {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: .875rem;
      margin-bottom: 1.25rem;
    }}
    .tab-nav .tab {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.1rem 1.2rem;
      box-shadow: var(--shadow-sm);
      text-align: left;
      color: var(--text);
      position: relative;
      overflow: hidden;
      transition: transform .15s, box-shadow .15s, background .12s, color .12s;
    }}
    .tab-nav .tab::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      border-radius: var(--radius) var(--radius) 0 0;
    }}
    .tab-nav .tab[data-f="day"]::before       {{ background: var(--primary); }}
    .tab-nav .tab[data-f="confirmed"]::before {{ background: #059669; }}
    .tab-nav .tab[data-f="cancelled"]::before {{ background: #dc2626; }}
    .tab-nav .tab[data-f="completed"]::before {{ background: #0891b2; }}
    .tab-nav .tab[data-f="all"]::before       {{ background: #64748b; }}
    .tab-nav .tab[data-f="pending"]::before   {{ background: #d97706; }}
    .tab-nav .tab:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow);
      background: var(--surface);
      border-color: var(--border2);
      color: var(--text);
    }}
    .tab-nav .tab:active  {{ transform: translateY(0); }}
    .tab-nav .tab.active  {{ color: #fff; border-color: transparent; }}
    .tab-nav .tab[data-f="day"].active       {{ background: var(--primary); }}
    .tab-nav .tab[data-f="confirmed"].active {{ background: #059669; }}
    .tab-nav .tab[data-f="cancelled"].active {{ background: #dc2626; }}
    .tab-nav .tab[data-f="completed"].active {{ background: #0891b2; }}
    .tab-nav .tab[data-f="all"].active       {{ background: #64748b; }}
    .tab-nav .tab[data-f="pending"].active   {{ background: #d97706; }}
    .tab-nav .num {{
      display: block;
      font-size: 1.75rem;
      font-weight: 700;
      line-height: 1;
      letter-spacing: -.03em;
      margin-bottom: .3rem;
    }}
    .tab-nav .lbl {{
      display: block;
      font-size: .68rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .06em;
      opacity: .7;
    }}

    /* ── TABLE PANEL ── */
    .panel {{
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      border: 1px solid var(--border);
      overflow: hidden;
    }}
    .panel-toolbar {{
      padding: .875rem 1.25rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: .75rem;
      flex-wrap: wrap;
      background: var(--surface2);
    }}
    .search-wrap {{
      position: relative;
      flex: 1;
      min-width: 200px;
    }}
    .search-icon {{
      position: absolute;
      left: .7rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--muted);
      pointer-events: none;
    }}
    #search {{
      width: 100%;
      padding: .5rem .8rem .5rem 2.2rem;
      border: 1px solid var(--border2);
      border-radius: var(--radius-sm);
      font-size: .85rem;
      font-family: inherit;
      background: var(--surface);
      color: var(--text);
      outline: none;
      transition: border-color .15s, box-shadow .15s;
    }}
    #search::placeholder {{ color: var(--muted); }}
    #search:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }}
    [data-theme="dark"] #search {{ background: var(--surface); color: var(--text); }}

    .tabs {{ display: flex; gap: .25rem; flex-wrap: wrap; }}
    .tab {{
      padding: .38rem .85rem;
      border-radius: 6px;
      font-size: .78rem;
      cursor: pointer;
      border: 1px solid transparent;
      color: var(--text2);
      background: none;
      font-weight: 500;
      font-family: inherit;
      transition: background .12s, color .12s, border-color .12s;
    }}
    .tab:hover  {{ background: var(--bg); color: var(--text); border-color: var(--border2); }}
    .tab.active {{ background: var(--primary); color: #fff; border-color: var(--primary); }}
    .tab .cnt   {{ opacity: .7; margin-left: .25rem; font-size: .72rem; }}

    .btn-new {{
      padding: .44rem 1rem;
      border-radius: var(--radius-sm);
      font-size: .82rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      border: none;
      background: var(--primary);
      color: #fff;
      white-space: nowrap;
      display: flex;
      align-items: center;
      gap: .35rem;
      transition: opacity .15s, transform .1s;
    }}
    .btn-new:hover  {{ opacity: .88; transform: translateY(-1px); }}
    .btn-new:active {{ transform: translateY(0); }}

    /* ── TABLE ── */
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 700px; }}
    thead th {{
      background: var(--surface2);
      text-align: left;
      padding: .7rem 1.1rem;
      font-size: .68rem;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      font-weight: 700;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}
    tbody td {{
      padding: .8rem 1.1rem;
      border-bottom: 1px solid var(--border);
      font-size: .855rem;
      vertical-align: middle;
    }}
    tbody tr:last-child td {{ border-bottom: none; }}
    tbody tr {{ transition: background .1s; }}
    tbody tr:hover td {{ background: var(--surface2); }}
    tbody tr.row-today td {{ background: #eff6ff; }}
    tbody tr.row-today:hover td {{ background: #dbeafe; }}
    [data-theme="dark"] tbody tr:hover    td {{ background: #1e2d40; }}
    [data-theme="dark"] tbody tr.row-today    td {{ background: #172554; }}
    [data-theme="dark"] tbody tr.row-today:hover td {{ background: #1e3a5f; }}

    .client-name {{ font-weight: 600; color: var(--text); }}
    .phone-num   {{ font-size: .8rem; color: var(--text2); font-family: 'SF Mono', 'Fira Code', monospace; letter-spacing: .02em; }}
    .date-cell   {{ display: flex; align-items: center; gap: .4rem; white-space: nowrap; }}
    .time-chip   {{
      display: inline-block;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 5px;
      padding: .15rem .5rem;
      font-size: .8rem;
      font-weight: 600;
      color: var(--text2);
      letter-spacing: .02em;
    }}
    .faltam      {{ font-size: .8rem; font-weight: 500; }}
    .time-ok     {{ color: #059669; }}
    .time-soon   {{ color: #d97706; }}
    .time-past   {{ color: var(--muted); }}

    .hoje-tag {{
      background: var(--primary);
      color: #fff;
      font-size: .58rem;
      font-weight: 700;
      padding: .12rem .4rem;
      border-radius: 4px;
      vertical-align: middle;
      letter-spacing: .04em;
    }}

    /* ── BADGES ── */
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: .22rem .7rem;
      border-radius: 999px;
      font-size: .72rem;
      font-weight: 600;
      white-space: nowrap;
      letter-spacing: .02em;
    }}
    .badge.scheduled         {{ background: #fef9c3; color: #854d0e; border: 1px solid #fde68a; }}
    .badge.day_reminder_sent {{ background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }}
    .badge.reminder_sent     {{ background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }}
    .badge.response_received {{ background: #ede9fe; color: #5b21b6; border: 1px solid #ddd6fe; }}
    .badge.confirmed         {{ background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }}
    .badge.attended          {{ background: #ccfbf1; color: #0f766e; border: 1px solid #99f6e4; }}
    .badge.no_show           {{ background: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }}
    .badge.completed         {{ background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }}
    .badge.cancelled         {{ background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }}

    [data-theme="dark"] .badge.scheduled         {{ background: #2a1c00; color: #fbbf24; border-color: #78350f; }}
    [data-theme="dark"] .badge.day_reminder_sent {{ background: #1e3a5f; color: #93c5fd; border-color: #1e40af; }}
    [data-theme="dark"] .badge.reminder_sent     {{ background: #1e1b4b; color: #a5b4fc; border-color: #3730a3; }}
    [data-theme="dark"] .badge.response_received {{ background: #2e1065; color: #c4b5fd; border-color: #5b21b6; }}
    [data-theme="dark"] .badge.confirmed         {{ background: #052e16; color: #6ee7b7; border-color: #065f46; }}
    [data-theme="dark"] .badge.attended          {{ background: #042f2e; color: #5eead4; border-color: #0f766e; }}
    [data-theme="dark"] .badge.no_show           {{ background: #431407; color: #fdba74; border-color: #9a3412; }}
    [data-theme="dark"] .badge.completed         {{ background: #082f49; color: #7dd3fc; border-color: #0369a1; }}
    [data-theme="dark"] .badge.cancelled         {{ background: #450a0a; color: #fca5a5; border-color: #991b1b; }}

    /* ── ACTION BUTTONS ── */
    .actions-cell {{ display: flex; gap: .35rem; align-items: center; flex-wrap: wrap; }}
    .action-btn {{
      display: inline-flex;
      align-items: center;
      gap: .28rem;
      padding: .3rem .65rem;
      border-radius: 6px;
      font-size: .72rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      border: 1px solid transparent;
      transition: opacity .15s, transform .1s;
      white-space: nowrap;
    }}
    .action-btn:hover    {{ opacity: .82; transform: translateY(-1px); }}
    .action-btn:active   {{ transform: translateY(0); }}
    .action-btn:disabled {{ opacity: .4; cursor: not-allowed; transform: none; }}
    .remind-btn  {{ background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }}
    .edit-btn    {{ background: #f5f3ff; color: #5b21b6; border-color: #ddd6fe; }}
    .cancel-btn  {{ background: #fef2f2; color: #b91c1c; border-color: #fecaca; }}
    .recover-btn {{ background: #ecfdf5; color: #065f46; border-color: #a7f3d0; }}
    .confirm-btn {{ background: #f0fdf4; color: #15803d; border-color: #bbf7d0; }}
    [data-theme="dark"] .remind-btn  {{ background: #1e3a5f; color: #93c5fd; border-color: #1e40af; }}
    [data-theme="dark"] .edit-btn    {{ background: #1e1b4b; color: #a5b4fc; border-color: #3730a3; }}
    [data-theme="dark"] .cancel-btn  {{ background: #450a0a; color: #fca5a5; border-color: #7f1d1d; }}
    [data-theme="dark"] .recover-btn {{ background: #052e16; color: #6ee7b7; border-color: #065f46; }}
    [data-theme="dark"] .confirm-btn {{ background: #052e16; color: #4ade80; border-color: #15803d; }}
    .close-protocol-btn {{ background: #f1f5f9; color: #475569; border-color: #cbd5e1; }}
    [data-theme="dark"] .close-protocol-btn {{ background: #1e293b; color: #94a3b8; border-color: #334155; }}
    .reset-session-btn  {{ background: #f8fafc; color: #64748b; border-color: #e2e8f0; }}
    [data-theme="dark"] .reset-session-btn  {{ background: #0f172a; color: #64748b; border-color: #1e293b; }}

    .empty-row {{ text-align: center; padding: 3rem 1rem; }}
    .empty-state {{ display: flex; flex-direction: column; align-items: center; color: var(--muted); font-size: .88rem; }}

    /* ── CALENDAR PANEL ── */
    .calendar-panel {{
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      border: 1px solid var(--border);
      overflow: hidden;
    }}
    .calendar-header {{
      padding: .875rem 1.25rem;
      font-size: .82rem;
      font-weight: 600;
      border-bottom: 1px solid var(--border);
      color: var(--text);
      display: flex;
      align-items: center;
      gap: .5rem;
      background: var(--surface2);
    }}
    .calendar-header .cal-dot {{
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #4285f4;
      flex-shrink: 0;
    }}
    .cal-empty {{
      padding: 2.5rem 1.5rem;
      text-align: center;
      color: var(--muted);
      font-size: .83rem;
      line-height: 1.8;
    }}
    .cal-empty-icon {{ font-size: 2.2rem; margin-bottom: .75rem; }}
    .cal-empty code {{
      display: inline-block;
      background: var(--bg);
      padding: .2rem .5rem;
      border-radius: 5px;
      font-size: .72rem;
      word-break: break-all;
      margin: .2rem 0;
      border: 1px solid var(--border);
    }}

    /* ── MODALS ── */
    #modal-new, #modal-edit, #modal-complete {{
      display: none;
      position: fixed;
      z-index: 1000;
      width: 460px;
      max-width: 92vw;
      background: var(--surface);
      color: var(--text);
      border-radius: var(--radius);
      box-shadow: var(--shadow-lg);
      border: 1px solid var(--border);
    }}
    .modal-drag-handle {{
      padding: .9rem 1.25rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: grab;
      user-select: none;
      border-radius: var(--radius) var(--radius) 0 0;
      background: var(--surface2);
    }}
    .modal-drag-handle:active {{ cursor: grabbing; }}
    .modal-drag-hint {{ font-size: .68rem; color: var(--muted); display: flex; align-items: center; gap: .3rem; }}
    .modal-body      {{ padding: 1.25rem 1.5rem 1.5rem; }}
    .modal-title     {{ font-size: 1rem; font-weight: 700; }}

    .form-group       {{ margin-bottom: .9rem; }}
    .form-group label {{
      display: block;
      font-size: .72rem;
      font-weight: 600;
      color: var(--text2);
      margin-bottom: .35rem;
      text-transform: uppercase;
      letter-spacing: .05em;
    }}
    .form-group input {{
      width: 100%;
      padding: .52rem .8rem;
      border: 1px solid var(--border2);
      border-radius: var(--radius-sm);
      font-size: .9rem;
      font-family: inherit;
      background: var(--surface);
      color: var(--text);
      outline: none;
      transition: border-color .15s, box-shadow .15s;
    }}
    .form-group input::placeholder {{ color: var(--muted); }}
    .form-group input:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }}
    .form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }}

    .modal-footer {{
      display: flex;
      justify-content: flex-end;
      gap: .5rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      margin-top: 1.1rem;
    }}
    .btn-secondary {{
      padding: .48rem 1rem;
      border-radius: var(--radius-sm);
      font-size: .84rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      border: 1px solid var(--border2);
      background: var(--surface);
      color: var(--text2);
      transition: background .12s;
    }}
    .btn-secondary:hover {{ background: var(--bg); }}
    .btn-primary {{
      padding: .48rem 1.1rem;
      border-radius: var(--radius-sm);
      font-size: .84rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      border: none;
      background: var(--primary);
      color: #fff;
      transition: opacity .12s, transform .1s;
    }}
    .btn-primary:hover    {{ opacity: .88; transform: translateY(-1px); }}
    .btn-primary:active   {{ transform: translateY(0); }}
    .btn-primary:disabled {{ opacity: .5; cursor: not-allowed; transform: none; }}

    /* ── CONFIRM MODAL ── */
    .confirm-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      z-index: 2000;
      align-items: center;
      justify-content: center;
    }}
    .confirm-overlay.open {{ display: flex; }}
    .confirm-backdrop {{
      position: absolute;
      inset: 0;
      background: rgba(0,0,0,.5);
      backdrop-filter: blur(3px);
    }}
    .confirm-box {{
      position: relative;
      z-index: 1;
      background: var(--surface);
      border-radius: var(--radius);
      padding: 1.75rem;
      max-width: 400px;
      width: 90%;
      box-shadow: var(--shadow-lg);
      border: 1px solid var(--border);
    }}
    .confirm-icon {{
      width: 44px; height: 44px;
      border-radius: 10px;
      background: #fef2f2;
      display: flex; align-items: center; justify-content: center;
      color: #dc2626;
      margin-bottom: 1rem;
    }}
    [data-theme="dark"] .confirm-icon {{ background: #450a0a; }}
    .confirm-title {{ font-size: 1rem; font-weight: 700; margin-bottom: .4rem; }}
    .confirm-msg   {{ font-size: .86rem; color: var(--text2); line-height: 1.6; margin-bottom: 1.5rem; }}

    /* ── TOAST ── */
    .toast {{
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      padding: .7rem 1.1rem;
      border-radius: 10px;
      font-size: .84rem;
      font-weight: 500;
      font-family: inherit;
      box-shadow: var(--shadow-lg);
      z-index: 3000;
      animation: slide-in .22s cubic-bezier(.16,1,.3,1);
      display: flex;
      align-items: center;
      gap: .5rem;
      max-width: 320px;
    }}
    .toast-ok  {{ background: #065f46; color: #ecfdf5; }}
    .toast-err {{ background: #991b1b; color: #fef2f2; }}
    @keyframes slide-in {{
      from {{ transform: translateX(110%); opacity: 0; }}
      to   {{ transform: translateX(0);    opacity: 1; }}
    }}

    /* ── RESPONSIVE ── */
    @media (max-width: 1250px) {{
      .layout       {{ flex-direction: column; }}
      .layout-left  {{ padding-right: 0; }}
      .layout-right {{ width: 100% !important; min-width: 0; position: static; }}
      .resize-handle {{ display: none; }}
      .tab-nav {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    @media (max-width: 768px) {{
      main   {{ padding: 1rem; }}
      header {{ padding: 0 1rem; }}
      .tab-nav       {{ grid-template-columns: repeat(3, 1fr); }}
      .panel-toolbar {{ gap: .5rem; }}
    }}
    @media (max-width: 480px) {{
      .tab-nav {{ grid-template-columns: repeat(2, 1fr); }}
    }}
  </style>
</head>
<body>

<header>
  <div class="header-left">
    <div class="logo-wrap">
      <img src="/painel/logo" alt="LenzOtica">
    </div>
    <div class="header-sep"></div>
    <div>
      <div class="brand">LenzOtica</div>
      <div class="brand-sub">Painel de Agendamentos</div>
    </div>
  </div>
  <div class="header-right">
    <button id="theme-btn" onclick="toggleTheme()" title="Alternar tema">
      <span id="theme-icon"></span>
    </button>
    <div class="refresh-wrap">
      <div id="ts">—</div>
      <div id="cd" style="font-size:.68rem;opacity:.6;"></div>
    </div>
  </div>
</header>

<main>
  <div class="layout">
    <div class="layout-left">

      <!-- TAB NAV -->
      <div class="tab-nav">
        <button class="tab active" data-f="day"       onclick="setTab(this)">
          <span class="num">{hoje_dia_count}</span>
          <span class="lbl">Atendimento do Dia</span>
        </button>
        <button class="tab"        data-f="confirmed" onclick="setTab(this)">
          <span class="num">{confirmados_tab}</span>
          <span class="lbl">Confirmado</span>
        </button>
        <button class="tab"        data-f="cancelled" onclick="setTab(this)">
          <span class="num">{cancelados_tab}</span>
          <span class="lbl">Cancelado</span>
        </button>
        <button class="tab"        data-f="completed" onclick="setTab(this)">
          <span class="num">{concluidos_tab}</span>
          <span class="lbl">Concluido</span>
        </button>
        <button class="tab"        data-f="all"       onclick="setTab(this)">
          <span class="num">{total}</span>
          <span class="lbl">Geral</span>
        </button>
        <button class="tab"        data-f="pending"   onclick="setTab(this)">
          <span class="num">{pendente_tab}</span>
          <span class="lbl">Pendente</span>
        </button>
      </div>

      <!-- TABLE PANEL -->
      <div class="panel" id="main-panel">
        <div class="panel-toolbar">
          <div class="search-wrap">
            <span class="search-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </span>
            <input id="search" type="text" placeholder="Buscar por nome ou telefone..." oninput="applyFilter()">
          </div>
          <button class="btn-new" onclick="openModal()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Novo agendamento
          </button>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Telefone</th>
                <th>Data</th>
                <th>Hora</th>
                <th>Faltam</th>
                <th>Status</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody id="tbody">{body}</tbody>
          </table>
        </div>
      </div>

      <!-- PENDING SECTION -->
      <div id="pending-section" style="display:none;">
        <div class="panel">
          <div class="panel-toolbar">
            <span style="font-size:.85rem;font-weight:600;color:var(--text)">Pendencias para o operador</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Telefone</th>
                  <th>Observacao</th>
                  <th>Data/Hora</th>
                  <th>Acoes</th>
                </tr>
              </thead>
              <tbody id="pending-tbody"></tbody>
            </table>
          </div>
        </div>
      </div>

    </div><!-- layout-left -->

    <div id="resize-handle" class="resize-handle" title="Arrastar para redimensionar"></div>

    <div class="layout-right">
      <div class="calendar-panel">
        <div class="calendar-header">
          <span class="cal-dot"></span>
          Google Calendar
        </div>
        {calendar_content}
      </div>
    </div>

  </div><!-- layout -->
</main>

<!-- Confirm Cancel Modal -->
<div id="modal-confirm" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeConfirmModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
    </div>
    <h3 class="confirm-title">Cancelar agendamento?</h3>
    <p class="confirm-msg">Tem certeza que deseja cancelar? O agendamento podera ser recuperado depois se necessario.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeConfirmModal()">Voltar</button>
      <button class="btn-primary" onclick="confirmDoCancel()" style="background:#dc2626;">Sim, cancelar</button>
    </div>
  </div>
</div>

<!-- Confirm Dismiss Pending Modal -->
<div id="modal-confirm-dismiss" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeConfirmDismissModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon" style="background:#fff7ed;color:#d97706;">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    </div>
    <h3 class="confirm-title">Descartar aviso?</h3>
    <p class="confirm-msg">O aviso sera removido da lista. O agendamento e a sessao da IA nao serao alterados.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeConfirmDismissModal()">Voltar</button>
      <button class="btn-primary" onclick="confirmDoDismiss()" style="background:#d97706;">Sim, descartar</button>
    </div>
  </div>
</div>

<!-- Confirm Close Protocol Modal -->
<div id="modal-confirm-protocol" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeConfirmProtocolModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon" style="background:#f0f9ff;color:#0369a1;">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
    </div>
    <h3 class="confirm-title">Encerrar protocolo?</h3>
    <p class="confirm-msg">O atendimento sera encerrado e removido do painel. Os dados ficam salvos no historico.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeConfirmProtocolModal()">Voltar</button>
      <button class="btn-primary" onclick="confirmDoCloseProtocol()" style="background:#0369a1;">Sim, encerrar</button>
    </div>
  </div>
</div>

<!-- Complete Modal -->
<div id="modal-complete">
  <div class="modal-drag-handle" id="modal-complete-handle">
    <h2 class="modal-title">Concluir Atendimento</h2>
    <span class="modal-drag-hint">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg>
      Arrastar
    </span>
  </div>
  <div class="modal-body">
    <form id="form-complete" onsubmit="submitComplete(event)">
      <div class="form-group">
        <label>Observacoes (opcional)</label>
        <input type="text" id="complete-notes" placeholder="Ex: Receita emitida, retorno em 6 meses...">
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeCompleteModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-complete">Concluir</button>
      </div>
    </form>
  </div>
</div>

<!-- Edit Modal -->
<div id="modal-edit">
  <div class="modal-drag-handle" id="modal-edit-handle">
    <h2 class="modal-title">Editar Agendamento</h2>
    <span class="modal-drag-hint">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg>
      Arrastar
    </span>
  </div>
  <div class="modal-body">
    <form id="form-edit" onsubmit="submitEdit(event)">
      <div class="form-group">
        <label>Nome completo</label>
        <input type="text" id="edit-name" required>
      </div>
      <div class="form-group">
        <label>Telefone com DDD</label>
        <input type="tel" id="edit-phone" required>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Data</label>
          <input type="date" id="edit-date" required>
        </div>
        <div class="form-group">
          <label>Hora</label>
          <input type="time" id="edit-time" required>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeEditModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-edit">Salvar alteracoes</button>
      </div>
    </form>
  </div>
</div>

<!-- New Appointment Modal -->
<div id="modal-new">
  <div class="modal-drag-handle" id="modal-handle">
    <h2 class="modal-title">Novo Agendamento</h2>
    <span class="modal-drag-hint">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg>
      Arrastar
    </span>
  </div>
  <div class="modal-body">
    <form id="form-new" onsubmit="submitNew(event)">
      <div class="form-group">
        <label>Nome completo</label>
        <input type="text" id="new-name" placeholder="Ex: Maria Silva" required>
      </div>
      <div class="form-group">
        <label>Telefone com DDD</label>
        <input type="tel" id="new-phone" placeholder="48999999999" required>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Data</label>
          <input type="date" id="new-date" required>
        </div>
        <div class="form-group">
          <label>Hora</label>
          <input type="time" id="new-time" required>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-new">Confirmar agendamento</button>
      </div>
    </form>
  </div>
</div>

<script>
  const ADMIN_TOKEN = "{admin_token}";
  const PENDING_ITEMS = {pending_json};
  function authHeaders() {{
    return {{"Content-Type": "application/json", "X-Admin-Token": ADMIN_TOKEN}};
  }}

  /* ── Toast ── */
  function showToast(msg, ok = true) {{
    const t = document.createElement("div");
    t.className = "toast " + (ok ? "toast-ok" : "toast-err");
    t.innerHTML = ok
      ? '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>' + msg
      : '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>' + msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3200);
  }}

  /* ── Confirm cancel ── */
  let _pendingCancelBtn = null;
  function openConfirmCancel(btn) {{
    _pendingCancelBtn = btn;
    document.getElementById("modal-confirm").classList.add("open");
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }}
  function closeConfirmModal() {{
    document.getElementById("modal-confirm").classList.remove("open");
    _pendingCancelBtn = null;
    isPaused = false;
    secs = 30;
  }}
  async function confirmDoCancel() {{
    const btn = _pendingCancelBtn;
    closeConfirmModal();
    if (!btn) return;
    const row = btn.closest("tr");
    btn.disabled = true;
    const res = await fetch("/admin/cancel", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ phone: row.dataset.phone, date: row.dataset.date, time: row.dataset.time }})
    }});
    if (res.ok) {{
      row.dataset.status = "cancelled";
      row.querySelector(".badge").className = "badge cancelled";
      row.querySelector(".badge").textContent = "Cancelado";
      row.querySelector(".actions-cell").innerHTML =
        '<button class="action-btn recover-btn" onclick="recoverApt(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar</button>' +
        '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>';
      row.classList.remove("row-today");
      showToast("Agendamento cancelado.");
      applyFilter();
    }} else {{
      btn.disabled = false;
      showToast("Erro ao cancelar.", false);
    }}
  }}

  /* ── Recover ── */
  async function recoverApt(btn) {{
    const row = btn.closest("tr");
    btn.disabled = true;
    btn.innerHTML = "Recuperando...";
    const res = await fetch("/admin/recover", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ phone: row.dataset.phone, date: row.dataset.date, time: row.dataset.time }})
    }});
    if (res.ok) {{
      row.dataset.status = "scheduled";
      row.querySelector(".badge").className = "badge scheduled";
      row.querySelector(".badge").textContent = "Aguardando";
      row.querySelector(".actions-cell").innerHTML =
        '<button class="action-btn remind-btn" onclick="sendRemind(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button>' +
        '<button class="action-btn edit-btn" onclick="openEditModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button>' +
        '<button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>';
      showToast("Agendamento recuperado!");
      applyFilter();
    }} else {{
      btn.disabled = false;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar';
      showToast("Erro ao recuperar.", false);
    }}
  }}

  /* ── Edit modal ── */
  function openEditModal(btn) {{
    const row = btn.closest("tr");
    document.getElementById("edit-name").value  = row.dataset.name;
    document.getElementById("edit-phone").value = row.dataset.phone.replace("@s.whatsapp.net","").replace("@lid","");
    document.getElementById("edit-date").value  = row.dataset.date;
    document.getElementById("edit-time").value  = row.dataset.time;
    const m = document.getElementById("modal-edit");
    m.dataset.oldPhone = row.dataset.phone;
    m.dataset.oldDate  = row.dataset.date;
    m.dataset.oldTime  = row.dataset.time;
    m._rowRef = row;
    m.style.display = "block";
    if (!m._positioned) {{
      m.style.left = Math.max(0, (window.innerWidth  - m.offsetWidth)  / 2) + "px";
      m.style.top  = Math.max(0, (window.innerHeight - m.offsetHeight) / 2) + "px";
      m._positioned = true;
    }}
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }}
  function closeEditModal() {{
    document.getElementById("modal-edit").style.display = "none";
    isPaused = false;
    secs = 30;
  }}
  async function submitEdit(e) {{
    e.preventDefault();
    const btn = document.getElementById("btn-submit-edit");
    btn.disabled = true;
    btn.textContent = "Salvando...";
    const m = document.getElementById("modal-edit");
    const res = await fetch("/admin/edit", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{
        old_phone: m.dataset.oldPhone,
        old_date:  m.dataset.oldDate,
        old_time:  m.dataset.oldTime,
        name:  document.getElementById("edit-name").value.trim(),
        phone: document.getElementById("edit-phone").value.trim(),
        date:  document.getElementById("edit-date").value,
        time:  document.getElementById("edit-time").value,
      }})
    }});
    if (res.ok) {{
      closeEditModal();
      showToast("Agendamento atualizado!");
      setTimeout(() => location.reload(), 1200);
    }} else {{
      btn.disabled = false;
      btn.textContent = "Salvar alteracoes";
      showToast("Erro ao atualizar.", false);
    }}
  }}

  /* ── Remind ── */
  async function sendRemind(btn) {{
    const row = btn.closest("tr");
    btn.disabled = true;
    btn.innerHTML = "Enviando...";
    const res = await fetch("/admin/remind", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ phone: row.dataset.phone, date: row.dataset.date, time: row.dataset.time }})
    }});
    if (res.ok) {{
      row.dataset.status = "reminder_sent";
      row.querySelector(".badge").className = "badge reminder_sent";
      row.querySelector(".badge").textContent = "Lembrete 1h";
      btn.remove();
      showToast("Lembrete enviado!");
    }} else {{
      btn.disabled = false;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete';
      showToast("Erro ao enviar lembrete.", false);
    }}
  }}

  /* ── New appointment modal ── */
  function openModal() {{
    document.getElementById("form-new").reset();
    const m = document.getElementById("modal-new");
    m.style.display = "block";
    if (!m._positioned) {{
      m.style.left = Math.max(0, (window.innerWidth  - m.offsetWidth)  / 2) + "px";
      m.style.top  = Math.max(0, (window.innerHeight - m.offsetHeight) / 2) + "px";
      m._positioned = true;
    }}
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }}
  function closeModal() {{
    document.getElementById("modal-new").style.display = "none";
    isPaused = false;
    secs = 30;
  }}
  async function submitNew(e) {{
    e.preventDefault();
    const btn = document.getElementById("btn-submit-new");
    btn.disabled = true;
    btn.textContent = "Salvando...";
    const res = await fetch("/admin/appointments", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{
        name:  document.getElementById("new-name").value.trim(),
        phone: document.getElementById("new-phone").value.trim(),
        date:  document.getElementById("new-date").value,
        time:  document.getElementById("new-time").value,
      }})
    }});
    if (res.ok) {{
      closeModal();
      showToast("Agendamento criado!");
      setTimeout(() => location.reload(), 1200);
    }} else {{
      btn.disabled = false;
      btn.textContent = "Confirmar agendamento";
      showToast("Erro ao criar agendamento.", false);
    }}
  }}

  /* ── Tabs & filter ── */
  const TODAY_STR = "{today}";
  const FILTERS = {{
    day:       row => row.dataset.date === TODAY_STR && !["cancelled","no_show","completed"].includes(row.dataset.status),
    confirmed: row => ["confirmed","attended"].includes(row.dataset.status),
    cancelled: row => ["cancelled","no_show"].includes(row.dataset.status),
    completed: row => row.dataset.status === "completed",
    all:       ()  => true,
  }};
  let cur = "day";

  function setTab(el) {{
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    el.classList.add("active");
    cur = el.dataset.f;
    const isPending = cur === "pending";
    document.getElementById("main-panel").style.display = isPending ? "none" : "";
    document.getElementById("pending-section").style.display = isPending ? "" : "none";
    if (isPending) renderPending(); else applyFilter();
  }}
  function activateTab(filter) {{
    const btn = document.querySelector(`.tab[data-f="${{filter}}"]`);
    if (btn) setTab(btn);
    document.querySelector(".panel").scrollIntoView({{ behavior: "smooth", block: "nearest" }});
  }}
  function applyFilter() {{
    if (cur === "pending") return;
    const q  = document.getElementById("search").value.toLowerCase();
    const fn = FILTERS[cur] || (() => true);
    document.querySelectorAll("#tbody tr[data-status]").forEach(row => {{
      const ok = fn(row) && (!q || row.textContent.toLowerCase().includes(q));
      row.style.display = ok ? "" : "none";
    }});
  }}

  /* ── Theme ── */
  const MOON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  const SUN  = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  function applyTheme(dark) {{
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    document.getElementById("theme-icon").innerHTML = dark ? SUN : MOON;
  }}
  function toggleTheme() {{
    const dark = document.documentElement.getAttribute("data-theme") !== "dark";
    localStorage.setItem("theme", dark ? "dark" : "light");
    applyTheme(dark);
  }}
  applyTheme(localStorage.getItem("theme") === "dark");

  /* ── Auto-refresh ── */
  let secs = 30, isPaused = false, lastActivity = 0;
  const IDLE_MS = 15000; // 15s sem interação = ocioso

  ["mousemove", "mousedown", "keydown", "scroll", "touchstart"].forEach(ev =>
    document.addEventListener(ev, () => {{ lastActivity = Date.now(); }}, {{ passive: true }})
  );

  function tick() {{
    document.getElementById("ts").textContent =
      "Atualizado " + new Date().toLocaleTimeString("pt-BR", {{hour:"2-digit",minute:"2-digit"}});
  }}
  function countdown() {{
    if (isPaused) return;
    if ((Date.now() - lastActivity) < IDLE_MS) {{
      secs = 30;
      document.getElementById("cd").textContent = "Pausado";
      return;
    }}
    document.getElementById("cd").textContent =
      secs > 0 ? "Atualiza em " + secs + "s" : "Atualizando...";
    if (--secs < 0) location.reload();
  }}
  tick();
  setInterval(countdown, 1000);

  /* ── Marcar comparecimento ── */
  async function markAttended(btn) {{
    const row = btn.closest("tr");
    btn.disabled = true;
    btn.innerHTML = "Salvando...";
    const res = await fetch("/admin/attended", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ phone: row.dataset.phone, date: row.dataset.date, time: row.dataset.time }})
    }});
    if (res.ok) {{
      row.dataset.status = "attended";
      row.querySelector(".badge").className = "badge attended";
      row.querySelector(".badge").textContent = "Compareceu";
      row.querySelector(".actions-cell").innerHTML =
        '<button class="action-btn confirm-btn" onclick="openCompleteModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Concluir</button>';
      showToast("Comparecimento registrado!");
      applyFilter();
    }} else {{
      btn.disabled = false;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="23 11 20 14 18 12"/></svg> Compareceu';
      showToast("Erro ao registrar comparecimento.", false);
    }}
  }}

  /* ── Modal Concluir ── */
  let _completeRow = null;
  function openCompleteModal(btn) {{
    _completeRow = btn.closest("tr");
    document.getElementById("complete-notes").value = "";
    const m = document.getElementById("modal-complete");
    m.style.display = "block";
    if (!m._positioned) {{
      m.style.left = Math.max(0, (window.innerWidth  - m.offsetWidth)  / 2) + "px";
      m.style.top  = Math.max(0, (window.innerHeight - m.offsetHeight) / 2) + "px";
      m._positioned = true;
    }}
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }}
  function closeCompleteModal() {{
    document.getElementById("modal-complete").style.display = "none";
    isPaused = false;
    secs = 30;
    _completeRow = null;
  }}
  async function submitComplete(e) {{
    e.preventDefault();
    if (!_completeRow) return;
    const targetRow = _completeRow;
    try {{
      const res = await fetch("/admin/completed", {{
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({{ phone: targetRow.dataset.phone, date: targetRow.dataset.date, time: targetRow.dataset.time, notes: notes }})
      }});
      if (res.ok) {{
        closeCompleteModal();
        targetRow.dataset.status = "completed";
        targetRow.querySelector(".badge").className = "badge completed";
        targetRow.querySelector(".badge").textContent = "Concluído";
        targetRow.querySelector(".actions-cell").innerHTML =
          '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)" title="Encerrar protocolo"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>';
        targetRow.querySelector(".faltam").textContent = "—";
        targetRow.querySelector(".faltam").className = "faltam";
        showToast("Atendimento concluído!");
        applyFilter();
      }} else {{
        btn.disabled = false;
        btn.textContent = "Concluir";
        showToast("Erro ao concluir.", false);
      }}
    }} catch (_) {{
      btn.disabled = false;
      btn.textContent = "Concluir";
      showToast("Erro de conexão.", false);
    }}
  }}

  /* ── Encerrar Protocolo ── */
  let _pendingCloseProtocolBtn = null;
  function openConfirmCloseProtocol(btn) {{
    _pendingCloseProtocolBtn = btn;
    document.getElementById("modal-confirm-protocol").classList.add("open");
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }}
  function closeConfirmProtocolModal() {{
    document.getElementById("modal-confirm-protocol").classList.remove("open");
    _pendingCloseProtocolBtn = null;
    isPaused = false;
    secs = 30;
  }}
  async function confirmDoCloseProtocol() {{
    const btn = _pendingCloseProtocolBtn;
    closeConfirmProtocolModal();
    if (!btn) return;
    const row = btn.closest("tr");
    btn.disabled = true;
    const res = await fetch("/admin/close_protocol", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ phone: row.dataset.phone, date: row.dataset.date, time: row.dataset.time }})
    }});
    if (res.ok) {{
      row.remove();
      showToast("Protocolo encerrado.");
    }} else {{
      btn.disabled = false;
      showToast("Erro ao encerrar protocolo.", false);
    }}
  }}

  /* ── Remarcar no-show ── */
  async function rescheduleApt(btn) {{
    const row = btn.closest("tr");
    btn.disabled = true;
    btn.innerHTML = "Remarcando...";
    const res = await fetch("/admin/reschedule", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ phone: row.dataset.phone, date: row.dataset.date, time: row.dataset.time }})
    }});
    if (res.ok) {{
      row.dataset.status = "scheduled";
      row.querySelector(".badge").className = "badge scheduled";
      row.querySelector(".badge").textContent = "Aguardando";
      row.querySelector(".actions-cell").innerHTML =
        '<button class="action-btn remind-btn" onclick="sendRemind(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button>' +
        '<button class="action-btn edit-btn" onclick="openEditModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button>' +
        '<button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>';
      showToast("Agendamento reaberto!");
      applyFilter();
    }} else {{
      btn.disabled = false;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> Remarcar';
      showToast("Erro ao remarcar.", false);
    }}
  }}

  /* ── Resetar sessão IA ── */
  async function _doResetSession(phone, name, btn, resetLabel) {{
    btn.disabled = true;
    btn.innerHTML = "Resetando...";
    const res = await fetch("/admin/reset_session", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ phone }})
    }});
    if (res.ok) {{
      showToast("Historico da IA resetado para " + name + ".");
    }} else {{
      showToast("Erro ao resetar.", false);
    }}
    btn.disabled = false;
    btn.innerHTML = resetLabel;
  }}
  const RESET_LABEL = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Resetar IA';
  async function resetSession(btn) {{
    const row  = btn.closest("tr");
    const name = row.dataset.name || "este contato";
    if (!confirm("Resetar o historico da IA para " + name + "?\\n\\nA proxima mensagem sera tratada como nova conversa.")) return;
    await _doResetSession(row.dataset.phone, name, btn, RESET_LABEL);
  }}
  async function resetSessionByPhone(phone, name, btn) {{
    if (!confirm("Resetar o historico da IA para " + name + "?\\n\\nA proxima mensagem sera tratada como nova conversa.")) return;
    await _doResetSession(phone, name, btn, RESET_LABEL);
  }}

  /* ── Pendente ── */
  function renderPending() {{
    const tbody = document.getElementById("pending-tbody");
    if (!PENDING_ITEMS.length) {{
      tbody.innerHTML = '<tr><td colspan="4" class="empty-row"><div class="empty-state"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:.3;margin-bottom:.75rem"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><div>Nenhuma pendencia no momento.</div></div></td></tr>';
      return;
    }}
    tbody.innerHTML = PENDING_ITEMS.map(p => {{
      const phone = (p.phone || "").replace("@s.whatsapp.net","").replace("@lid","");
      const dt = new Date(p.created_at);
      const dtBr = isNaN(dt.getTime()) ? (p.created_at || "") : dt.toLocaleString("pt-BR");
      const note = (p.note || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      const idJson   = JSON.stringify(p.id);
      const phoneRaw = JSON.stringify(p.phone);
      const nameDisp = phone;
      return '<tr>' +
        '<td><span class="phone-num">' + phone + '</span></td>' +
        '<td>' + note + '</td>' +
        '<td>' + dtBr + '</td>' +
        '<td><div class="actions-cell">' +
          '<button class="action-btn reset-session-btn" onclick="resetSessionByPhone(' + phoneRaw + ',' + JSON.stringify(nameDisp) + ',this)" title="Resetar historico da IA"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Resetar IA</button>' +
          '<button class="action-btn confirm-btn" onclick="concludePending(this)" title="Concluir"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Concluir</button>' +
        '</div></td>' +
        '</tr>';
    }}).join("");
  }}
  async function concludePending(btn) {{
    const rows = document.querySelectorAll("#pending-tbody tr");
    const row  = btn.closest("tr");
    let idx = -1;
    rows.forEach((r, i) => {{ if (r === row) idx = i; }});
    if (idx < 0 || idx >= PENDING_ITEMS.length) return;
    const item = PENDING_ITEMS[idx];
    btn.disabled = true;
    btn.innerHTML = "Concluindo...";
    const res = await fetch("/admin/pending/dismiss", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ id: item.id }})
    }});
    if (res.ok) {{
      PENDING_ITEMS.splice(idx, 1);
      renderPending();
      showToast("Pendencia concluida.");
    }} else {{
      btn.disabled = false;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Concluir';
      showToast("Erro ao concluir.", false);
    }}
  }}
  async function finalizePending(id, phone, btn) {{
    btn.disabled = true;
    btn.innerHTML = "Finalizando...";
    try {{
      await fetch("/admin/close_by_phone", {{
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({{ phone }})
      }});
    }} catch (_) {{}}
    const res = await fetch("/admin/pending/dismiss", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ id }})
    }});
    if (res.ok) {{
      btn.closest("tr").remove();
      const idx = PENDING_ITEMS.findIndex(p => p.id === id);
      if (idx >= 0) PENDING_ITEMS.splice(idx, 1);
      showToast("Chamado finalizado.");
    }} else {{
      btn.disabled = false;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Finalizar';
      showToast("Erro ao finalizar.", false);
    }}
  }}

  let _pendingDismissId  = null;
  let _pendingDismissBtn = null;
  function dismissPending(id, btn) {{
    _pendingDismissId  = id;
    _pendingDismissBtn = btn;
    document.getElementById("modal-confirm-dismiss").classList.add("open");
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }}
  function closeConfirmDismissModal() {{
    document.getElementById("modal-confirm-dismiss").classList.remove("open");
    _pendingDismissId  = null;
    _pendingDismissBtn = null;
    isPaused = false;
    secs = 30;
  }}
  async function confirmDoDismiss() {{
    const id  = _pendingDismissId;
    const btn = _pendingDismissBtn;
    closeConfirmDismissModal();
    if (!id) return;
    btn.disabled = true;
    btn.textContent = "Descartando...";
    const res = await fetch("/admin/pending/dismiss", {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ id }})
    }});
    if (res.ok) {{
      btn.closest("tr").remove();
      const idx = PENDING_ITEMS.findIndex(p => p.id === id);
      if (idx >= 0) PENDING_ITEMS.splice(idx, 1);
      showToast("Aviso descartado.");
    }} else {{
      btn.disabled = false;
      btn.textContent = "Descartar";
      showToast("Erro ao descartar.", false);
    }}
  }}

  /* ── Drag — new modal ── */
  (function () {{
    const m = document.getElementById("modal-new");
    const h = document.getElementById("modal-handle");
    let drag = false, ox = 0, oy = 0;
    h.addEventListener("mousedown", e => {{
      drag = true;
      const r = m.getBoundingClientRect();
      ox = e.clientX - r.left; oy = e.clientY - r.top;
      document.body.style.userSelect = "none";
    }});
    document.addEventListener("mousemove", e => {{
      if (!drag) return;
      m.style.left = Math.max(0, Math.min(window.innerWidth  - m.offsetWidth,  e.clientX - ox)) + "px";
      m.style.top  = Math.max(0, Math.min(window.innerHeight - m.offsetHeight, e.clientY - oy)) + "px";
    }});
    document.addEventListener("mouseup", () => {{ drag = false; document.body.style.userSelect = ""; }});
  }})();

  /* ── Drag — complete modal ── */
  (function () {{
    const m = document.getElementById("modal-complete");
    const h = document.getElementById("modal-complete-handle");
    let drag = false, ox = 0, oy = 0;
    h.addEventListener("mousedown", e => {{
      drag = true;
      const r = m.getBoundingClientRect();
      ox = e.clientX - r.left; oy = e.clientY - r.top;
      document.body.style.userSelect = "none";
    }});
    document.addEventListener("mousemove", e => {{
      if (!drag || m.style.display === "none") return;
      m.style.left = Math.max(0, Math.min(window.innerWidth  - m.offsetWidth,  e.clientX - ox)) + "px";
      m.style.top  = Math.max(0, Math.min(window.innerHeight - m.offsetHeight, e.clientY - oy)) + "px";
    }});
    document.addEventListener("mouseup", () => {{ if (drag) {{ drag = false; document.body.style.userSelect = ""; }} }});
  }})();

  /* ── Drag — edit modal ── */
  (function () {{
    const m = document.getElementById("modal-edit");
    const h = document.getElementById("modal-edit-handle");
    let drag = false, ox = 0, oy = 0;
    h.addEventListener("mousedown", e => {{
      drag = true;
      const r = m.getBoundingClientRect();
      ox = e.clientX - r.left; oy = e.clientY - r.top;
      document.body.style.userSelect = "none";
    }});
    document.addEventListener("mousemove", e => {{
      if (!drag || m.style.display === "none") return;
      m.style.left = Math.max(0, Math.min(window.innerWidth  - m.offsetWidth,  e.clientX - ox)) + "px";
      m.style.top  = Math.max(0, Math.min(window.innerHeight - m.offsetHeight, e.clientY - oy)) + "px";
    }});
    document.addEventListener("mouseup", () => {{ if (drag) {{ drag = false; document.body.style.userSelect = ""; }} }});
  }})();
  /* ── Resize calendar panel ── */
  (function () {{
    const handle = document.getElementById("resize-handle");
    const right  = document.querySelector(".layout-right");
    if (!handle || !right) return;

    const saved = localStorage.getItem("cal-panel-width");
    if (saved) right.style.width = parseInt(saved) + "px";

    let dragging = false, startX = 0, startW = 0;

    handle.addEventListener("mousedown", e => {{
      dragging = true;
      startX = e.clientX;
      startW = right.offsetWidth;
      handle.classList.add("dragging");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      e.preventDefault();
    }});

    document.addEventListener("mousemove", e => {{
      if (!dragging) return;
      const delta = startX - e.clientX;
      const newW = Math.min(900, Math.max(260, startW + delta));
      right.style.width = newW + "px";
    }});

    document.addEventListener("mouseup", () => {{
      if (!dragging) return;
      dragging = false;
      handle.classList.remove("dragging");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      localStorage.setItem("cal-panel-width", right.offsetWidth);
    }});
  }})();
</script>

</body>
</html>"""
