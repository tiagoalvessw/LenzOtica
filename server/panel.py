from datetime import datetime, timedelta
import json

_STATUS = {
    "scheduled":          ("scheduled",          "Aguardando"),
    "day_reminder_sent":  ("day_reminder_sent",  "Lembrete 1 dia"),
    "reminder_sent":      ("reminder_sent",       "Lembrete 1h"),
    "response_received":  ("response_received",   "Respondeu"),
    "confirmed":          ("confirmed",           "Confirmado"),
    "attended":           ("attended",            "Compareceu"),
    "no_show":            ("no_show",             "Nao veio"),
    "completed":          ("completed",           "Concluido"),
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


def render_panel(agendamentos: list, calendar_embed_url: str = "", admin_token: str = "", pending_items: list = None, clients_count: int = 0, overdue_count: int = 0) -> str:
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
            actions += '<button class="action-btn recover-btn" onclick="recoverApt(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar</button>'
            actions += '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>'
        elif st == "completed":
            actions = '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>'
        elif st == "no_show":
            actions += '<button class="action-btn recover-btn" onclick="rescheduleApt(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> Remarcar</button>'
            actions += '<button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>'
        elif st == "attended":
            actions += '<button class="action-btn confirm-btn" onclick="openCompleteModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Concluir</button>'
        elif st == "confirmed":
            actions += '<button class="action-btn confirm-btn" onclick="markAttended(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="23 11 20 14 18 12"/></svg> Compareceu</button>'
            actions += '<button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>'
        else:
            if st in ("scheduled", "day_reminder_sent"):
                actions += '<button class="action-btn remind-btn" onclick="sendRemind(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button>'
            actions += '<button class="action-btn edit-btn" onclick="openEditModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button>'
            actions += '<button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>'

        actions += '<button class="action-btn reset-session-btn" onclick="resetSession(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Resetar IA</button>'

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

    attended_n = sum(1 for a in agendamentos if a["status"] in ("attended", "completed"))
    base_comp  = sum(1 for a in agendamentos if a["status"] in ("confirmed", "attended", "completed"))
    taxa_comp  = round(attended_n / base_comp * 100) if base_comp > 0 else 0

    today_date = datetime.now().date()
    day_names  = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    days_counts = []
    for i in range(6, -1, -1):
        target = today_date - timedelta(days=i)
        cnt = sum(1 for a in agendamentos if a.get("date") == target.isoformat() and a.get("status") != "cancelled")
        days_counts.append(cnt)
    chart_max_val = max(days_counts) if days_counts else 1
    chart_max_val = chart_max_val or 1
    chart_bars = ""
    for i, cnt in enumerate(days_counts):
        target = today_date - timedelta(days=6 - i)
        lbl = day_names[target.weekday()]
        pct = round(cnt / chart_max_val * 100)
        is_today_cls = "bar-today" if i == 6 else ""
        chart_bars += (
            f'<div class="chart-col">'
            f'<div class="chart-bar-wrap">'
            f'<div class="chart-bar {is_today_cls}" style="height:{max(pct, 4)}%">'
            f'<span class="chart-val">{cnt if cnt else ""}</span>'
            f'</div></div>'
            f'<span class="chart-lbl">{lbl}</span>'
            f'</div>'
        )

    # ── Dashboard v2 ───────────────────────────────────────────────────────────
    chart30_counts: list = []
    chart30_dates:  list = []
    for _i in range(29, -1, -1):
        _target = today_date - timedelta(days=_i)
        _cnt = sum(1 for a in agendamentos if a.get("date") == _target.isoformat() and a.get("status") != "cancelled")
        chart30_counts.append(_cnt)
        chart30_dates.append(_target.isoformat())
    chart30_json  = json.dumps(chart30_counts)
    chart30d_json = json.dumps(chart30_dates)
    _chart_avg    = round(sum(chart30_counts) / 30, 1) if chart30_counts else 0

    _this_start = (today_date - timedelta(days=6)).isoformat()
    _last_start = (today_date - timedelta(days=13)).isoformat()
    _last_end   = (today_date - timedelta(days=7)).isoformat()
    trend_confirmados = (
        sum(1 for a in agendamentos if a.get("status") in ("confirmed", "attended", "completed") and _this_start <= a.get("date", "") <= today)
        - sum(1 for a in agendamentos if a.get("status") in ("confirmed", "attended", "completed") and _last_start <= a.get("date", "") <= _last_end)
    )
    trend_cancelados = (
        sum(1 for a in agendamentos if a.get("status") in ("cancelled", "no_show") and _this_start <= a.get("date", "") <= today)
        - sum(1 for a in agendamentos if a.get("status") in ("cancelled", "no_show") and _last_start <= a.get("date", "") <= _last_end)
    )
    hoje_confirmados  = sum(1 for a in agendamentos if a.get("date") == today and a.get("status") in ("confirmed", "attended"))
    hoje_aguardando   = sum(1 for a in agendamentos if a.get("date") == today and a.get("status") in ("scheduled", "day_reminder_sent", "reminder_sent", "response_received"))
    hoje_sem_lembrete = sum(1 for a in agendamentos if a.get("date") == today and a.get("status") in ("scheduled", "day_reminder_sent"))
    ai_errors_n       = sum(1 for p in (pending_items or []) if any(k in p.get("note", "") for k in ("Rate limit", "Erro no modelo")))
    pendente_badge_html = '<div class="metric-badge">!</div>' if pendente_tab > 0 else ""

    seen_phones_ia: set = set()
    ia_rows = ""
    for a in sorted(agendamentos, key=lambda x: x.get("date", ""), reverse=True):
        ph = a["phone"]
        if ph in seen_phones_ia:
            continue
        seen_phones_ia.add(ph)
        phone_d = ph.replace("@s.whatsapp.net", "").replace("@lid", "")
        st_cls, st_lbl = _STATUS.get(a["status"], (a["status"], a["status"]))
        safe_ia = a["name"].replace('"', "&quot;")
        try:
            dt_ia = datetime.fromisoformat(a["date"])
            date_ia = f"{dt_ia.day:02d}/{dt_ia.month:02d}/{dt_ia.year}"
        except Exception:
            date_ia = a["date"]
        ia_rows += (
            f'<tr>'
            f'<td><span class="client-name">{a["name"]}</span></td>'
            f'<td><span class="phone-num">{phone_d}</span></td>'
            f'<td>{date_ia}</td>'
            f'<td><span class="badge {st_cls}">{st_lbl}</span></td>'
            f'<td><div class="actions-cell">'
            f'<button class="action-btn reset-session-btn" onclick="resetSessionByPhone({json.dumps(ph)},{json.dumps(safe_ia)},this)">'
            f'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>'
            f' Resetar IA</button>'
            f'</div></td>'
            f'</tr>\n'
        )
    ia_body = ia_rows if ia_rows else (
        '<tr><td colspan="5" class="empty-row"><div class="empty-state">'
        '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:.3;margin-bottom:.75rem">'
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
        '<div>Nenhuma sessao ativa.</div></div></td></tr>'
    )

    cal_badge = '<span class="config-badge ok">&#10003; Configurado</span>' if calendar_embed_url else '<span class="config-badge err">&#10007; Nao configurado</span>'

    body = rows if agendamentos else '<tr><td colspan="7" class="empty-row"><div class="empty-state"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:.3;margin-bottom:.75rem"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg><div>Nenhum agendamento encontrado.</div></div></td></tr>'

    if calendar_embed_url:
        if "mode=" not in calendar_embed_url:
            sep = "&" if "?" in calendar_embed_url else "?"
            _embed_url = calendar_embed_url + sep + "mode=WEEK"
        else:
            import re as _re
            _embed_url = _re.sub(r"mode=[^&]*", "mode=WEEK", calendar_embed_url)
        calendar_content = (
            f'<iframe src="{_embed_url}" style="border:0;width:100%;height:620px;display:block;"'
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
<!-- panel-v2-autorefresh-fix -->
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LenzOtica — Painel</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script>document.documentElement.setAttribute("data-theme",localStorage.getItem("theme")||"light");</script>
  <link rel="stylesheet" href="/static/panel.css">
</head>
<body>

<!-- SIDEBAR -->
<aside class="sidebar" id="sidebar">
  <div class="sb-logo">
    <img src="/painel/logo" alt="L" onerror="this.style.display='none'">
    <div class="sb-logo-text">
      <div class="sb-logo-title">LenzOtica</div>
      <div class="sb-logo-sub">Sistema de Gestao</div>
    </div>
  </div>
  <nav class="sb-nav">
    <button class="nav-item active" data-page="dashboard" onclick="navTo('dashboard')">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
      <span class="nav-label">Dashboard</span>
    </button>
    <button class="nav-item" data-page="agendamentos" onclick="navTo('agendamentos')">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      <span class="nav-label">Agendamentos</span>
      <span class="nav-badge">{total}</span>
    </button>
    <button class="nav-item" data-page="ia" onclick="navTo('ia')">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span class="nav-label">Fale com a Liza</span>
    </button>
    <button class="nav-item" data-page="clientes" onclick="navTo('clientes')">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      <span class="nav-label">Clientes</span>
      <span class="nav-badge">{clients_count}</span>
    </button>
    <button class="nav-item" data-page="chat" onclick="navTo('chat')">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span class="nav-label">Chat Cliente</span>
      <span class="nav-badge" id="chat-unread-badge" style="display:none">0</span>
    </button>
    <button class="nav-item" data-page="config" onclick="navTo('config')">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
      <span class="nav-label">Configuracoes</span>
    </button>
  </nav>
  <div class="sb-footer">
    <button class="sb-toggle" onclick="toggleSidebar()" title="Recolher menu">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" id="toggle-icon"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      <span class="toggle-lbl">Recolher</span>
    </button>
  </div>
</aside>

<!-- APP SHELL -->
<div class="app-shell">
  <header>
    <span class="header-title" id="header-title">Dashboard</span>
    <div class="header-right">
      <div class="refresh-wrap" id="refresh-wrap">
        <div id="ts">—</div>
        <div id="cd" style="font-size:.68rem;opacity:.7;"></div>
      </div>
      <button id="theme-btn" onclick="toggleTheme()" title="Alternar tema"><span id="theme-icon"></span></button>
    </div>
  </header>

  <main>

    <!-- DASHBOARD -->
    <section id="page-dashboard" class="page active">
      <div class="page-header">
        <div>
          <div class="page-title">Dashboard</div>
          <div class="page-subtitle">Visao geral dos atendimentos</div>
        </div>
        <button class="btn-new" onclick="navToTab('agendamentos','day');setTimeout(openModal,160)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Novo agendamento
        </button>
      </div>

      <div id="dash-alerts"></div>

      <div class="metrics-grid">
        <div class="metric-card mc-blue" onclick="navToTab('agendamentos','day')" title="Ver atendimentos de hoje">
          {pendente_badge_html}
          <div class="metric-num">{hoje_dia_count}</div>
          <div class="metric-lbl">Atendimentos Hoje</div>
          <div class="metric-sub" id="m-sub-hoje"></div>
          <div class="metric-click-hint">&#8599; Ver agendamentos</div>
        </div>
        <div class="metric-card mc-green" onclick="navToTab('agendamentos','confirmed')" title="Ver confirmados">
          <div class="metric-num">{confirmados_tab}</div>
          <div class="metric-lbl">Confirmados</div>
          <div class="metric-sub" id="m-sub-confirmados"></div>
          <div class="metric-click-hint">&#8599; Ver confirmados</div>
        </div>
        <div class="metric-card mc-red" onclick="navToTab('agendamentos','cancelled')" title="Ver cancelados">
          <div class="metric-num">{cancelados_tab}</div>
          <div class="metric-lbl">Cancelados</div>
          <div class="metric-sub" id="m-sub-cancelados"></div>
          <div class="metric-click-hint">&#8599; Ver cancelados</div>
        </div>
        <div class="metric-card mc-cyan" onclick="navToTab('agendamentos','completed')" title="Ver concluidos">
          <div class="metric-num">{concluidos_tab}</div>
          <div class="metric-lbl">Concluidos</div>
          <div class="metric-sub" id="m-sub-concluidos"></div>
          <div class="metric-click-hint">&#8599; Ver concluidos</div>
        </div>
        <div class="metric-card mc-amber" onclick="navToTab('agendamentos','pending')" title="Ver pendencias">
          <div class="metric-num">{pendente_tab}</div>
          <div class="metric-lbl">Pendencias</div>
          <div class="metric-sub" id="m-sub-pendente"></div>
          <div class="metric-click-hint">&#8599; Ver pendencias</div>
        </div>
        <div class="metric-card mc-purple">
          <div class="metric-num">{taxa_comp}%</div>
          <div class="metric-lbl">Taxa Comparecimento</div>
          <div class="metric-sub" id="m-sub-taxa"></div>
        </div>
      </div>

      <div class="dash-row">
        <div class="dash-card">
          <div class="dash-card-hdr">
            Agendamentos &mdash; historico
            <div class="chart-controls">
              <button class="chart-range-btn active" data-days="7" onclick="setChartRange(this)">7d</button>
              <button class="chart-range-btn" data-days="14" onclick="setChartRange(this)">14d</button>
              <button class="chart-range-btn" data-days="30" onclick="setChartRange(this)">30d</button>
            </div>
          </div>
          <div class="dash-card-body">
            <div style="position:relative">
              <div class="chart-avg-line" id="chart-avg-line"><span class="chart-avg-label" id="chart-avg-label"></span></div>
              <div class="bar-chart-v2" id="bar-chart-v2"></div>
            </div>
            <div class="chart-legend">
              <span class="chart-legend-item"><span class="chart-legend-dot" style="background:#22c55e"></span>Acima da media</span>
              <span class="chart-legend-item"><span class="chart-legend-dot" style="background:#f59e0b"></span>Abaixo da media</span>
            </div>
          </div>
        </div>
        <div class="dash-card">
          <div class="dash-card-hdr">Distribuicao por status</div>
          <div class="dash-card-body"><div class="status-list" id="status-breakdown"></div></div>
        </div>
      </div>

      <div class="dash-card">
        <div class="dash-card-hdr">Proximos atendimentos</div>
        <div class="activity-list" id="upcoming-list"></div>
      </div>
    </section>

    <!-- AGENDAMENTOS -->
    <section id="page-agendamentos" class="page">
      <div class="page-header">
        <div>
          <div class="page-title">Agendamentos</div>
          <div class="page-subtitle">Gerencie todos os agendamentos</div>
        </div>
      </div>
      <div class="layout">
        <div class="layout-left">
          <div class="tab-nav">
            <button class="tab active" data-f="day" onclick="setTab(this)">
              <span class="num">{hoje_dia_count}</span><span class="lbl">Atendimento do Dia</span>
            </button>
            <button class="tab" data-f="confirmed" onclick="setTab(this)">
              <span class="num">{confirmados_tab}</span><span class="lbl">Confirmado</span>
            </button>
            <button class="tab" data-f="cancelled" onclick="setTab(this)">
              <span class="num">{cancelados_tab}</span><span class="lbl">Cancelado</span>
            </button>
            <button class="tab" data-f="completed" onclick="setTab(this)">
              <span class="num">{concluidos_tab}</span><span class="lbl">Concluido</span>
            </button>
            <button class="tab" data-f="all" onclick="setTab(this)">
              <span class="num">{total}</span><span class="lbl">Geral</span>
            </button>
            <button class="tab" data-f="pending" onclick="setTab(this)">
              <span class="num">{pendente_tab}</span><span class="lbl">Pendente</span>
            </button>
          </div>
          <div class="panel" id="main-panel">
            <div class="panel-toolbar">
              <div class="search-wrap">
                <span class="search-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
                <input id="search" type="text" placeholder="Buscar por nome ou telefone..." oninput="applyFilter()">
              </div>
              <div class="date-filter-wrap">
                <label for="filter-date-from">De</label>
                <input type="date" id="filter-date-from" onchange="onDateFilterChange()">
                <label for="filter-date-to">Ate</label>
                <input type="date" id="filter-date-to" onchange="onDateFilterChange()">
                <button class="btn-clear-dates" id="btn-clear-dates" onclick="clearDateFilter()">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  Limpar
                </button>
              </div>
              <button class="btn-new" onclick="openModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Novo agendamento
              </button>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Cliente</th><th>Telefone</th><th>Data</th><th>Hora</th><th>Faltam</th><th>Status</th><th>Acoes</th></tr></thead>
                <tbody id="tbody">{body}</tbody>
              </table>
            </div>
            <div class="pagination" id="pagination">
              <span class="pagination-info" id="pg-info"></span>
              <div class="pagination-btns" id="pg-btns"></div>
            </div>
          </div>
          <div id="pending-section" style="display:none;">
            <div class="panel">
              <div class="panel-toolbar"><span style="font-size:.85rem;font-weight:600;color:var(--text)">Pendencias para o operador</span></div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Telefone</th><th>Observacao</th><th>Data/Hora</th><th>Acoes</th></tr></thead>
                  <tbody id="pending-tbody"></tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        <div id="resize-handle" class="resize-handle" title="Arrastar para redimensionar"></div>
        <div class="layout-right">
          <div class="calendar-panel">
            <div class="calendar-header"><span class="cal-dot"></span>Google Calendar</div>
            {calendar_content}
          </div>
        </div>
      </div>
    </section>

    <!-- AGENTE IA -->
    <section id="page-ia" class="page">
      <div class="page-header">
        <div>
          <div class="page-title">Fale com a Liza</div>
          <div class="page-subtitle">Gerenciamento do assistente virtual WhatsApp</div>
        </div>
      </div>
      <div class="ia-status-card">
        <div class="ia-dot"></div>
        <div class="ia-status-info">
          <div class="ia-status-title">Agente Online</div>
          <div class="ia-status-sub">Assistente de agendamento ativo via WhatsApp</div>
        </div>
        <div class="ia-stat"><div class="ia-stat-num">{total}</div><div class="ia-stat-lbl">Clientes</div></div>
        <div class="ia-stat"><div class="ia-stat-num">{pendente_tab}</div><div class="ia-stat-lbl">Pendentes</div></div>
      </div>
      <div class="panel">
        <div class="panel-toolbar"><span style="font-size:.85rem;font-weight:600;color:var(--text)">Sessoes ativas por cliente</span></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Cliente</th><th>Telefone</th><th>Ultimo Agendamento</th><th>Status</th><th>Acoes</th></tr></thead>
            <tbody>{ia_body}</tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- CLIENTES -->
    <section id="page-clientes" class="page">
      <div class="page-header">
        <div>
          <div class="page-title">Clientes</div>
          <div class="page-subtitle">Cadastro, historico e acompanhamento de retorno</div>
        </div>
        <button class="btn-new" onclick="openClientModal(null)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Novo Cliente
        </button>
      </div>

      <!-- Metricas -->
      <div class="metrics-grid">
        <div class="metric-card mc-blue"><div class="metric-num" id="cm-total">—</div><div class="metric-lbl">Total Clientes</div></div>
        <div class="metric-card mc-green"><div class="metric-num" id="cm-new">—</div><div class="metric-lbl">Novos este Mes</div></div>
        <div class="metric-card mc-amber"><div class="metric-num" id="cm-upcoming">—</div><div class="metric-lbl">Retorno em 30 dias</div></div>
        <div class="metric-card mc-red"><div class="metric-num" id="cm-overdue">—</div><div class="metric-lbl">Retorno Atrasado</div></div>
      </div>

      <!-- Tabela -->
      <div class="panel">
        <div class="panel-toolbar">
          <div class="search-wrap">
            <span class="search-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
            <input id="client-search" type="text" placeholder="Buscar por nome, sobrenome ou telefone..." oninput="filterClients()" style="width:100%;padding:.5rem .8rem .5rem 2.2rem;border:1px solid var(--border2);border-radius:var(--radius-sm);font-size:.85rem;font-family:inherit;background:var(--surface);color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s">
          </div>
          <div class="clients-filters" id="clients-filters">
            <button class="filter-chip active" data-cf="all"    onclick="setClientFilter(this)">Todos</button>
            <button class="filter-chip"        data-cf="overdue" onclick="setClientFilter(this)">&#128308; Atrasado</button>
            <button class="filter-chip"        data-cf="upcoming" onclick="setClientFilter(this)">&#128993; Proximo</button>
            <button class="filter-chip"        data-cf="ok"      onclick="setClientFilter(this)">&#128994; OK</button>
          </div>
          <button class="btn-new" onclick="openClientModal(null)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Novo Cliente
          </button>
          <button class="btn-export" onclick="exportClientsCSV()" title="Exportar lista de clientes como CSV">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Exportar CSV
          </button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="sortable-th" id="sh-first_name" onclick="sortClients('first_name')">Nome <span class="sort-icon">&#x21C5;</span></th>
                <th class="sortable-th" id="sh-last_name" onclick="sortClients('last_name')">Sobrenome <span class="sort-icon">&#x21C5;</span></th>
                <th>Telefone</th>
                <th class="sortable-th" id="sh-visit_count" onclick="sortClients('visit_count')">Visitas <span class="sort-icon">&#x21C5;</span></th>
                <th class="sortable-th" id="sh-last_appointment_date" onclick="sortClients('last_appointment_date')">Ultima Consulta <span class="sort-icon">&#x21C5;</span></th>
                <th>Nasc.</th>
                <th class="sortable-th" id="sh-return_date" onclick="sortClients('return_date')">Data Retorno <span class="sort-icon">&#x21C5;</span></th>
                <th class="sortable-th" id="sh-return_status_order" onclick="sortClients('return_status_order')">Status <span class="sort-icon">&#x21C5;</span></th>
                <th>Observacoes</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody id="clients-tbody">
              <tr><td colspan="10" class="empty-row"><div class="clients-empty"><div class="clients-empty-icon">&#128100;</div><div>Carregando...</div></div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- CHAT CLIENTE -->
    <section id="page-chat" class="page">
      <div class="chat-layout" id="chat-layout">

        <!-- Painel esquerdo: lista de contatos -->
        <div class="chat-contacts-panel">
          <div class="chat-contacts-hdr">
            <div class="chat-contacts-title" style="justify-content:space-between">
              <div style="display:flex;align-items:center;gap:.4rem">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#25D366" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                Conversas WhatsApp
              </div>
              <button id="global-ia-btn" class="global-ia-btn ia-on" onclick="toggleGlobalIA()"
                title="Clique para pausar ou retomar a IA globalmente">
                <!-- Icone de robo -->
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="11" width="18" height="10" rx="2"/>
                  <path d="M12 11V7"/>
                  <circle cx="12" cy="5" r="2"/>
                  <line x1="8" y1="15" x2="8" y2="15"/><line x1="16" y1="15" x2="16" y2="15"/>
                  <path d="M8 19h8"/>
                </svg>
              </button>
            </div>
            <!-- Banner de status da IA -->
            <div class="ia-global-banner ia-on" id="ia-global-banner">
              <span class="ia-banner-dot"></span>
              <span id="ia-global-banner-txt">IA ativa &mdash; respondendo automaticamente</span>
            </div>
            <input class="chat-search" id="chat-search" type="text" placeholder="Buscar por nome ou numero..." oninput="filterChatContacts()">
            <div class="chat-filter-row">
              <button class="chat-filter-btn active" data-cf="all" onclick="setChatContactFilter(this)">Todos</button>
              <button class="chat-filter-btn" data-cf="unread" onclick="setChatContactFilter(this)">Nao lidos</button>
              <button class="chat-filter-btn" data-cf="ia-off" onclick="setChatContactFilter(this)">IA pausada</button>
            </div>
          </div>
          <div class="chat-contact-list" id="chat-contact-list">
            <div class="chat-empty-contacts">Carregando...</div>
          </div>
        </div>

        <!-- Painel direito: conversa ativa -->
        <div class="chat-conv-panel" id="chat-conv-panel">

          <!-- Estado vazio (nenhum contato selecionado) -->
          <div class="chat-conv-empty" id="chat-conv-empty">
            <div class="chat-conv-empty-icon">&#128172;</div>
            <p>Selecione um contato para ver a conversa</p>
          </div>

          <!-- Conversa ativa -->
          <div id="chat-active-conv" style="display:none">
            <!-- Header da conversa -->
            <div class="chat-conv-header">
              <div class="chat-avatar" id="conv-avatar" style="background:#2563eb">?</div>
              <div class="chat-conv-info">
                <div class="chat-conv-name" id="conv-name">—</div>
                <div class="chat-conv-phone" id="conv-phone"></div>
              </div>

            </div>

            <!-- Area de mensagens -->
            <div class="chat-messages" id="chat-messages-area"></div>


            <!-- Barra de input -->
            <div class="chat-input-bar">
              <textarea class="chat-textarea" id="chat-input" placeholder="Digite uma mensagem..." rows="1"
                onkeydown="chatKeydown(event)" oninput="chatInputResize(this)"></textarea>
              <button class="chat-send-btn" id="chat-send-btn" onclick="sendChatMsg()" title="Enviar (Enter)">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </button>
            </div>
          </div>

        </div>
      </div>
    </section>

    <!-- CONFIGURACOES -->
    <section id="page-config" class="page">
      <div class="page-header">
        <div>
          <div class="page-title">Configuracoes</div>
          <div class="page-subtitle">Configure o agente IA e as informacoes da loja</div>
        </div>
      </div>

      <div class="cfg-tabs">
        <button class="cfg-tab active" data-tab="loja" onclick="switchCfgTab('loja')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          <span class="cfg-tab-label">Loja</span>
        </button>
        <button class="cfg-tab" data-tab="identidade" onclick="switchCfgTab('identidade')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
          <span class="cfg-tab-label">Identidade</span>
        </button>
        <button class="cfg-tab" data-tab="horarios" onclick="switchCfgTab('horarios')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span class="cfg-tab-label">Horarios</span>
        </button>
        <button class="cfg-tab" data-tab="faq" onclick="switchCfgTab('faq')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span class="cfg-tab-label">FAQ</span>
        </button>
        <button class="cfg-tab" data-tab="conhecimento" onclick="switchCfgTab('conhecimento')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          <span class="cfg-tab-label">Conhecimento</span>
        </button>
        <button class="cfg-tab" data-tab="notificacoes" onclick="switchCfgTab('notificacoes')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          <span class="cfg-tab-label">Notificacoes</span>
        </button>
        <button class="cfg-tab" data-tab="avancado" onclick="switchCfgTab('avancado')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
          <span class="cfg-tab-label">Avancado</span>
        </button>
        <button class="cfg-tab" data-tab="monitoramento" onclick="switchCfgTab('monitoramento')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          <span class="cfg-tab-label">Monitoramento</span>
        </button>
      </div>

      <!-- PANE: Loja -->
      <div id="cfg-pane-loja" class="cfg-pane active">
        <div class="config-section">
          <div class="config-section-hdr">Informacoes da Loja</div>
          <div class="bcf-form">
            <p class="bcf-hint">Estas informacoes sao usadas pelo agente ao responder perguntas dos clientes sobre a loja (endereco, servicos, etc).</p>
            <div class="bcf-row">
              <div class="bcf-group"><label class="bcf-label">Nome da loja</label><input class="bcf-input" id="bc-store-name" placeholder="Ex: LenzOtica"></div>
              <div class="bcf-group"><label class="bcf-label">Telefone</label><input class="bcf-input" id="bc-store-phone" placeholder="Ex: (48) 3375-2050"></div>
            </div>
            <div class="bcf-group"><label class="bcf-label">Endereco completo</label><input class="bcf-input" id="bc-store-address" placeholder="Ex: Rua Exemplo, 123, Bairro, Cidade - SC"></div>
            <div class="bcf-group">
              <label class="bcf-label">Servicos oferecidos</label>
              <input class="bcf-input" id="bc-store-services" placeholder="Ex: Exame de vista gratuito, venda de oculos, lentes de contato">
              <span class="bcf-hint">Breve descricao dos servicos oferecidos. Usado na apresentacao da loja ao cliente.</span>
            </div>
            <div class="bcf-group">
              <label class="bcf-label">Observacao de localizacao</label>
              <input class="bcf-input" id="bc-store-notes" placeholder="Ex: Estamos ao lado do cartorio">
              <span class="bcf-hint">Dica adicional para clientes encontrarem a loja. Mencionado quando perguntarem como chegar.</span>
            </div>
            <div><button class="btn-primary" onclick="saveBotConfig(this)">Salvar informacoes da loja</button></div>
          </div>
        </div>
      </div>

      <!-- PANE: Identidade -->
      <div id="cfg-pane-identidade" class="cfg-pane">
        <div class="config-section">
          <div class="config-section-hdr">Identidade do Agente</div>
          <div class="bcf-form">
            <p class="bcf-hint">Defina como o agente se apresenta e se comunica. Estas configuracoes sao incluidas automaticamente no prompt do sistema.</p>
            <div class="bcf-row">
              <div class="bcf-group">
                <label class="bcf-label">Nome do agente</label>
                <input class="bcf-input" id="bc-bot-name" placeholder="Ex: Liza">
                <span class="bcf-hint">Como o agente se identifica para os clientes.</span>
              </div>
              <div class="bcf-group">
                <label class="bcf-label">Tom de comunicacao</label>
                <select class="bcf-select" id="bc-bot-tone">
                  <option value="informal">Informal — "Claro!", "Com certeza!" (WhatsApp)</option>
                  <option value="formal">Formal — "Com prazer", "Certamente" (corporativo)</option>
                </select>
              </div>
            </div>
            <div class="bcf-group">
              <label class="bcf-label">Personalidade</label>
              <textarea class="bcf-textarea" id="bc-bot-personality" rows="2" placeholder="Ex: Simpatica e acolhedora. Usa o nome do cliente quando sabe. Mensagens curtas e objetivas."></textarea>
              <span class="bcf-hint">Descricao curta do perfil do agente. Incluida nas instrucoes internas do sistema.</span>
            </div>
            <div class="bcf-group">
              <label class="bcf-label">Apresentacao inicial</label>
              <input class="bcf-input" id="bc-bot-greeting" placeholder="Ex: Me chamo Liza, como posso ajuda-lo?">
              <span class="bcf-hint">Frase usada apos a saudacao de horario. Resultado: "Bom dia! Me chamo Liza, como posso ajuda-lo?"</span>
            </div>
            <div class="bcf-group">
              <label class="bcf-label">Regras extras (uma por linha)</label>
              <textarea class="bcf-textarea" id="bc-bot-extra-rules" rows="3" placeholder="Nunca use emojis&#10;Nunca se identifique como robo ou IA&#10;Sempre pergunte o nome do cliente"></textarea>
              <span class="bcf-hint">Cada linha vira uma regra adicional na lista de instrucoes do agente.</span>
            </div>
            <div><button class="btn-primary" onclick="saveBotConfig(this)">Salvar identidade</button></div>
          </div>
        </div>
      </div>

      <!-- PANE: Horarios -->
      <div id="cfg-pane-horarios" class="cfg-pane">
        <div class="config-section">
          <div class="config-section-hdr">Horario de Atendimento</div>
          <div class="config-body">
            <div class="config-row" style="flex-direction:column;align-items:stretch;gap:.75rem">
              <p class="bcf-hint" style="padding-top:.35rem">Configure os dias e horarios de funcionamento. A IA usa estas informacoes para oferecer horarios reais de agendamento.</p>
              <div class="bh-slot-card">
                <div class="bh-slot-group">
                  <label class="bh-slot-label">Duracao da consulta</label>
                  <select class="bh-slot-select" id="bh-slot-duration">
                    <option value="15">15 min</option>
                    <option value="20">20 min</option>
                    <option value="30" selected>30 min</option>
                    <option value="45">45 min</option>
                    <option value="60">1 hora</option>
                    <option value="90">1h 30min</option>
                  </select>
                  <span class="bh-slot-hint">Tempo padrao de cada atendimento — a IA usa para calcular os horarios disponiveis.</span>
                </div>
                <div class="bh-slot-group">
                  <label class="bh-slot-label">Intervalo entre consultas</label>
                  <select class="bh-slot-select" id="bh-slot-interval">
                    <option value="0" selected>Sem intervalo</option>
                    <option value="10">10 min</option>
                    <option value="15">15 min</option>
                    <option value="30">30 min</option>
                  </select>
                  <span class="bh-slot-hint">Folga entre agendamentos consecutivos para preparacao do atendimento.</span>
                </div>
              </div>
              <div id="bh-grid" class="bh-grid"><span style="font-size:.8rem;color:var(--muted)">Carregando...</span></div>
              <button class="btn-primary" style="width:fit-content;margin-top:.25rem" onclick="saveBusinessHours(this)">Salvar horarios</button>
            </div>
          </div>
        </div>
      </div>

      <!-- PANE: FAQ -->
      <div id="cfg-pane-faq" class="cfg-pane">
        <div class="config-section">
          <div class="config-section-hdr" style="display:flex;align-items:center;justify-content:space-between">
            <span>Perguntas Frequentes (FAQ)</span>
            <button class="btn-new" onclick="openFaqModal(null)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Adicionar FAQ
            </button>
          </div>
          <div class="config-body" style="padding-bottom:1rem">
            <p class="bcf-hint" style="padding:.5rem 0 .75rem">FAQs fazem o agente responder perguntas especificas exatamente como voce configurar — sem inventar informacoes.</p>
            <div class="table-wrap">
              <table>
                <thead><tr><th style="width:35%">Pergunta</th><th>Resposta</th><th>Status</th><th>Acoes</th></tr></thead>
                <tbody id="faq-tbody"><tr><td colspan="4" class="empty-row"><div class="empty-state">Carregando...</div></td></tr></tbody>
              </table>
            </div>
            <div class="faq-ex-box" id="faq-ex-box" style="display:none">
              <strong>Exemplos de FAQ que voce pode adicionar:</strong>
              <ul style="margin-top:.3rem;padding-left:1.2rem">
                <li>"Voces aceitam convenio?" &#8594; "Atendemos particulares, mas o exame e gratuito!"</li>
                <li>"Quanto demora?" &#8594; "Em media 5 a 7 dias uteis apos aprovacao."</li>
                <li>"Posso trazer minha receita?" &#8594; "Sim! Pode trazer e a gente faz o orcamento."</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- PANE: Conhecimento (RAG) -->
      <div id="cfg-pane-conhecimento" class="cfg-pane">

        <!-- Banner "Como funciona" -->
        <div class="rag-how-banner">
          <div class="rag-how-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Como funciona a Base de Conhecimento?
          </div>
          <div class="rag-steps-row">
            <div class="rag-step-item">
              <div class="rag-step-num">1</div>
              <strong>Voce adiciona documentos</strong>
              Politicas, catalogo de produtos, precos, scripts de atendimento, respostas padrao...
            </div>
            <div class="rag-step-arrow">&#8594;</div>
            <div class="rag-step-item">
              <div class="rag-step-num">2</div>
              <strong>O sistema indexa automaticamente</strong>
              O texto e dividido em trechos (chunks) e transformado em vetores de busca semantica.
            </div>
            <div class="rag-step-arrow">&#8594;</div>
            <div class="rag-step-item">
              <div class="rag-step-num">3</div>
              <strong>A IA responde com mais precisao</strong>
              A cada mensagem, a IA busca os trechos mais relevantes e os usa para responder ao cliente com informacoes reais da loja.
            </div>
          </div>
        </div>

        <div class="config-section">
          <!-- Header com toggle, stats e status -->
          <div class="config-section-hdr rag-section-hdr">
            <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
              <span>Documentos Indexados</span>
              <div class="rag-stats-row" id="rag-stats-row" style="display:none">
                <span class="rag-stat-chip" id="rag-stat-docs">— docs</span>
                <span class="rag-stat-chip" id="rag-stat-chunks">— chunks</span>
              </div>
            </div>
            <label class="toggle-switch" title="Ativar ou desativar o uso da base de conhecimento nas respostas da IA">
              <input type="checkbox" id="rag-enabled" onchange="saveRagEnabled()">
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
              <span style="font-size:.75rem;color:var(--text2)">RAG Ativo</span>
            </label>
          </div>

          <div class="config-body">
            <div class="config-row" style="flex-direction:column;align-items:stretch;gap:.75rem;border-bottom:1px solid var(--border);padding-bottom:1.25rem">

              <!-- Guia rapido de tipos -->
              <div class="rag-type-guide">
                <span class="rag-type-guide-title">Tipos de documento:</span>
                <span class="rag-type-chip" title="Perguntas e respostas diretas — ex: Voces aceitam convenio? Quanto custa?">&#128172; FAQ — perguntas e respostas</span>
                <span class="rag-type-chip" title="Regras internas — ex: politica de cancelamento, garantia, prazo de confeccao">&#128196; Politica — regras da loja</span>
                <span class="rag-type-chip" title="Lista de produtos, modelos, marcas e precos disponiveis">&#128722; Catalogo — produtos e precos</span>
                <span class="rag-type-chip" title="Roteiros de atendimento para situacoes especificas">&#127908; Script — roteiro de atendimento</span>
                <span class="rag-type-chip" title="Instrucoes operacionais, informacoes extras">&#128214; Manual — outras informacoes</span>
              </div>

              <div style="display:flex;align-items:center;justify-content:space-between">
                <span style="font-size:.84rem;font-weight:600;color:var(--text)">Documentos cadastrados</span>
                <button class="btn-new" onclick="openDocModal()">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  Adicionar Documento
                </button>
              </div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Titulo</th><th>Tipo</th><th title="Numero de trechos indexados — mais chunks = mais cobertura">Chunks &#9432;</th><th>Status</th><th>Acoes</th></tr></thead>
                  <tbody id="doc-tbody"><tr><td colspan="5" class="empty-row"><div class="empty-state">Carregando...</div></td></tr></tbody>
                </table>
              </div>
            </div>

            <!-- Log de consultas -->
            <div class="config-row" style="flex-direction:column;align-items:stretch;gap:.5rem;padding-top:.875rem">
              <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
                <span style="font-size:.82rem;font-weight:600;color:var(--text)">Log de Consultas RAG</span>
                <span style="font-size:.72rem;color:var(--muted)">(ultimas 50 buscas)</span>
                <div class="rag-sim-legend-row">
                  <span class="rag-sim-legend"><span class="rag-sim-dot sim-high"></span>Alta (&ge;75%)</span>
                  <span class="rag-sim-legend"><span class="rag-sim-dot sim-mid"></span>Media (50–74%)</span>
                  <span class="rag-sim-legend"><span class="rag-sim-dot sim-low"></span>Baixa (&lt;50%)</span>
                </div>
              </div>
              <p class="bcf-hint" style="padding:0">A coluna <strong>Similaridade</strong> mostra o quanto o documento encontrado era relevante para a pergunta. Quanto mais alta, melhor a resposta da IA.</p>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Telefone</th><th>Pergunta do cliente</th><th>Chunks</th><th>Similaridade</th><th>Latencia</th><th>Quando</th></tr></thead>
                  <tbody id="rag-log-tbody"><tr><td colspan="6" class="empty-row"><div class="empty-state">Carregando...</div></td></tr></tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- PANE: Notificacoes -->
      <div id="cfg-pane-notificacoes" class="cfg-pane">
        <div class="config-section">
          <div class="config-section-hdr">Templates de Mensagem WhatsApp</div>
          <div class="notif-tpl-list">

            <div class="notif-info-bar">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <span>Personalize as mensagens automaticas enviadas pelo bot. Clique nas variaveis coloridas para inseri-las na posicao do cursor. Deixe o campo vazio para usar o texto padrao do sistema.</span>
            </div>

            <!-- Card 1: Lembrete 1 dia antes -->
            <div class="notif-tpl-card">
              <div class="notif-tpl-hdr">
                <div class="notif-tpl-badge" style="background:#fef3c7;color:#d97706">&#9201;</div>
                <div class="notif-tpl-info">
                  <div class="notif-tpl-title">Lembrete &mdash; 1 dia antes</div>
                  <div class="notif-tpl-desc">Enviado automaticamente no dia anterior ao agendamento. Nao exige resposta do cliente.</div>
                </div>
              </div>
              <div class="notif-tpl-body">
                <div class="notif-var-row">
                  <span class="notif-var-lbl">Variaveis:</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-lembrete-dia','{{nome}}')">{{nome}}</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-lembrete-dia','{{data}}')">{{data}}</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-lembrete-dia','{{hora}}')">{{hora}}</span>
                </div>
                <textarea class="notif-ta" id="notif-ta-lembrete-dia" rows="5" oninput="updateCharCount(this,'notif-cc-lembrete-dia')" placeholder="Deixe vazio para usar o texto padrao do sistema"></textarea>
                <div class="notif-char-count" id="notif-cc-lembrete-dia">0 caracteres</div>
              </div>
            </div>

            <!-- Card 2: Lembrete 1h antes -->
            <div class="notif-tpl-card">
              <div class="notif-tpl-hdr">
                <div class="notif-tpl-badge" style="background:#dbeafe;color:#2563eb">&#128276;</div>
                <div class="notif-tpl-info">
                  <div class="notif-tpl-title">Lembrete &mdash; 1h antes &nbsp;<span style="font-size:.7rem;font-weight:400;color:var(--muted)">(aguarda SIM / NAO)</span></div>
                  <div class="notif-tpl-desc">Enviado ~1h antes do horario marcado. O cliente pode responder SIM para confirmar ou NAO para cancelar. Tambem usado pelo botao Lembrete manual na aba Agendamentos.</div>
                </div>
              </div>
              <div class="notif-tpl-body">
                <div class="notif-var-row">
                  <span class="notif-var-lbl">Variaveis:</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-lembrete-hora','{{nome}}')">{{nome}}</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-lembrete-hora','{{data}}')">{{data}}</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-lembrete-hora','{{hora}}')">{{hora}}</span>
                </div>
                <textarea class="notif-ta" id="notif-ta-lembrete-hora" rows="5" oninput="updateCharCount(this,'notif-cc-lembrete-hora')" placeholder="Deixe vazio para usar o texto padrao do sistema"></textarea>
                <div class="notif-char-count" id="notif-cc-lembrete-hora">0 caracteres</div>
              </div>
            </div>

            <!-- Card 3: Cancelamento automatico -->
            <div class="notif-tpl-card">
              <div class="notif-tpl-hdr">
                <div class="notif-tpl-badge" style="background:#fee2e2;color:#dc2626">&#10060;</div>
                <div class="notif-tpl-info">
                  <div class="notif-tpl-title">Cancelamento automatico</div>
                  <div class="notif-tpl-desc">Enviado quando o cliente nao confirma presenca apos receber o lembrete de 1h. O agendamento e cancelado automaticamente.</div>
                </div>
              </div>
              <div class="notif-tpl-body">
                <div class="notif-var-row">
                  <span class="notif-var-lbl">Variaveis:</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-cancelamento','{{nome}}')">{{nome}}</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-cancelamento','{{data}}')">{{data}}</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-cancelamento','{{hora}}')">{{hora}}</span>
                </div>
                <textarea class="notif-ta" id="notif-ta-cancelamento" rows="5" oninput="updateCharCount(this,'notif-cc-cancelamento')" placeholder="Deixe vazio para usar o texto padrao do sistema"></textarea>
                <div class="notif-char-count" id="notif-cc-cancelamento">0 caracteres</div>
              </div>
            </div>

            <!-- Card 4: Retorno de cliente -->
            <div class="notif-tpl-card">
              <div class="notif-tpl-hdr">
                <div class="notif-tpl-badge" style="background:#d1fae5;color:#059669">&#128260;</div>
                <div class="notif-tpl-info">
                  <div class="notif-tpl-title">Retorno de cliente</div>
                  <div class="notif-tpl-desc">Enviado pelo botao Notificar na aba Clientes quando e hora do retorno. Nao possui data/hora de agendamento.</div>
                </div>
              </div>
              <div class="notif-tpl-body">
                <div class="notif-var-row">
                  <span class="notif-var-lbl">Variaveis:</span>
                  <span class="notif-var-chip" onclick="insertVar('notif-ta-retorno','{{nome}}')">{{nome}}</span>
                </div>
                <textarea class="notif-ta" id="notif-ta-retorno" rows="4" oninput="updateCharCount(this,'notif-cc-retorno')" placeholder="Deixe vazio para usar o texto padrao do sistema"></textarea>
                <div class="notif-char-count" id="notif-cc-retorno">0 caracteres</div>
              </div>
            </div>

            <!-- Card 5: Confirmação de agendamento -->
            <div class="notif-tpl-card">
              <div class="notif-tpl-hdr">
                <div class="notif-tpl-badge" style="background:#dbeafe;color:#1d4ed8">&#128203;</div>
                <div class="notif-tpl-info">
                  <div class="notif-tpl-title">Confirmacao de Agendamento</div>
                  <div class="notif-tpl-desc">Mensagem enviada ao cliente apos o agendamento ser registrado. Composta por 3 partes enviadas em sequencia.</div>
                </div>
              </div>
              <div class="notif-tpl-body" style="gap:.5rem">
                <label class="bcf-label" style="padding-top:.25rem">Tipo de atendimento</label>
                <input class="bcf-input" id="notif-confirmation-type" placeholder="Ex: Exame de vista">
                <label class="bcf-label" style="padding-top:.5rem">Endereco da loja</label>
                <input class="bcf-input" id="notif-confirmation-address" placeholder="Ex: Rua Exemplo, 123, Bairro, Cidade - SC">
                <label class="bcf-label" style="padding-top:.5rem">Aviso final</label>
                <input class="bcf-input" id="notif-confirmation-footer" placeholder="Ex: Caso precise reagendar, avisar com antecedencia!!!">
              </div>
            </div>

            <!-- Card 6: Campanha -->
            <div class="notif-tpl-card">
              <div class="notif-tpl-hdr">
                <div class="notif-tpl-badge" style="background:#fef9c3;color:#a16207">&#127881;</div>
                <div class="notif-tpl-info">
                  <div class="notif-tpl-title">
                    Mensagem de Campanha
                    <label class="toggle-switch" style="margin-left:.75rem" title="Ativar ou desativar a campanha">
                      <input type="checkbox" id="notif-campaign-enabled" onchange="saveCampaignEnabled()">
                      <span class="toggle-track"><span class="toggle-thumb"></span></span>
                      <span style="font-size:.72rem;color:var(--text2)">Ativa</span>
                    </label>
                  </div>
                  <div class="notif-tpl-desc">Mensagem injetada no contexto da IA quando um novo cliente demonstra interesse. Desative quando nao houver campanha em andamento.</div>
                </div>
              </div>
              <div class="notif-tpl-body">
                <textarea class="notif-ta" id="notif-ta-campanha" rows="3" oninput="updateCharCount(this,'notif-cc-campanha')" placeholder="Ex: Essa semana temos exame gratuito! Quer agendar?"></textarea>
                <div class="notif-char-count" id="notif-cc-campanha">0 caracteres</div>
              </div>
            </div>

            <!-- Card 7: Respostas a midias -->
            <div class="notif-tpl-card">
              <div class="notif-tpl-hdr">
                <div class="notif-tpl-badge" style="background:#f3e8ff;color:#7e22ce">&#127908;</div>
                <div class="notif-tpl-info">
                  <div class="notif-tpl-title">Respostas a Midias</div>
                  <div class="notif-tpl-desc">Mensagens enviadas quando o cliente manda audio, imagem, video, documento ou sticker — a IA nao processa esses tipos de arquivo.</div>
                </div>
              </div>
              <div class="notif-tpl-body" style="gap:.5rem">
                <label class="bcf-label" style="padding-top:.25rem">Audio &#127908;</label>
                <input class="bcf-input" id="notif-media-audio" placeholder="Ex: Nao consigo ouvir audios, mas pode me escrever!">
                <label class="bcf-label" style="padding-top:.5rem">Imagem &#128247;</label>
                <input class="bcf-input" id="notif-media-image" placeholder="Ex: Nao consigo ver imagens, mas pode me descrever!">
                <label class="bcf-label" style="padding-top:.5rem">Video &#127916;</label>
                <input class="bcf-input" id="notif-media-video" placeholder="Ex: Nao consigo assistir videos, mas pode me escrever!">
                <label class="bcf-label" style="padding-top:.5rem">Documento &#128196;</label>
                <input class="bcf-input" id="notif-media-document" placeholder="Ex: Nao consigo abrir documentos, mas pode me descrever!">
                <label class="bcf-label" style="padding-top:.5rem">Sticker &#128515;</label>
                <input class="bcf-input" id="notif-media-sticker" placeholder="Ex: Que simpatico! Posso te ajudar com alguma coisa?">
              </div>
            </div>

            <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
              <button class="btn-primary" onclick="saveNotifTemplates(this)">Salvar templates</button>
              <button style="font-size:.78rem;padding:.38rem .85rem;border-radius:var(--radius-sm);border:1px solid var(--border2);background:var(--surface);cursor:pointer;color:var(--text2);font-family:inherit;transition:background .12s" onclick="resetNotifTemplates()">&#8635; Restaurar textos padrao</button>
            </div>

          </div>
        </div>

        <!-- Templates Personalizados -->
        <div class="config-section" style="margin-top:1.25rem">
          <div class="config-section-hdr ctpl-section-hdr">
            <span>Templates Personalizados</span>
            <button class="btn-new" onclick="openCustomTplModal(null)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Novo template
            </button>
          </div>
          <div class="notif-info-bar" style="margin:1rem 1.25rem 0">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <span>Crie mensagens prontas para reutilizar no dia a dia &mdash; respostas frequentes, avisos, promocoes e muito mais. Use as variaveis <strong>&#123;nome&#125;</strong>, <strong>&#123;data&#125;</strong> e <strong>&#123;hora&#125;</strong> para personalizar automaticamente.</span>
          </div>
          <div id="ctpl-list" class="ctpl-list">
            <div class="ctpl-empty">
              <div class="ctpl-empty-icon">&#128172;</div>
              <div>Carregando...</div>
            </div>
          </div>
        </div>

      </div>

      <!-- PANE: Avancado -->
      <div id="cfg-pane-avancado" class="cfg-pane">
        <div class="config-section" style="margin-bottom:1.25rem">
          <div class="config-section-hdr">Parametros RAG</div>
          <div class="config-body">
            <div class="config-row">
              <div class="config-key">Parametros de busca</div>
              <div class="config-val">
                <div class="rag-params">
                  <div class="rp-item">
                    <label><span class="rp-label-icon">?</span> Resultados</label>
                    <div class="rp-stepper">
                      <button class="rp-btn" onclick="rpStep('rag-top-k',-1,1,20)">&#8722;</button>
                      <input type="number" id="rag-top-k" class="rp-input" min="1" max="20" value="3">
                      <button class="rp-btn" onclick="rpStep('rag-top-k',1,1,20)">&#43;</button>
                    </div>
                    <div class="rp-tooltip">Quantos trechos do conhecimento a IA consulta por mensagem. Mais = respostas mais ricas, porem mais lentas.</div>
                  </div>
                  <div class="rp-item">
                    <label><span class="rp-label-icon">?</span> Similaridade</label>
                    <div class="rp-stepper">
                      <button class="rp-btn" onclick="rpStep('rag-min-sim',-0.05,0,1,2)">&#8722;</button>
                      <input type="number" id="rag-min-sim" class="rp-input" min="0" max="1" step="0.05" value="0.75">
                      <button class="rp-btn" onclick="rpStep('rag-min-sim',0.05,0,1,2)">&#43;</button>
                    </div>
                    <div class="rp-tooltip">Filtro de relevancia (0 a 1). Valor alto = so trechos muito parecidos com a pergunta. Baixo = aceita mais resultados, mas pode trazer conteudo fora do tema.</div>
                  </div>
                  <div class="rp-item">
                    <label><span class="rp-label-icon">?</span> Tokens ctx</label>
                    <div class="rp-stepper">
                      <button class="rp-btn" onclick="rpStep('rag-max-ctx',-50,100,3000)">&#8722;</button>
                      <input type="number" id="rag-max-ctx" class="rp-input" min="100" max="3000" value="800">
                      <button class="rp-btn" onclick="rpStep('rag-max-ctx',50,100,3000)">&#43;</button>
                    </div>
                    <div class="rp-tooltip">Limite de tokens do conhecimento enviado para a IA. Mais tokens = mais contexto, porem maior uso da cota do Groq.</div>
                  </div>
                  <div class="rp-item">
                    <label><span class="rp-label-icon">?</span> Chunk</label>
                    <div class="rp-stepper">
                      <button class="rp-btn" onclick="rpStep('rag-chunk-size',-50,50,1000)">&#8722;</button>
                      <input type="number" id="rag-chunk-size" class="rp-input" min="50" max="1000" value="400">
                      <button class="rp-btn" onclick="rpStep('rag-chunk-size',50,50,1000)">&#43;</button>
                    </div>
                    <div class="rp-tooltip">Tamanho de cada pedaco de texto ao indexar documentos. Chunks menores sao mais precisos; maiores preservam mais contexto.</div>
                  </div>
                  <div class="rp-item">
                    <label><span class="rp-label-icon">?</span> Sobreposicao</label>
                    <div class="rp-stepper">
                      <button class="rp-btn" onclick="rpStep('rag-chunk-overlap',-10,0,200)">&#8722;</button>
                      <input type="number" id="rag-chunk-overlap" class="rp-input" min="0" max="200" value="80">
                      <button class="rp-btn" onclick="rpStep('rag-chunk-overlap',10,0,200)">&#43;</button>
                    </div>
                    <div class="rp-tooltip">Quantos tokens um chunk compartilha com o seguinte. Evita cortar frases no meio e perde o sentido entre trechos.</div>
                  </div>
                </div>
                <button class="btn-primary" style="width:fit-content;margin-top:.25rem" onclick="saveRagConfig(this)">Salvar parametros</button>
              </div>
            </div>
          </div>
        </div>
        <div class="config-section" style="margin-bottom:1.25rem">
          <div class="config-section-hdr">Prompt do Sistema (edicao direta)</div>
          <div class="config-body">
            <div class="config-row" style="flex-direction:column;align-items:stretch;gap:.75rem">
              <div class="config-hint"><strong>Atencao:</strong> editar aqui substitui o prompt gerado automaticamente pelas abas Loja, Identidade e FAQ. Use o botao abaixo para regenerar a partir das configuracoes estruturadas.<br>
                <button style="margin-top:.5rem;font-size:.76rem;padding:.28rem .7rem;border-radius:6px;border:1px solid var(--border2);background:var(--surface);cursor:pointer;color:var(--text2);font-family:inherit" onclick="rebuildPrompt()">&#8635; Regenerar prompt das abas estruturadas</button>
              </div>
              <textarea id="system-prompt-ta" class="prompt-textarea" rows="18" placeholder="Carregando..."></textarea>
              <button class="btn-primary" style="width:fit-content" onclick="savePrompt(this)">Salvar prompt direto</button>
            </div>
          </div>
        </div>
        <div class="config-section">
          <div class="config-section-hdr">Integracoes e Acesso</div>
          <div class="config-body">
            <div class="config-row">
              <div class="config-key">Google Calendar</div>
              <div class="config-val">{cal_badge}<div class="config-hint">Configure em <code>server/.env</code>:<br><code>CALENDAR_EMBED_URL=https://calendar.google.com/calendar/embed?src=...</code></div></div>
            </div>
            <div class="config-row">
              <div class="config-key">WhatsApp (Evolution API)</div>
              <div class="config-val"><span class="config-badge ok">&#10003; Configurado via .env</span><div class="config-hint">Variaveis: <code>EVOLUTION_URL</code>, <code>EVOLUTION_KEY</code>, <code>EVOLUTION_INSTANCE</code></div></div>
            </div>
            <div class="config-row">
              <div class="config-key">Token de administrador</div>
              <div class="config-val"><span class="config-badge ok">&#10003; Definido</span><div class="config-hint">Defina em <code>server/.env</code>: <code>ADMIN_TOKEN=sua_senha_aqui</code></div></div>
            </div>
            <div class="config-row">
              <div class="config-key">Acesso externo</div>
              <div class="config-val"><div class="config-hint">Para acesso externo use <strong>Cloudflare Tunnel</strong> ou <strong>Tailscale</strong>. Consulte o README.</div></div>
            </div>
          </div>
        </div>
      </div>

      <!-- PANE: Monitoramento -->
      <div id="cfg-pane-monitoramento" class="cfg-pane">

        <!-- Saude dos servicos -->
        <div class="config-section">
          <div class="config-section-hdr status-hdr-row">
            <span>Status do Sistema</span>
            <div class="status-hdr-controls">
              <span class="status-live-indicator">
                <span class="status-live-dot"></span>ao vivo
              </span>
              <button class="btn-new" id="btn-refresh-status" onclick="refreshStatus(this)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                Atualizar
              </button>
            </div>
          </div>
          <div class="status-grid" id="status-grid">
            <div class="status-row-skeleton"></div>
            <div class="status-row-skeleton" style="opacity:.7"></div>
            <div class="status-row-skeleton" style="opacity:.5"></div>
            <div class="status-row-skeleton" style="opacity:.35"></div>
            <div class="status-row-skeleton" style="opacity:.2"></div>
          </div>
          <div class="status-footer">
            <span id="status-last-check" style="color:var(--text2)">Aguardando primeira verificacao...</span>
            <span>Proxima atualizacao em <strong id="status-next-refresh">30</strong>s</span>
          </div>
        </div>

        <!-- Registros — acordeao colapsavel -->
        <div class="config-section" style="margin-top:1.25rem">
          <div class="config-section-hdr log-section-hdr">
            <div style="display:flex;align-items:center;gap:.75rem">
              <span>Registros</span>
              <div class="log-count-row">
                <span class="log-count-chip log-count-error" id="log-count-error">—</span>
                <span class="log-count-chip log-count-warn"  id="log-count-warn">—</span>
              </div>
            </div>
            <button class="log-accordion-btn" id="log-acc-btn" onclick="toggleLogAccordion()">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              Ver registros
              <svg class="acc-arrow" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
            </button>
          </div>

          <!-- Corpo colapsavel -->
          <div class="log-accordion-body" id="log-accordion-body">
            <div class="log-filter-row">
              <button class="log-filter-btn" data-lf="all"   data-lf-active="all"   onclick="setLogFilter(this,'all')">Todos</button>
              <button class="log-filter-btn" data-lf="error"                         onclick="setLogFilter(this,'error')">&#128308; Erros</button>
              <button class="log-filter-btn" data-lf="warn"                          onclick="setLogFilter(this,'warn')">&#128993; Avisos</button>
              <button class="log-filter-btn" data-lf="info"                          onclick="setLogFilter(this,'info')">&#128994; Info</button>
              <input class="log-search" id="log-search" type="text" placeholder="&#128269; Buscar nos logs..." oninput="_schedLogSearch()">
              <select id="log-limit" onchange="loadErrorLogs()" title="Quantidade de registros exibidos"
                style="padding:.28rem .55rem;border:1px solid var(--border2);border-radius:var(--radius-sm);font-size:.78rem;font-family:inherit;background:var(--surface);color:var(--text2);cursor:pointer;outline:none;transition:border-color .15s">
                <option value="5"  selected>5 ultimos</option>
                <option value="10">10 ultimos</option>
                <option value="20">20 ultimos</option>
                <option value="50">50 ultimos</option>
              </select>
              <div style="margin-left:auto;display:flex;gap:.4rem">
                <button class="btn-export" onclick="exportLogs()" title="Baixar debug.log">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  Exportar
                </button>
                <button class="action-btn close-protocol-btn" id="btn-clear-logs" onclick="clearLogs()">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                  Limpar
                </button>
              </div>
            </div>
            <div style="overflow-x:auto">
              <table class="log-table">
                <thead>
                  <tr><th>Hora</th><th>Nivel</th><th>Modulo</th><th>Mensagem</th></tr>
                </thead>
                <tbody id="log-tbody">
                  <tr><td colspan="4" class="log-empty">Clique em "Ver registros" para carregar.</td></tr>
                </tbody>
              </table>
            </div>
            <div class="log-footer">
              <span id="log-footer-count">—</span>
              <span id="log-footer-meta">—</span>
            </div>
          </div>
        </div>

      </div>

    </section>

  </main>
</div>

<!-- MODAIS -->
<div id="modal-confirm" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeConfirmModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div>
    <h3 class="confirm-title">Cancelar agendamento?</h3>
    <p class="confirm-msg">Tem certeza que deseja cancelar? O agendamento podera ser recuperado depois se necessario.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeConfirmModal()">Voltar</button>
      <button class="btn-primary" onclick="confirmDoCancel()" style="background:#dc2626;">Sim, cancelar</button>
    </div>
  </div>
</div>

<div id="modal-confirm-dismiss" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeConfirmDismissModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon" style="background:#fff7ed;color:#d97706;"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
    <h3 class="confirm-title">Descartar aviso?</h3>
    <p class="confirm-msg">O aviso sera removido da lista. O agendamento e a sessao da IA nao serao alterados.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeConfirmDismissModal()">Voltar</button>
      <button class="btn-primary" onclick="confirmDoDismiss()" style="background:#d97706;">Sim, descartar</button>
    </div>
  </div>
</div>

<div id="modal-confirm-protocol" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeConfirmProtocolModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon" style="background:#f0f9ff;color:#0369a1;"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg></div>
    <h3 class="confirm-title">Encerrar protocolo?</h3>
    <p class="confirm-msg">O atendimento sera encerrado e removido do painel. Os dados ficam salvos no historico.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeConfirmProtocolModal()">Voltar</button>
      <button class="btn-primary" onclick="confirmDoCloseProtocol()" style="background:#0369a1;">Sim, encerrar</button>
    </div>
  </div>
</div>

<div id="modal-complete">
  <div class="modal-drag-handle" id="modal-complete-handle">
    <h2 class="modal-title">Concluir Atendimento</h2>
    <span class="modal-drag-hint"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg> Arrastar</span>
  </div>
  <div class="modal-body">
    <form id="form-complete" onsubmit="submitComplete(event)">
      <div class="form-group">
        <label>Observacoes (opcional)</label>
        <input type="text" id="complete-notes" placeholder="Ex: Receita emitida, retorno em 6 meses...">
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeCompleteModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-complete">Encerrar</button>
      </div>
    </form>
  </div>
</div>

<div id="modal-edit">
  <div class="modal-drag-handle" id="modal-edit-handle">
    <h2 class="modal-title">Editar Agendamento</h2>
    <span class="modal-drag-hint"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg> Arrastar</span>
  </div>
  <div class="modal-body">
    <form id="form-edit" onsubmit="submitEdit(event)">
      <div class="form-group"><label>Nome completo</label><input type="text" id="edit-name" required></div>
      <div class="form-group"><label>Telefone com DDD</label><input type="tel" id="edit-phone" required></div>
      <div class="form-row">
        <div class="form-group"><label>Data</label><input type="date" id="edit-date" required></div>
        <div class="form-group"><label>Hora</label><input type="time" id="edit-time" required></div>
      </div>
      <label style="display:flex;align-items:center;gap:.5rem;font-size:.8rem;color:var(--text2);margin-bottom:.75rem;cursor:pointer">
        <input type="checkbox" id="edit-notify" checked style="accent-color:var(--primary)">
        Notificar cliente via WhatsApp sobre a remarcacao
      </label>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeEditModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-edit">Salvar alteracoes</button>
      </div>
    </form>
  </div>
</div>

<div id="modal-new">
  <div class="modal-drag-handle" id="modal-handle">
    <h2 class="modal-title">Novo Agendamento</h2>
    <span class="modal-drag-hint"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg> Arrastar</span>
  </div>
  <div class="modal-body">
    <form id="form-new" onsubmit="submitNew(event)">
      <div class="form-group"><label>Nome completo</label><input type="text" id="new-name" placeholder="Ex: Maria Silva" required></div>
      <div class="form-group"><label>Telefone com DDD</label><input type="tel" id="new-phone" placeholder="48999999999" required></div>
      <div class="form-row">
        <div class="form-group"><label>Data</label><input type="date" id="new-date" required></div>
        <div class="form-group"><label>Hora</label><input type="time" id="new-time" required></div>
      </div>
      <label style="display:flex;align-items:center;gap:.5rem;font-size:.8rem;color:var(--text2);margin-bottom:.75rem;cursor:pointer">
        <input type="checkbox" id="new-notify" checked style="accent-color:var(--primary)">
        Notificar cliente via WhatsApp sobre o agendamento
      </label>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-new">Confirmar agendamento</button>
      </div>
    </form>
  </div>
</div>

<div id="modal-doc" style="display:none;position:fixed;z-index:1000;width:560px;max-width:92vw;background:var(--surface);color:var(--text);border-radius:var(--radius);box-shadow:var(--shadow-lg);border:1px solid var(--border)">
  <div class="modal-drag-handle" id="modal-doc-handle">
    <h2 class="modal-title">Adicionar Documento</h2>
    <span class="modal-drag-hint"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg> Arrastar</span>
  </div>
  <div class="modal-body">
    <form id="form-doc" onsubmit="submitDoc(event)">
      <div class="form-group"><label>Titulo</label><input type="text" id="doc-title" placeholder="Ex: Politica de cancelamento" required></div>
      <div class="form-group">
        <label>Tipo</label>
        <select id="doc-type" style="width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);padding:.4rem .6rem;font-size:.84rem;background:var(--surface2);color:var(--text)">
          <option value="faq">FAQ</option>
          <option value="policy">Politica</option>
          <option value="product_catalog">Catalogo de Produtos</option>
          <option value="script">Script</option>
          <option value="manual">Manual</option>
        </select>
      </div>
      <div class="form-group">
        <label>Conteudo (texto bruto)</label>
        <textarea id="doc-content" rows="10" placeholder="Cole aqui o texto que a IA usara como base de conhecimento..." required style="width:100%;font-size:.8rem;font-family:inherit;border:1px solid var(--border);border-radius:var(--radius-sm);padding:.5rem .75rem;background:var(--surface2);color:var(--text);resize:vertical;line-height:1.5"></textarea>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeDocModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-doc">Indexar e Salvar</button>
      </div>
    </form>
  </div>
</div>

<div id="modal-faq" style="display:none;position:fixed;z-index:1000;width:520px;max-width:92vw;background:var(--surface);color:var(--text);border-radius:var(--radius);box-shadow:var(--shadow-lg);border:1px solid var(--border)">
  <div class="modal-drag-handle" id="modal-faq-handle">
    <h2 class="modal-title" id="faq-modal-title">Adicionar FAQ</h2>
    <span class="modal-drag-hint"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg> Arrastar</span>
  </div>
  <div class="modal-body">
    <form id="form-faq" onsubmit="submitFaq(event)">
      <input type="hidden" id="faq-edit-id" value="">
      <div class="form-group"><label>Pergunta</label><input type="text" id="faq-question" placeholder="Ex: Voces aceitam convenio?" required></div>
      <div class="form-group">
        <label>Resposta</label>
        <textarea id="faq-answer" rows="4" placeholder="Ex: Atendemos particulares, mas o exame de vista e totalmente gratuito!" required style="width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);padding:.5rem .75rem;font-size:.84rem;font-family:inherit;background:var(--surface2);color:var(--text);resize:vertical;line-height:1.5;outline:none;transition:border-color .15s,box-shadow .15s"></textarea>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeFaqModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-faq">Salvar</button>
      </div>
    </form>
  </div>
</div>

<!-- MODAL TEMPLATE PERSONALIZADO -->
<div id="modal-custom-tpl" style="display:none;position:fixed;z-index:1000;width:520px;max-width:92vw;background:var(--surface);color:var(--text);border-radius:var(--radius);box-shadow:var(--shadow-lg);border:1px solid var(--border)">
  <div class="modal-drag-handle" id="modal-custom-tpl-handle">
    <h2 class="modal-title" id="custom-tpl-modal-title">Novo Template</h2>
    <span class="modal-drag-hint"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg> Arrastar</span>
  </div>
  <div class="modal-body">
    <form id="form-custom-tpl" onsubmit="submitCustomTpl(event)">
      <input type="hidden" id="custom-tpl-edit-id" value="">
      <div class="form-group">
        <label>Nome do template <span style="color:#dc2626">*</span></label>
        <input type="text" id="custom-tpl-name" placeholder="Ex: Confirmacao de consulta, Aviso de atraso..." required>
      </div>
      <div class="form-group" style="margin-bottom:.4rem">
        <label>Variaveis disponiveis</label>
        <div class="notif-var-row" style="margin-bottom:0">
          <span class="notif-var-chip" onclick="insertVar('custom-tpl-content','{{nome}}')">&#123;nome&#125;</span>
          <span class="notif-var-chip" onclick="insertVar('custom-tpl-content','{{data}}')">&#123;data&#125;</span>
          <span class="notif-var-chip" onclick="insertVar('custom-tpl-content','{{hora}}')">&#123;hora&#125;</span>
          <span class="notif-var-chip" onclick="insertVar('custom-tpl-content','{{telefone}}')">&#123;telefone&#125;</span>
        </div>
      </div>
      <div class="form-group">
        <label>Mensagem <span style="color:#dc2626">*</span></label>
        <textarea id="custom-tpl-content" class="notif-ta" rows="7"
          placeholder="Ex: Ola, {{nome}}! Passando para confirmar sua consulta no dia {{data}} as {{hora}}h. Te esperamos!"
          oninput="updateCharCount(this,'custom-tpl-cc')" required></textarea>
        <div class="notif-char-count" id="custom-tpl-cc">0 caracteres</div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeCustomTplModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-custom-tpl">Salvar template</button>
      </div>
    </form>
  </div>
</div>

<!-- MODAL CONFIRMAR EXCLUSAO TEMPLATE -->
<div id="modal-confirm-ctpl-del" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="document.getElementById('modal-confirm-ctpl-del').classList.remove('open')"></div>
  <div class="confirm-box">
    <div class="confirm-icon" style="background:#fef2f2;color:#dc2626;">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
    </div>
    <h3 class="confirm-title">Excluir template?</h3>
    <p class="confirm-msg" id="ctpl-del-msg">Esta acao nao pode ser desfeita.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="document.getElementById('modal-confirm-ctpl-del').classList.remove('open')">Cancelar</button>
      <button class="btn-primary" id="btn-confirm-ctpl-del" style="background:#dc2626;">Sim, excluir</button>
    </div>
  </div>
</div>

<!-- MODAL CLIENTE -->
<div id="modal-client" style="display:none;position:fixed;z-index:1000;width:520px;max-width:92vw;background:var(--surface);color:var(--text);border-radius:var(--radius);box-shadow:var(--shadow-lg);border:1px solid var(--border)">
  <div class="modal-drag-handle" id="modal-client-handle">
    <h2 class="modal-title" id="client-modal-title">Novo Cliente</h2>
    <span class="modal-drag-hint"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg> Arrastar</span>
  </div>
  <div class="modal-body">
    <form id="form-client" onsubmit="submitClient(event)">
      <input type="hidden" id="client-edit-id" value="">
      <div class="form-row">
        <div class="form-group">
          <label>Nome <span style="color:#dc2626">*</span></label>
          <input type="text" id="client-first-name" placeholder="Ex: Maria" required>
        </div>
        <div class="form-group">
          <label>Sobrenome</label>
          <input type="text" id="client-last-name" placeholder="Ex: Silva">
        </div>
      </div>
      <div class="form-group">
        <label>Telefone (com DDD)</label>
        <input type="tel" id="client-phone" placeholder="Ex: 48999999999">
      </div>
      <div class="form-group">
        <label>Data de Nascimento</label>
        <input type="date" id="client-birth-date">
      </div>
      <div class="form-group">
        <label>Data da Ultima Consulta</label>
        <input type="date" id="client-apt-date" onchange="suggestReturnDate()">
      </div>
      <div class="form-group">
        <label>Observacoes / Historico do Atendimento</label>
        <textarea id="client-notes" class="client-notes-ta" rows="3"
          placeholder="Ex: Cliente fez oculos de grau, modelo: Marca Propria, retorno em 6 meses"
          oninput="parseReturnFromNotes()"></textarea>
        <div class="return-parse-hint" id="return-parse-hint"></div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Retorno em (meses)</label>
          <input type="number" id="client-return-months" min="1" max="36" placeholder="Ex: 6" oninput="calcReturnDateFromMonths()">
          <span class="bcf-hint" style="font-size:.7rem">Preencha para calcular a data automaticamente.</span>
        </div>
        <div class="form-group">
          <label>Data de Retorno</label>
          <input type="date" id="client-return-date">
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeClientModal()">Cancelar</button>
        <button type="submit" class="btn-primary" id="btn-submit-client">Salvar</button>
      </div>
    </form>
  </div>
</div>

<!-- MODAL CONFIRMAR EXCLUSAO CLIENTE -->
<div id="modal-confirm-client-del" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeClientDelModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon" style="background:#fef2f2;color:#dc2626;">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
    </div>
    <h3 class="confirm-title">Excluir cliente?</h3>
    <p class="confirm-msg" id="client-del-msg">Esta acao nao pode ser desfeita.</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeClientDelModal()">Cancelar</button>
      <button class="btn-primary" onclick="confirmDeleteClient()" style="background:#dc2626;">Sim, excluir</button>
    </div>
  </div>
</div>

<!-- MODAL CONFIRMAR NOTIFICACAO CLIENTE -->
<div id="modal-confirm-client-notify" class="confirm-overlay">
  <div class="confirm-backdrop" onclick="closeNotifyModal()"></div>
  <div class="confirm-box">
    <div class="confirm-icon" style="background:#ecfdf5;color:#059669;">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
    </div>
    <h3 class="confirm-title">Enviar lembrete?</h3>
    <p class="confirm-msg" id="client-notify-msg">Enviar lembrete de retorno via WhatsApp para este cliente?</p>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;">
      <button class="btn-secondary" onclick="closeNotifyModal()">Cancelar</button>
      <button class="btn-primary" onclick="confirmNotifyClient()" style="background:#059669;">Sim, enviar</button>
    </div>
  </div>
</div>

<script>
  const ADMIN_TOKEN = "{admin_token}";
  const TODAY_STR   = "{today}";
  const PENDING_ITEMS = {pending_json};
  window._PANEL_DATA = {{
    confirmados:       {confirmados_tab},
    cancelados:        {cancelados_tab},
    concluidos:        {concluidos_tab},
    hoje:              {hoje_dia_count},
    pendente:          {pendente_tab},
    hoje_confirmados:  {hoje_confirmados},
    hoje_aguardando:   {hoje_aguardando},
    hoje_sem_lembrete: {hoje_sem_lembrete},
    trend_confirmados: {trend_confirmados},
    trend_cancelados:  {trend_cancelados},
    ai_errors_n:       {ai_errors_n},
    overdue_n:         {overdue_count},
    chart30:           {chart30_json},
    chart30d:          {chart30d_json},
    chart_avg:         {_chart_avg},
  }};
</script>
<script src="/static/panel.js"></script>
<script>
  if (typeof navTo !== "function") {{
    document.body.innerHTML = '<div style="font-family:sans-serif;padding:3rem;text-align:center;color:#c00">'
      + '<h2>Erro ao carregar o painel</h2>'
      + '<p>Os arquivos estáticos não foram encontrados (<code>/static/panel.js</code> retornou 404).</p>'
      + '<p>Reinicie o servidor e limpe o cache do navegador (Ctrl+Shift+R).</p>'
      + '<pre style="text-align:left;background:#f5f5f5;padding:1rem;display:inline-block">'
      + 'cd server\\npython -m uvicorn main:app --reload --host 0.0.0.0</pre>'
      + '</div>';
  }}
</script>

</body>
</html>"""
