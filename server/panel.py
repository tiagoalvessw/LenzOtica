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


def render_panel(agendamentos: list, calendar_embed_url: str = "", admin_token: str = "", pending_items: list = None, clients_count: int = 0) -> str:
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
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{
      --primary:#2563eb;--primary-dark:#1d4ed8;--primary-glow:rgba(37,99,235,.15);
      --sb-bg:#0c1425;--sb-text:#64748b;--sb-w:220px;--sb-cw:64px;
      --bg:#f1f5f9;--surface:#fff;--surface2:#f8fafc;
      --text:#0f172a;--text2:#475569;--muted:#94a3b8;
      --border:#e2e8f0;--border2:#cbd5e1;
      --shadow-sm:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
      --shadow:0 4px 16px rgba(0,0,0,.08),0 1px 4px rgba(0,0,0,.04);
      --shadow-lg:0 10px 40px rgba(0,0,0,.14),0 2px 8px rgba(0,0,0,.06);
      --radius:12px;--radius-sm:8px;
    }}
    [data-theme="dark"]{{
      --bg:#0f172a;--surface:#1e293b;--surface2:#162032;
      --text:#f1f5f9;--text2:#94a3b8;--muted:#64748b;
      --border:#334155;--border2:#475569;
      --shadow-sm:0 1px 3px rgba(0,0,0,.3);
      --shadow:0 4px 16px rgba(0,0,0,.35);
      --shadow-lg:0 10px 40px rgba(0,0,0,.5);
      --sb-bg:#020617;
    }}
    html,body{{height:100%;font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.5}}
    body{{display:flex;overflow:hidden}}

    /* SIDEBAR */
    .sidebar{{width:var(--sb-w);flex-shrink:0;height:100vh;background:var(--sb-bg);display:flex;flex-direction:column;transition:width .2s ease;overflow:hidden;z-index:200}}
    .sidebar.collapsed{{width:var(--sb-cw)}}
    .sb-logo{{height:64px;display:flex;align-items:center;gap:.75rem;padding:0 1rem;border-bottom:1px solid rgba(255,255,255,.06);flex-shrink:0;overflow:hidden;white-space:nowrap}}
    .sb-logo img{{height:36px;width:36px;border-radius:8px;flex-shrink:0;object-fit:cover}}
    .sb-logo-text{{opacity:1;transition:opacity .15s;overflow:hidden}}
    .sidebar.collapsed .sb-logo-text{{opacity:0;pointer-events:none}}
    .sb-logo-title{{font-size:.9rem;font-weight:700;color:#f1f5f9;letter-spacing:-.01em}}
    .sb-logo-sub{{font-size:.62rem;color:#475569;letter-spacing:.02em}}
    .sb-nav{{flex:1;padding:.75rem .5rem;display:flex;flex-direction:column;gap:.15rem;overflow-y:auto;overflow-x:hidden}}
    .nav-item{{display:flex;align-items:center;gap:.7rem;padding:.6rem .75rem;border-radius:8px;color:var(--sb-text);font-size:.83rem;font-weight:500;cursor:pointer;border:none;background:none;font-family:inherit;transition:background .12s,color .12s;white-space:nowrap;overflow:hidden;width:100%;text-align:left}}
    .nav-item:hover{{background:rgba(255,255,255,.07);color:#cbd5e1}}
    .nav-item.active{{background:rgba(37,99,235,.2);color:#93c5fd}}
    .nav-item svg{{flex-shrink:0}}
    .nav-label{{flex:1}}
    .nav-badge{{background:#2563eb;color:#fff;font-size:.62rem;font-weight:700;padding:.1rem .42rem;border-radius:999px;min-width:18px;text-align:center;flex-shrink:0}}
    .sidebar.collapsed .nav-label,.sidebar.collapsed .nav-badge{{display:none}}
    .sb-footer{{border-top:1px solid rgba(255,255,255,.06);padding:.5rem}}
    .sb-toggle{{display:flex;align-items:center;justify-content:center;gap:.6rem;padding:.55rem .75rem;border-radius:8px;color:#475569;font-size:.78rem;font-weight:500;cursor:pointer;border:none;background:none;font-family:inherit;transition:background .12s,color .12s;width:100%;white-space:nowrap;overflow:hidden}}
    .sb-toggle:hover{{background:rgba(255,255,255,.07);color:#94a3b8}}
    .sidebar.collapsed .toggle-lbl{{display:none}}

    /* APP SHELL */
    .app-shell{{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}}
    header{{height:56px;background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 1.5rem;flex-shrink:0;gap:1rem}}
    .header-title{{font-size:.95rem;font-weight:700;color:var(--text);letter-spacing:-.01em}}
    .header-right{{display:flex;align-items:center;gap:.75rem}}
    #theme-btn{{background:var(--surface2);border:1px solid var(--border);color:var(--text2);cursor:pointer;padding:.35rem .5rem;border-radius:8px;display:flex;align-items:center;justify-content:center;transition:background .15s}}
    #theme-btn:hover{{background:var(--bg)}}
    .refresh-wrap{{text-align:right;font-size:.72rem;color:var(--text2);line-height:1.7}}
    main{{flex:1;overflow-y:auto;overflow-x:hidden}}

    /* PAGES */
    .page{{display:none;padding:1.5rem;max-width:1600px}}
    .page.active{{display:block}}
    .page-header{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:1.5rem;flex-wrap:wrap;gap:.75rem}}
    .page-title{{font-size:1.3rem;font-weight:700;letter-spacing:-.02em;color:var(--text)}}
    .page-subtitle{{font-size:.78rem;color:var(--muted);margin-top:.2rem}}

    /* METRICS */
    .metrics-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:1rem;margin-bottom:1.25rem}}
    .metric-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.1rem 1.2rem;box-shadow:var(--shadow-sm);position:relative;overflow:hidden}}
    .metric-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:var(--radius) var(--radius) 0 0}}
    .mc-blue::before{{background:#2563eb}}.mc-green::before{{background:#059669}}
    .mc-red::before{{background:#dc2626}}.mc-cyan::before{{background:#0891b2}}
    .mc-amber::before{{background:#d97706}}.mc-purple::before{{background:#7c3aed}}
    .metric-num{{font-size:2rem;font-weight:700;letter-spacing:-.04em;line-height:1;margin-bottom:.3rem}}
    .mc-blue .metric-num{{color:#2563eb}}.mc-green .metric-num{{color:#059669}}
    .mc-red .metric-num{{color:#dc2626}}.mc-cyan .metric-num{{color:#0891b2}}
    .mc-amber .metric-num{{color:#d97706}}.mc-purple .metric-num{{color:#7c3aed}}
    .metric-lbl{{font-size:.67rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}

    /* DASH CARDS */
    .dash-row{{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.25rem}}
    .dash-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow-sm);overflow:hidden;margin-bottom:1.25rem}}
    .dash-card-hdr{{padding:.875rem 1.25rem;border-bottom:1px solid var(--border);font-size:.82rem;font-weight:600;color:var(--text);background:var(--surface2)}}
    .dash-card-body{{padding:1.25rem}}

    /* BAR CHART */
    .bar-chart{{display:flex;align-items:flex-end;gap:.4rem;height:120px}}
    .chart-col{{flex:1;display:flex;flex-direction:column;align-items:center;height:100%;gap:.25rem}}
    .chart-bar-wrap{{flex:1;width:100%;display:flex;align-items:flex-end}}
    .chart-bar{{width:100%;background:#bfdbfe;border-radius:4px 4px 0 0;position:relative;min-height:4px;transition:background .15s;cursor:default}}
    .chart-bar.bar-today{{background:var(--primary)}}
    .chart-bar:hover{{opacity:.8}}
    .chart-val{{position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-size:.62rem;font-weight:600;color:var(--text2);white-space:nowrap}}
    .chart-lbl{{font-size:.62rem;color:var(--muted);font-weight:500}}
    [data-theme="dark"] .chart-bar{{background:#1e3a5f}}
    [data-theme="dark"] .chart-bar.bar-today{{background:var(--primary)}}

    /* STATUS BREAKDOWN */
    .status-list{{display:flex;flex-direction:column;gap:.65rem}}
    .status-row{{display:flex;align-items:center;gap:.75rem}}
    .sr-label{{font-size:.78rem;color:var(--text2);width:105px;flex-shrink:0}}
    .sr-bar{{flex:1;height:8px;background:var(--border);border-radius:99px;overflow:hidden}}
    .sr-fill{{height:100%;border-radius:99px;transition:width .5s ease}}
    .sr-count{{font-size:.75rem;font-weight:600;color:var(--text);min-width:22px;text-align:right}}

    /* UPCOMING */
    .activity-list{{display:flex;flex-direction:column}}
    .activity-item{{display:flex;align-items:center;gap:.75rem;padding:.7rem 1.25rem;border-bottom:1px solid var(--border);transition:background .1s}}
    .activity-item:last-child{{border-bottom:none}}
    .activity-item:hover{{background:var(--surface2)}}
    .act-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
    .act-info{{flex:1;min-width:0}}
    .act-name{{font-size:.84rem;font-weight:600;color:var(--text)}}
    .act-detail{{font-size:.74rem;color:var(--muted);margin-top:1px}}
    .act-time{{font-size:.72rem;color:var(--muted);white-space:nowrap}}

    /* TAB NAV */
    .tab-nav{{display:grid;grid-template-columns:repeat(6,1fr);gap:.875rem;margin-bottom:1.25rem}}
    .tab-nav .tab{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.1rem 1.2rem;box-shadow:var(--shadow-sm);text-align:left;color:var(--text);position:relative;overflow:hidden;transition:transform .15s,box-shadow .15s,background .12s,color .12s;cursor:pointer;font-family:inherit}}
    .tab-nav .tab::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:var(--radius) var(--radius) 0 0}}
    .tab-nav .tab[data-f="day"]::before{{background:var(--primary)}}
    .tab-nav .tab[data-f="confirmed"]::before{{background:#059669}}
    .tab-nav .tab[data-f="cancelled"]::before{{background:#dc2626}}
    .tab-nav .tab[data-f="completed"]::before{{background:#0891b2}}
    .tab-nav .tab[data-f="all"]::before{{background:#64748b}}
    .tab-nav .tab[data-f="pending"]::before{{background:#d97706}}
    .tab-nav .tab:hover{{transform:translateY(-2px);box-shadow:var(--shadow);border-color:var(--border2)}}
    .tab-nav .tab:active{{transform:translateY(0)}}
    .tab-nav .tab.active{{color:#fff;border-color:transparent}}
    .tab-nav .tab[data-f="day"].active{{background:var(--primary)}}
    .tab-nav .tab[data-f="confirmed"].active{{background:#059669}}
    .tab-nav .tab[data-f="cancelled"].active{{background:#dc2626}}
    .tab-nav .tab[data-f="completed"].active{{background:#0891b2}}
    .tab-nav .tab[data-f="all"].active{{background:#64748b}}
    .tab-nav .tab[data-f="pending"].active{{background:#d97706}}
    .tab-nav .num{{display:block;font-size:1.75rem;font-weight:700;line-height:1;letter-spacing:-.03em;margin-bottom:.3rem}}
    .tab-nav .lbl{{display:block;font-size:.67rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;opacity:.7}}

    /* TABLE PANEL */
    .panel{{background:var(--surface);border-radius:var(--radius);box-shadow:var(--shadow-sm);border:1px solid var(--border);overflow:hidden}}
    .panel-toolbar{{padding:.875rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;background:var(--surface2)}}
    .search-wrap{{position:relative;flex:1;min-width:200px}}
    .search-icon{{position:absolute;left:.7rem;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}}
    #search{{width:100%;padding:.5rem .8rem .5rem 2.2rem;border:1px solid var(--border2);border-radius:var(--radius-sm);font-size:.85rem;font-family:inherit;background:var(--surface);color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s}}
    #search::placeholder{{color:var(--muted)}}
    #search:focus{{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow)}}
    .btn-new{{padding:.44rem 1rem;border-radius:var(--radius-sm);font-size:.82rem;font-weight:600;font-family:inherit;cursor:pointer;border:none;background:var(--primary);color:#fff;white-space:nowrap;display:flex;align-items:center;gap:.35rem;transition:opacity .15s,transform .1s}}
    .btn-new:hover{{opacity:.88;transform:translateY(-1px)}}
    .btn-new:active{{transform:translateY(0)}}
    .table-wrap{{overflow-x:auto}}
    table{{width:100%;border-collapse:collapse;min-width:700px}}
    thead th{{background:var(--surface2);text-align:left;padding:.7rem 1.1rem;font-size:.67rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;border-bottom:1px solid var(--border);white-space:nowrap}}
    tbody td{{padding:.8rem 1.1rem;border-bottom:1px solid var(--border);font-size:.855rem;vertical-align:middle}}
    tbody tr:last-child td{{border-bottom:none}}
    tbody tr{{transition:background .1s}}
    tbody tr:hover td{{background:var(--surface2)}}
    tbody tr.row-today td{{background:#eff6ff}}
    tbody tr.row-today:hover td{{background:#dbeafe}}
    [data-theme="dark"] tbody tr:hover td{{background:#1e2d40}}
    [data-theme="dark"] tbody tr.row-today td{{background:#172554}}
    [data-theme="dark"] tbody tr.row-today:hover td{{background:#1e3a5f}}
    .client-name{{font-weight:600;color:var(--text)}}
    .phone-num{{font-size:.8rem;color:var(--text2);font-family:'SF Mono','Fira Code',monospace;letter-spacing:.02em}}
    .date-cell{{display:flex;align-items:center;gap:.4rem;white-space:nowrap}}
    .time-chip{{display:inline-block;background:var(--bg);border:1px solid var(--border);border-radius:5px;padding:.15rem .5rem;font-size:.8rem;font-weight:600;color:var(--text2);letter-spacing:.02em}}
    .faltam{{font-size:.8rem;font-weight:500}}
    .time-ok{{color:#059669}}.time-soon{{color:#d97706}}.time-past{{color:var(--muted)}}
    .hoje-tag{{background:var(--primary);color:#fff;font-size:.58rem;font-weight:700;padding:.12rem .4rem;border-radius:4px;vertical-align:middle;letter-spacing:.04em}}

    /* BADGES */
    .badge{{display:inline-flex;align-items:center;padding:.22rem .7rem;border-radius:999px;font-size:.72rem;font-weight:600;white-space:nowrap;letter-spacing:.02em}}
    .badge.scheduled{{background:#fef9c3;color:#854d0e;border:1px solid #fde68a}}
    .badge.day_reminder_sent{{background:#dbeafe;color:#1e40af;border:1px solid #bfdbfe}}
    .badge.reminder_sent{{background:#e0e7ff;color:#3730a3;border:1px solid #c7d2fe}}
    .badge.response_received{{background:#ede9fe;color:#5b21b6;border:1px solid #ddd6fe}}
    .badge.confirmed{{background:#d1fae5;color:#065f46;border:1px solid #a7f3d0}}
    .badge.attended{{background:#ccfbf1;color:#0f766e;border:1px solid #99f6e4}}
    .badge.no_show{{background:#ffedd5;color:#9a3412;border:1px solid #fed7aa}}
    .badge.completed{{background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd}}
    .badge.cancelled{{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}}
    [data-theme="dark"] .badge.scheduled{{background:#2a1c00;color:#fbbf24;border-color:#78350f}}
    [data-theme="dark"] .badge.day_reminder_sent{{background:#1e3a5f;color:#93c5fd;border-color:#1e40af}}
    [data-theme="dark"] .badge.reminder_sent{{background:#1e1b4b;color:#a5b4fc;border-color:#3730a3}}
    [data-theme="dark"] .badge.response_received{{background:#2e1065;color:#c4b5fd;border-color:#5b21b6}}
    [data-theme="dark"] .badge.confirmed{{background:#052e16;color:#6ee7b7;border-color:#065f46}}
    [data-theme="dark"] .badge.attended{{background:#042f2e;color:#5eead4;border-color:#0f766e}}
    [data-theme="dark"] .badge.no_show{{background:#431407;color:#fdba74;border-color:#9a3412}}
    [data-theme="dark"] .badge.completed{{background:#082f49;color:#7dd3fc;border-color:#0369a1}}
    [data-theme="dark"] .badge.cancelled{{background:#450a0a;color:#fca5a5;border-color:#991b1b}}

    /* ACTION BUTTONS */
    .actions-cell{{display:flex;gap:.35rem;align-items:center;flex-wrap:wrap}}
    .action-btn{{display:inline-flex;align-items:center;gap:.28rem;padding:.3rem .65rem;border-radius:6px;font-size:.72rem;font-weight:600;font-family:inherit;cursor:pointer;border:1px solid transparent;transition:opacity .15s,transform .1s;white-space:nowrap}}
    .action-btn:hover{{opacity:.82;transform:translateY(-1px)}}
    .action-btn:active{{transform:translateY(0)}}
    .action-btn:disabled{{opacity:.4;cursor:not-allowed;transform:none}}
    .remind-btn{{background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe}}
    .edit-btn{{background:#f5f3ff;color:#5b21b6;border-color:#ddd6fe}}
    .cancel-btn{{background:#fef2f2;color:#b91c1c;border-color:#fecaca}}
    .recover-btn{{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}}
    .confirm-btn{{background:#f0fdf4;color:#15803d;border-color:#bbf7d0}}
    .close-protocol-btn{{background:#f1f5f9;color:#475569;border-color:#cbd5e1}}
    .reset-session-btn{{background:#f8fafc;color:#64748b;border-color:#e2e8f0}}
    [data-theme="dark"] .remind-btn{{background:#1e3a5f;color:#93c5fd;border-color:#1e40af}}
    [data-theme="dark"] .edit-btn{{background:#1e1b4b;color:#a5b4fc;border-color:#3730a3}}
    [data-theme="dark"] .cancel-btn{{background:#450a0a;color:#fca5a5;border-color:#7f1d1d}}
    [data-theme="dark"] .recover-btn{{background:#052e16;color:#6ee7b7;border-color:#065f46}}
    [data-theme="dark"] .confirm-btn{{background:#052e16;color:#4ade80;border-color:#15803d}}
    [data-theme="dark"] .close-protocol-btn{{background:#1e293b;color:#94a3b8;border-color:#334155}}
    [data-theme="dark"] .reset-session-btn{{background:#0f172a;color:#64748b;border-color:#1e293b}}
    .empty-row{{text-align:center;padding:3rem 1rem}}
    .empty-state{{display:flex;flex-direction:column;align-items:center;color:var(--muted);font-size:.88rem}}

    /* CALENDAR LAYOUT */
    .layout{{display:flex;align-items:start;gap:0}}
    .layout-left{{flex:1;min-width:0;padding-right:1.5rem}}
    .resize-handle{{width:10px;flex-shrink:0;cursor:col-resize;position:relative;align-self:stretch;border-radius:4px;transition:background .15s;margin:0 .1rem}}
    .resize-handle:hover,.resize-handle.dragging{{background:var(--border2)}}
    .resize-handle::after{{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:3px;height:36px;border-radius:99px;background:var(--border2);transition:background .15s}}
    .resize-handle:hover::after,.resize-handle.dragging::after{{background:var(--primary)}}
    .layout-right{{width:400px;min-width:260px;max-width:900px;flex-shrink:0;position:sticky;top:0}}
    .calendar-panel{{background:var(--surface);border-radius:var(--radius);box-shadow:var(--shadow-sm);border:1px solid var(--border);overflow:hidden}}
    .calendar-header{{padding:.875rem 1.25rem;font-size:.82rem;font-weight:600;border-bottom:1px solid var(--border);color:var(--text);display:flex;align-items:center;gap:.5rem;background:var(--surface2)}}
    .cal-dot{{width:8px;height:8px;border-radius:50%;background:#4285f4;flex-shrink:0}}
    .cal-empty{{padding:2.5rem 1.5rem;text-align:center;color:var(--muted);font-size:.83rem;line-height:1.8}}
    .cal-empty-icon{{font-size:2.2rem;margin-bottom:.75rem}}
    .cal-empty code{{display:inline-block;background:var(--bg);padding:.2rem .5rem;border-radius:5px;font-size:.72rem;word-break:break-all;margin:.2rem 0;border:1px solid var(--border)}}

    /* IA PAGE */
    .ia-status-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem 1.5rem;display:flex;align-items:center;gap:1.25rem;margin-bottom:1.25rem;box-shadow:var(--shadow-sm);flex-wrap:wrap}}
    .ia-dot{{width:12px;height:12px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 4px rgba(34,197,94,.2);flex-shrink:0;animation:pulse 2s infinite}}
    @keyframes pulse{{0%,100%{{box-shadow:0 0 0 4px rgba(34,197,94,.2)}}50%{{box-shadow:0 0 0 8px rgba(34,197,94,.06)}}}}
    .ia-status-info{{flex:1;min-width:120px}}
    .ia-status-title{{font-weight:600;color:var(--text);margin-bottom:.15rem}}
    .ia-status-sub{{font-size:.78rem;color:var(--muted)}}
    .ia-stat{{text-align:center;padding:0 1.25rem;border-left:1px solid var(--border)}}
    .ia-stat-num{{font-size:1.5rem;font-weight:700;color:var(--primary)}}
    .ia-stat-lbl{{font-size:.67rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}}

    /* CONFIG PAGE */
    .config-section{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow-sm);margin-bottom:1.25rem}}
    .config-section-hdr{{padding:.875rem 1.25rem;border-bottom:1px solid var(--border);font-size:.85rem;font-weight:600;color:var(--text);background:var(--surface2)}}
    .config-body{{padding:0 1.5rem}}
    .config-row{{display:flex;align-items:flex-start;gap:1.5rem;padding:.9rem 0;border-bottom:1px solid var(--border)}}
    .config-row:last-child{{border-bottom:none}}
    .config-key{{font-size:.78rem;font-weight:600;color:var(--text2);min-width:185px;padding-top:.15rem}}
    .config-val{{flex:1;font-size:.84rem;color:var(--text)}}
    .config-badge{{display:inline-flex;align-items:center;gap:.3rem;padding:.18rem .6rem;border-radius:999px;font-size:.7rem;font-weight:600}}
    .config-badge.ok{{background:#d1fae5;color:#065f46}}
    .config-badge.err{{background:#fee2e2;color:#991b1b}}
    [data-theme="dark"] .config-badge.ok{{background:#052e16;color:#6ee7b7}}
    [data-theme="dark"] .config-badge.err{{background:#450a0a;color:#fca5a5}}
    .config-hint{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:.65rem .9rem;font-size:.77rem;color:var(--text2);line-height:1.7;margin-top:.6rem}}
    .config-hint code{{background:var(--bg);padding:.1rem .35rem;border-radius:4px;font-size:.74rem;border:1px solid var(--border2)}}
    /* TOGGLE SWITCH */
    .toggle-switch{{display:inline-flex;align-items:center;cursor:pointer;gap:.5rem}}
    .toggle-switch input{{display:none}}
    .toggle-track{{width:38px;height:20px;background:var(--border2);border-radius:999px;position:relative;transition:background .2s;flex-shrink:0}}
    .toggle-switch input:checked + .toggle-track{{background:var(--primary)}}
    .toggle-thumb{{position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.2);transition:transform .2s}}
    .toggle-switch input:checked + .toggle-track .toggle-thumb{{transform:translateX(18px)}}
    /* BUSINESS HOURS */
    .bh-grid{{display:flex;flex-direction:column;gap:.35rem;margin-top:.5rem}}
    .bh-row{{display:flex;align-items:center;gap:.75rem;padding:.35rem 0;border-bottom:1px solid var(--border)}}
    .bh-row:last-child{{border-bottom:none}}
    .bh-day{{min-width:90px;font-size:.82rem;font-weight:600;color:var(--text)}}
    .bh-flex-lbl{{font-size:.72rem;color:var(--muted)}}
    .rp-input{{border:1px solid var(--border);border-radius:var(--radius-sm);padding:.3rem .5rem;font-size:.82rem;background:var(--surface2);color:var(--text);width:90px}}
    .rp-input:disabled{{opacity:.35;cursor:not-allowed}}
    /* PROMPT */
    .prompt-textarea{{width:100%;font-size:.77rem;font-family:monospace;border:1px solid var(--border);border-radius:var(--radius-sm);padding:.65rem .9rem;background:var(--surface2);color:var(--text);resize:vertical;line-height:1.6;min-height:240px}}
    /* RAG PARAMS */
    .rag-params{{display:flex;flex-wrap:wrap;gap:1rem;margin-bottom:.5rem}}
    .rp-item{{display:flex;flex-direction:column;gap:.25rem}}
    .rp-item label{{font-size:.72rem;color:var(--text2);font-weight:600;white-space:nowrap}}
    .rp-item .rp-input{{width:110px}}
    .rag-section-hdr{{display:flex;align-items:center;justify-content:space-between}}

    /* RAG CONHECIMENTO — banner, guia de tipos, legenda */
    .rag-how-banner{{background:linear-gradient(135deg,#eff6ff,#f0f9ff);border:1px solid #bfdbfe;border-radius:var(--radius);padding:1.1rem 1.5rem;margin-bottom:1.25rem}}
    [data-theme="dark"] .rag-how-banner{{background:linear-gradient(135deg,#172554,#082f49);border-color:#1e3a5f}}
    .rag-how-title{{font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:.85rem;display:flex;align-items:center;gap:.5rem}}
    .rag-steps-row{{display:flex;align-items:stretch;gap:.75rem;flex-wrap:wrap}}
    .rag-step-item{{flex:1;min-width:140px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);padding:.75rem 1rem;font-size:.78rem;color:var(--text2);line-height:1.5}}
    .rag-step-item strong{{display:block;color:var(--text);margin-bottom:.25rem;font-size:.82rem}}
    .rag-step-num{{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:var(--primary);color:#fff;font-size:.7rem;font-weight:700;margin-bottom:.4rem;flex-shrink:0}}
    .rag-step-arrow{{color:var(--muted);font-size:1.3rem;align-self:center;flex-shrink:0}}
    @media(max-width:700px){{.rag-step-arrow{{display:none}}}}
    .rag-type-guide{{display:flex;align-items:center;flex-wrap:wrap;gap:.4rem;padding:.5rem 0;border-bottom:1px dashed var(--border);margin-bottom:.5rem}}
    .rag-type-guide-title{{font-size:.74rem;font-weight:600;color:var(--text2);margin-right:.25rem;white-space:nowrap}}
    .rag-type-chip{{display:inline-flex;align-items:center;gap:.25rem;padding:.22rem .65rem;border-radius:999px;font-size:.72rem;font-weight:500;background:var(--surface2);border:1px solid var(--border);color:var(--text2);cursor:default;transition:background .12s,border-color .12s;white-space:nowrap}}
    .rag-type-chip:hover{{background:var(--bg);border-color:var(--primary);color:var(--primary)}}
    .rag-sim-legend-row{{display:flex;align-items:center;gap:.15rem;flex-wrap:wrap}}
    .rag-sim-legend{{display:inline-flex;align-items:center;gap:.3rem;font-size:.7rem;color:var(--text2);margin-left:.4rem}}
    .rag-sim-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
    .sim-high{{background:#059669}}.sim-mid{{background:#d97706}}.sim-low{{background:#dc2626}}
    .sim-cell-high{{color:#059669;font-weight:600}}.sim-cell-mid{{color:#d97706;font-weight:600}}.sim-cell-low{{color:#dc2626;font-weight:600}}
    .rag-stats-row{{display:flex;align-items:center;gap:.5rem;font-size:.75rem;color:var(--muted)}}
    .rag-stat-chip{{display:inline-flex;align-items:center;gap:.25rem;padding:.15rem .5rem;border-radius:6px;background:var(--surface2);border:1px solid var(--border);font-weight:600;color:var(--text2)}}
    .rag-empty-box{{display:flex;flex-direction:column;align-items:center;gap:.75rem;padding:2rem 1rem;text-align:center}}
    .rag-empty-icon{{font-size:2.2rem}}
    .rag-empty-title{{font-size:.9rem;font-weight:700;color:var(--text)}}
    .rag-empty-sub{{font-size:.8rem;color:var(--muted);max-width:380px;line-height:1.6}}
    .rag-example-grid{{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin-top:.25rem}}
    .rag-example-item{{background:var(--surface2);border:1px dashed var(--border2);border-radius:var(--radius-sm);padding:.4rem .75rem;font-size:.74rem;color:var(--text2);cursor:pointer;transition:background .12s;white-space:nowrap}}
    .rag-example-item:hover{{background:var(--border);color:var(--text)}}

    /* CONFIG SUB-TABS */
    .cfg-tabs{{display:flex;gap:.35rem;margin-bottom:1.25rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.35rem;box-shadow:var(--shadow-sm)}}
    .cfg-tab{{flex:1;padding:.48rem .5rem;border-radius:var(--radius-sm);font-size:.8rem;font-weight:600;font-family:inherit;cursor:pointer;border:none;background:none;color:var(--text2);transition:background .12s,color .12s;text-align:center;display:flex;flex-direction:column;align-items:center;gap:.18rem;position:relative}}
    .cfg-tab:hover{{background:var(--surface2);color:var(--text)}}
    .cfg-tab.active{{background:var(--primary);color:#fff}}
    .cfg-tab-icon{{opacity:.65;flex-shrink:0;transition:opacity .12s}}
    .cfg-tab.active .cfg-tab-icon,.cfg-tab:hover .cfg-tab-icon{{opacity:1}}
    .cfg-tab-label{{font-size:.67rem;white-space:nowrap;letter-spacing:.02em;line-height:1}}
    .cfg-dirty-dot{{position:absolute;top:.27rem;right:.27rem;width:7px;height:7px;border-radius:50%;background:#f59e0b;display:none;box-shadow:0 0 0 2px var(--surface)}}
    .cfg-tab.has-dirty .cfg-dirty-dot{{display:block}}
    .cfg-pane{{display:none}}
    .cfg-pane.active{{display:block}}
    /* Save button spinner */
    .btn-spinner{{display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:btn-spin .65s linear infinite;vertical-align:middle;margin-right:.3rem}}
    @keyframes btn-spin{{to{{transform:rotate(360deg)}}}}
    /* Slot duration card (Horarios tab) */
    .bh-slot-card{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:.9rem 1rem;margin-bottom:.85rem;display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
    .bh-slot-group{{display:flex;flex-direction:column;gap:.3rem}}
    .bh-slot-label{{font-size:.7rem;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.06em}}
    .bh-slot-select{{border:1px solid var(--border);border-radius:var(--radius-sm);padding:.42rem .7rem;font-size:.84rem;font-family:inherit;background:var(--surface);color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s;width:100%}}
    .bh-slot-select:focus{{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow)}}
    .bh-slot-hint{{font-size:.71rem;color:var(--muted);line-height:1.5}}
    /* NOTIFICATION TEMPLATES */
    .notif-info-bar{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:.7rem 1rem;margin-bottom:1rem;font-size:.78rem;color:var(--text2);line-height:1.7;display:flex;align-items:flex-start;gap:.6rem}}
    .notif-info-bar svg{{flex-shrink:0;margin-top:.1rem;color:var(--primary)}}
    .notif-tpl-list{{display:flex;flex-direction:column;gap:.85rem;padding:1.25rem 1.5rem 1.5rem}}
    .notif-tpl-card{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);overflow:hidden;transition:box-shadow .15s}}
    .notif-tpl-card:focus-within{{box-shadow:0 0 0 2px var(--primary-glow);border-color:var(--primary)}}
    .notif-tpl-hdr{{display:flex;align-items:flex-start;gap:.7rem;padding:.72rem 1rem;border-bottom:1px solid var(--border);background:var(--surface)}}
    .notif-tpl-badge{{width:30px;height:30px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.95rem;flex-shrink:0}}
    .notif-tpl-info{{flex:1;min-width:0}}
    .notif-tpl-title{{font-size:.83rem;font-weight:700;color:var(--text);margin-bottom:.12rem}}
    .notif-tpl-desc{{font-size:.73rem;color:var(--muted);line-height:1.5}}
    .notif-tpl-body{{padding:.7rem 1rem .85rem}}
    .notif-var-row{{display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;margin-bottom:.55rem}}
    .notif-var-lbl{{font-size:.68rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}}
    .notif-var-chip{{font-size:.73rem;font-weight:600;font-family:monospace;padding:.16rem .52rem;border-radius:4px;background:var(--bg);border:1px solid var(--border2);color:var(--primary);cursor:pointer;transition:background .1s,border-color .1s,transform .08s;user-select:none;line-height:1.6}}
    .notif-var-chip:hover{{background:var(--primary-glow);border-color:var(--primary);transform:translateY(-1px)}}
    .notif-var-chip:active{{transform:translateY(0)}}
    .notif-ta{{width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);padding:.5rem .75rem;font-size:.84rem;font-family:inherit;background:var(--surface);color:var(--text);outline:none;resize:vertical;line-height:1.6;transition:border-color .15s,box-shadow .15s}}
    .notif-ta:focus{{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow)}}
    .notif-char-count{{font-size:.68rem;color:var(--muted);text-align:right;margin-top:.25rem}}
    .notif-char-count.warn{{color:#d97706}}
    .notif-char-count.over{{color:#dc2626;font-weight:600}}
    /* SYSTEM STATUS PAGE */
    .status-hdr-row{{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem}}
    .status-hdr-controls{{display:flex;align-items:center;gap:.65rem}}
    .status-live-indicator{{display:flex;align-items:center;gap:.35rem;font-size:.7rem;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:.06em}}
    .status-live-dot{{width:7px;height:7px;border-radius:50%;background:#059669;animation:live-pulse 2s ease-in-out infinite;flex-shrink:0}}
    @keyframes live-pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.35;transform:scale(.65)}}}}
    .status-grid{{padding:0}}
    .status-row{{display:flex;align-items:center;gap:.85rem;padding:.82rem 1.25rem;border-bottom:1px solid var(--border);border-left:3px solid transparent;transition:border-color .2s,background .15s}}
    .status-row:last-child{{border-bottom:none}}
    .status-row:hover{{background:var(--surface2)}}
    .status-row.ok{{border-left-color:#059669}}
    .status-row.warn{{border-left-color:#d97706}}
    .status-row.error{{border-left-color:#dc2626}}
    .status-row.loading{{border-left-color:var(--border2)}}
    .status-row-icon{{flex-shrink:0;display:flex;align-items:center;opacity:.75}}
    .status-row.ok .status-row-icon{{color:#059669;opacity:1}}
    .status-row.warn .status-row-icon{{color:#d97706;opacity:1}}
    .status-row.error .status-row-icon{{color:#dc2626;opacity:1}}
    .status-row-name{{font-size:.84rem;font-weight:700;color:var(--text);min-width:190px;flex-shrink:0}}
    .status-row-detail{{flex:1;font-size:.81rem;color:var(--text2);line-height:1.4}}
    .status-row-right{{display:flex;align-items:center;gap:.45rem;flex-shrink:0}}
    .status-latency{{font-size:.69rem;font-weight:600;color:var(--muted);font-family:monospace;background:var(--surface2);padding:.1rem .38rem;border-radius:4px;border:1px solid var(--border);white-space:nowrap}}
    .status-badge{{display:inline-flex;align-items:center;padding:.17rem .6rem;border-radius:999px;font-size:.68rem;font-weight:700;white-space:nowrap}}
    .status-badge.ok{{background:#d1fae5;color:#065f46}}
    .status-badge.warn{{background:#fef3c7;color:#92400e}}
    .status-badge.error{{background:#fee2e2;color:#991b1b}}
    .status-badge.loading,.status-badge.unknown{{background:var(--surface2);color:var(--muted)}}
    [data-theme="dark"] .status-badge.ok{{background:#052e16;color:#6ee7b7}}
    [data-theme="dark"] .status-badge.warn{{background:#422006;color:#fde68a}}
    [data-theme="dark"] .status-badge.error{{background:#450a0a;color:#fca5a5}}
    .status-footer{{padding:.65rem 1.25rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem;border-top:1px solid var(--border);background:var(--surface2);font-size:.73rem;color:var(--muted)}}
    .status-row-skeleton{{height:52px;background:linear-gradient(90deg,var(--surface2) 25%,var(--border) 50%,var(--surface2) 75%);background-size:200% 100%;animation:shimmer 1.4s infinite;border-bottom:1px solid var(--border)}}
    @keyframes shimmer{{0%{{background-position:200% 0}}100%{{background-position:-200% 0}}}}
    /* BOT CONFIG FORM */
    .bcf-form{{display:flex;flex-direction:column;gap:.85rem;padding:1.25rem 1.5rem}}
    .bcf-label{{font-size:.72rem;font-weight:600;color:var(--text2);margin-bottom:.3rem;display:block;text-transform:uppercase;letter-spacing:.05em}}
    .bcf-input,.bcf-textarea,.bcf-select{{width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);padding:.45rem .75rem;font-size:.84rem;font-family:inherit;background:var(--surface2);color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s}}
    .bcf-input:focus,.bcf-textarea:focus,.bcf-select:focus{{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow)}}
    .bcf-textarea{{resize:vertical;line-height:1.6}}
    .bcf-hint{{font-size:.74rem;color:var(--muted);margin-top:.2rem;line-height:1.6}}
    .bcf-row{{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}}
    .bcf-group{{display:flex;flex-direction:column}}
    .faq-ex-box{{background:var(--surface2);border:1px dashed var(--border2);border-radius:var(--radius-sm);padding:.75rem 1rem;font-size:.8rem;color:var(--muted);margin-top:.75rem;line-height:2}}

    /* MODALS */
    #modal-new,#modal-edit,#modal-complete{{display:none;position:fixed;z-index:1000;width:460px;max-width:92vw;background:var(--surface);color:var(--text);border-radius:var(--radius);box-shadow:var(--shadow-lg);border:1px solid var(--border)}}
    .modal-drag-handle{{padding:.9rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;cursor:grab;user-select:none;border-radius:var(--radius) var(--radius) 0 0;background:var(--surface2)}}
    .modal-drag-handle:active{{cursor:grabbing}}
    .modal-drag-hint{{font-size:.68rem;color:var(--muted);display:flex;align-items:center;gap:.3rem}}
    .modal-body{{padding:1.25rem 1.5rem 1.5rem}}
    .modal-title{{font-size:1rem;font-weight:700}}
    .form-group{{margin-bottom:.9rem}}
    .form-group label{{display:block;font-size:.72rem;font-weight:600;color:var(--text2);margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.05em}}
    .form-group input{{width:100%;padding:.52rem .8rem;border:1px solid var(--border2);border-radius:var(--radius-sm);font-size:.9rem;font-family:inherit;background:var(--surface);color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s}}
    .form-group input::placeholder{{color:var(--muted)}}
    .form-group input:focus{{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow)}}
    .form-row{{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}}
    .modal-footer{{display:flex;justify-content:flex-end;gap:.5rem;padding-top:1rem;border-top:1px solid var(--border);margin-top:1.1rem}}
    .btn-secondary{{padding:.48rem 1rem;border-radius:var(--radius-sm);font-size:.84rem;font-weight:600;font-family:inherit;cursor:pointer;border:1px solid var(--border2);background:var(--surface);color:var(--text2);transition:background .12s}}
    .btn-secondary:hover{{background:var(--bg)}}
    .btn-primary{{padding:.48rem 1.1rem;border-radius:var(--radius-sm);font-size:.84rem;font-weight:600;font-family:inherit;cursor:pointer;border:none;background:var(--primary);color:#fff;transition:opacity .12s,transform .1s}}
    .btn-primary:hover{{opacity:.88;transform:translateY(-1px)}}
    .btn-primary:active{{transform:translateY(0)}}
    .btn-primary:disabled{{opacity:.5;cursor:not-allowed;transform:none}}
    .confirm-overlay{{display:none;position:fixed;inset:0;z-index:2000;align-items:center;justify-content:center}}
    .confirm-overlay.open{{display:flex}}
    .confirm-backdrop{{position:absolute;inset:0;background:rgba(0,0,0,.5);backdrop-filter:blur(3px)}}
    .confirm-box{{position:relative;z-index:1;background:var(--surface);border-radius:var(--radius);padding:1.75rem;max-width:400px;width:90%;box-shadow:var(--shadow-lg);border:1px solid var(--border)}}
    .confirm-icon{{width:44px;height:44px;border-radius:10px;background:#fef2f2;display:flex;align-items:center;justify-content:center;color:#dc2626;margin-bottom:1rem}}
    [data-theme="dark"] .confirm-icon{{background:#450a0a}}
    .confirm-title{{font-size:1rem;font-weight:700;margin-bottom:.4rem}}
    .confirm-msg{{font-size:.86rem;color:var(--text2);line-height:1.6;margin-bottom:1.5rem}}
    .toast{{position:fixed;bottom:1.5rem;right:1.5rem;padding:.7rem 1.1rem;border-radius:10px;font-size:.84rem;font-weight:500;font-family:inherit;box-shadow:var(--shadow-lg);z-index:3000;animation:slide-in .22s cubic-bezier(.16,1,.3,1);display:flex;align-items:center;gap:.5rem;max-width:320px}}
    .toast-ok{{background:#065f46;color:#ecfdf5}}.toast-err{{background:#991b1b;color:#fef2f2}}
    @keyframes slide-in{{from{{transform:translateX(110%);opacity:0}}to{{transform:translateX(0);opacity:1}}}}

    /* RESPONSIVE */
    @media(max-width:1100px){{.tab-nav{{grid-template-columns:repeat(3,1fr)}}}}
    @media(max-width:900px){{
      .layout{{flex-direction:column}}.layout-left{{padding-right:0;margin-bottom:1rem}}
      .layout-right{{width:100%!important;min-width:0;position:static}}.resize-handle{{display:none}}
      .dash-row{{grid-template-columns:1fr}}
    }}
    @media(max-width:768px){{
      .page{{padding:1rem}}.tab-nav{{grid-template-columns:repeat(3,1fr)}}
      .metrics-grid{{grid-template-columns:repeat(2,1fr)}}
    }}
    @media(max-width:480px){{
      .tab-nav{{grid-template-columns:repeat(2,1fr)}}.metrics-grid{{grid-template-columns:repeat(2,1fr)}}
    }}

    /* ── CLIENTES PAGE ──────────────────────────────────────────────────── */
    .return-badge{{display:inline-flex;align-items:center;gap:.28rem;padding:.22rem .65rem;border-radius:999px;font-size:.72rem;font-weight:600;white-space:nowrap;letter-spacing:.02em}}
    .return-ok{{background:#d1fae5;color:#065f46;border:1px solid #a7f3d0}}
    .return-upcoming{{background:#fef9c3;color:#854d0e;border:1px solid #fde68a}}
    .return-overdue{{background:#fee2e2;color:#991b1b;border:1px solid #fecaca;animation:pulse-red 2s infinite}}
    .return-none{{background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0}}
    [data-theme="dark"] .return-ok{{background:#052e16;color:#6ee7b7;border-color:#065f46}}
    [data-theme="dark"] .return-upcoming{{background:#2a1c00;color:#fbbf24;border-color:#78350f}}
    [data-theme="dark"] .return-overdue{{background:#450a0a;color:#fca5a5;border-color:#7f1d1d}}
    [data-theme="dark"] .return-none{{background:#1e293b;color:#64748b;border-color:#334155}}
    @keyframes pulse-red{{0%,100%{{box-shadow:none}}50%{{box-shadow:0 0 0 3px rgba(220,38,38,.18)}}}}
    .notes-cell{{max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.82rem;color:var(--text2);cursor:default}}
    .client-phone-link{{color:var(--primary);text-decoration:none;font-family:'SF Mono','Fira Code',monospace;font-size:.8rem}}
    .client-phone-link:hover{{text-decoration:underline}}
    .notify-btn{{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}}
    .delete-btn{{background:#fef2f2;color:#b91c1c;border-color:#fecaca}}
    [data-theme="dark"] .notify-btn{{background:#052e16;color:#6ee7b7;border-color:#065f46}}
    [data-theme="dark"] .delete-btn{{background:#450a0a;color:#fca5a5;border-color:#7f1d1d}}
    .clients-empty{{display:flex;flex-direction:column;align-items:center;gap:.75rem;padding:3rem 1rem;text-align:center;color:var(--muted)}}
    .clients-empty-icon{{font-size:2.5rem}}
    .clients-filters{{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}}
    .filter-chip{{padding:.3rem .75rem;border-radius:999px;font-size:.75rem;font-weight:600;font-family:inherit;cursor:pointer;border:1px solid var(--border2);background:var(--surface);color:var(--text2);transition:background .12s,color .12s}}
    .filter-chip.active{{background:var(--primary);color:#fff;border-color:transparent}}
    .filter-chip:hover:not(.active){{background:var(--surface2)}}
    /* Client modal textarea */
    .client-notes-ta{{width:100%;padding:.52rem .8rem;border:1px solid var(--border2);border-radius:var(--radius-sm);font-size:.84rem;font-family:inherit;background:var(--surface);color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s;resize:vertical;line-height:1.6;min-height:72px}}
    .client-notes-ta:focus{{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow)}}
    .client-notes-ta::placeholder{{color:var(--muted)}}
    .return-parse-hint{{display:none;font-size:.72rem;color:#059669;margin-top:.3rem;font-weight:500}}
    /* Sortable headers */
    .sortable-th{{cursor:pointer;user-select:none;transition:color .12s}}
    .sortable-th:hover{{color:var(--primary)}}
    .sort-icon{{display:inline-block;margin-left:.3rem;font-size:.65rem;opacity:.3;vertical-align:middle;transition:opacity .12s,color .12s}}
    .sort-asc .sort-icon,.sort-desc .sort-icon{{opacity:1;color:var(--primary)}}
    /* Visit badge */
    .visit-badge{{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;border-radius:999px;font-size:.72rem;font-weight:700;background:var(--surface2);border:1px solid var(--border);color:var(--text2)}}
    .visit-badge.has-visits{{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8}}
    [data-theme="dark"] .visit-badge.has-visits{{background:#1e3a5f;border-color:#1e40af;color:#93c5fd}}
    /* Export btn */
    .btn-export{{padding:.44rem 1rem;border-radius:var(--radius-sm);font-size:.82rem;font-weight:600;font-family:inherit;cursor:pointer;border:1px solid var(--border2);background:var(--surface2);color:var(--text2);white-space:nowrap;display:flex;align-items:center;gap:.35rem;transition:background .12s,color .12s}}
    .btn-export:hover{{background:var(--border);color:var(--text)}}

    /* ── CHAT CLIENTE ───────────────────────────────────────────────────────── */
    #page-chat.active{{display:flex;flex-direction:column;padding:0;max-width:none;height:calc(100vh - 56px);overflow:hidden}}
    .chat-layout{{display:flex;height:100%;min-height:0}}

    /* Painel de contatos */
    .chat-contacts-panel{{width:330px;flex-shrink:0;border-right:1px solid var(--border);display:flex;flex-direction:column;background:var(--surface);overflow:hidden}}
    .chat-contacts-hdr{{padding:.85rem 1rem;border-bottom:1px solid var(--border);background:var(--surface2);flex-shrink:0}}
    .chat-contacts-title{{font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:.55rem;display:flex;align-items:center;gap:.4rem}}
    .chat-search{{width:100%;padding:.42rem .85rem;border:1px solid var(--border2);border-radius:999px;font-size:.82rem;font-family:inherit;background:var(--bg);color:var(--text);outline:none;transition:border-color .15s;box-sizing:border-box}}
    .chat-search:focus{{border-color:#25D366}}
    .chat-search::placeholder{{color:var(--muted)}}
    .chat-filter-row{{display:flex;gap:.3rem;margin-top:.5rem}}
    .chat-filter-btn{{flex:1;padding:.28rem .3rem;border-radius:999px;font-size:.7rem;font-weight:600;font-family:inherit;cursor:pointer;border:1px solid var(--border2);background:var(--surface);color:var(--text2);transition:background .12s,color .12s;white-space:nowrap}}
    .chat-filter-btn.active{{background:#25D366;color:#fff;border-color:transparent}}
    .chat-filter-btn:hover:not(.active){{background:var(--surface2)}}
    .chat-contact-list{{flex:1;overflow-y:auto}}
    .chat-contact-item{{display:flex;align-items:center;gap:.65rem;padding:.75rem .9rem;border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s}}
    .chat-contact-item:hover{{background:var(--surface2)}}
    .chat-contact-item.active{{background:#e7f8ec}}
    [data-theme="dark"] .chat-contact-item.active{{background:#0d2b14}}
    .chat-avatar{{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.88rem;font-weight:700;color:#fff;flex-shrink:0;letter-spacing:-.01em}}
    .chat-contact-info{{flex:1;min-width:0}}
    .chat-contact-name{{font-size:.84rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;gap:.3rem}}
    .chat-contact-preview{{font-size:.75rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}}
    .chat-contact-meta{{display:flex;flex-direction:column;align-items:flex-end;gap:.22rem;flex-shrink:0}}
    .chat-contact-time{{font-size:.67rem;color:var(--muted);white-space:nowrap}}
    .chat-unread-badge{{background:#25D366;color:#fff;font-size:.6rem;font-weight:700;padding:.1rem .4rem;border-radius:999px;min-width:17px;text-align:center;line-height:1.5}}
    .chat-empty-contacts{{padding:2.5rem 1rem;text-align:center;color:var(--muted);font-size:.82rem}}

    /* Painel de conversa */
    .chat-conv-panel{{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}}
    #chat-active-conv{{flex:1;display:flex;flex-direction:column;overflow:hidden;min-height:0}}
    .chat-conv-header{{height:60px;padding:0 1.25rem;display:flex;align-items:center;gap:.75rem;border-bottom:1px solid var(--border);background:var(--surface2);flex-shrink:0}}
    .chat-conv-info{{flex:1;min-width:0}}
    .chat-conv-name{{font-size:.9rem;font-weight:700;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .chat-conv-phone{{font-size:.72rem;color:var(--muted);font-family:'SF Mono','Fira Code',monospace}}
    .chat-ia-control{{display:flex;align-items:center;gap:.5rem;flex-shrink:0}}
    .chat-ia-badge{{display:inline-flex;align-items:center;gap:.32rem;padding:.22rem .62rem;border-radius:999px;font-size:.72rem;font-weight:700}}
    .chat-ia-on{{background:#d1fae5;color:#065f46;border:1px solid #a7f3d0}}
    .chat-ia-off{{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}}
    [data-theme="dark"] .chat-ia-on{{background:#052e16;color:#6ee7b7;border-color:#065f46}}
    [data-theme="dark"] .chat-ia-off{{background:#450a0a;color:#fca5a5;border-color:#7f1d1d}}
    .chat-ia-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
    .chat-ia-on .chat-ia-dot{{background:#22c55e}}
    .chat-ia-off .chat-ia-dot{{background:#ef4444}}
    .btn-ia-toggle{{padding:.3rem .75rem;border-radius:6px;font-size:.74rem;font-weight:600;font-family:inherit;cursor:pointer;border:none;transition:background .12s,color .12s;white-space:nowrap}}
    .btn-ia-toggle.pause{{background:#fef9c3;color:#854d0e}}
    .btn-ia-toggle.pause:hover{{background:#fde68a}}
    .btn-ia-toggle.resume{{background:#d1fae5;color:#065f46}}
    .btn-ia-toggle.resume:hover{{background:#a7f3d0}}
    [data-theme="dark"] .btn-ia-toggle.pause{{background:#2a1c00;color:#fbbf24}}
    [data-theme="dark"] .btn-ia-toggle.resume{{background:#052e16;color:#6ee7b7}}

    /* Área de mensagens */
    .chat-messages{{flex:1;overflow-y:auto;padding:.75rem 1rem;background:#e5ddd5;display:flex;flex-direction:column;gap:.25rem;min-height:0}}
    [data-theme="dark"] .chat-messages{{background:#0b141a}}
    .chat-date-sep{{text-align:center;font-size:.7rem;color:var(--muted);background:rgba(255,255,255,.75);padding:.18rem .65rem;border-radius:999px;align-self:center;margin:.4rem 0;backdrop-filter:blur(4px);box-shadow:0 1px 3px rgba(0,0,0,.08)}}
    [data-theme="dark"] .chat-date-sep{{background:rgba(30,41,59,.85);color:#94a3b8}}
    .chat-bubble{{max-width:72%;padding:.48rem .7rem .32rem;border-radius:8px;font-size:.865rem;line-height:1.45;position:relative;word-wrap:break-word;white-space:pre-wrap}}
    .chat-bubble.received{{background:#fff;align-self:flex-start;border-radius:0 8px 8px 8px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
    .chat-bubble.sent{{background:#dcf8c6;align-self:flex-end;border-radius:8px 0 8px 8px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
    .chat-bubble.operator{{background:#d0ebff;align-self:flex-end;border-radius:8px 0 8px 8px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
    [data-theme="dark"] .chat-bubble.received{{background:#202c33;color:#e9edef}}
    [data-theme="dark"] .chat-bubble.sent{{background:#005c4b;color:#e9edef}}
    [data-theme="dark"] .chat-bubble.operator{{background:#1c3045;color:#e9edef}}
    .chat-bubble-meta{{display:flex;align-items:center;justify-content:flex-end;gap:.22rem;margin-top:.2rem}}
    .chat-bubble-time{{font-size:.64rem;color:rgba(0,0,0,.38)}}
    [data-theme="dark"] .chat-bubble-time{{color:rgba(255,255,255,.35)}}
    .chat-tick{{font-size:.7rem;color:#53bdeb}}
    .chat-sub-label{{font-size:.64rem;font-style:italic;color:var(--muted);align-self:flex-end;margin-bottom:.12rem;opacity:.8}}
    .chat-sub-label.op{{color:#1d4ed8}}
    [data-theme="dark"] .chat-sub-label.op{{color:#93c5fd}}

    /* Banner IA pausada */
    .chat-ia-warning-bar{{padding:.42rem 1rem;background:#fef9c3;color:#854d0e;font-size:.77rem;font-weight:500;border-top:1px solid #fde68a;display:flex;align-items:center;gap:.45rem;flex-shrink:0}}
    [data-theme="dark"] .chat-ia-warning-bar{{background:#2a1c00;color:#fbbf24;border-color:#78350f}}

    /* Barra de input */
    .chat-input-bar{{padding:.65rem .9rem;background:var(--surface);border-top:1px solid var(--border);display:flex;align-items:flex-end;gap:.6rem;flex-shrink:0}}
    .chat-textarea{{flex:1;padding:.52rem .85rem;border:1px solid var(--border2);border-radius:20px;font-size:.875rem;font-family:inherit;background:var(--bg);color:var(--text);outline:none;resize:none;line-height:1.45;max-height:130px;overflow-y:auto;transition:border-color .15s;box-sizing:border-box}}
    .chat-textarea:focus{{border-color:#25D366;box-shadow:0 0 0 3px rgba(37,211,102,.12)}}
    .chat-textarea::placeholder{{color:var(--muted)}}
    .chat-send-btn{{width:41px;height:41px;border-radius:50%;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s,transform .1s;background:#25D366;color:#fff}}
    .chat-send-btn:hover{{opacity:.88;transform:scale(1.06)}}
    .chat-send-btn:active{{transform:scale(.95)}}
    .chat-send-btn:disabled{{opacity:.4;cursor:not-allowed;transform:none}}

    /* Empty state conversa */
    .chat-conv-empty{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted);gap:.65rem;text-align:center;background:#e5ddd5}}
    [data-theme="dark"] .chat-conv-empty{{background:#0b141a}}
    .chat-conv-empty-icon{{font-size:3rem;opacity:.35}}
    .chat-conv-empty p{{font-size:.88rem;max-width:200px;line-height:1.55;opacity:.7}}

    @media(max-width:768px){{
      .chat-contacts-panel{{width:100%}}
      .chat-layout.conv-open .chat-contacts-panel{{display:none}}
      .chat-layout.conv-open .chat-conv-panel{{display:flex}}
    }}
  </style>
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
        <button class="btn-new" onclick="navTo('agendamentos');setTimeout(openModal,80)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Novo agendamento
        </button>
      </div>

      <div class="metrics-grid">
        <div class="metric-card mc-blue"><div class="metric-num">{hoje_dia_count}</div><div class="metric-lbl">Atendimentos Hoje</div></div>
        <div class="metric-card mc-green"><div class="metric-num">{confirmados_tab}</div><div class="metric-lbl">Confirmados</div></div>
        <div class="metric-card mc-red"><div class="metric-num">{cancelados_tab}</div><div class="metric-lbl">Cancelados</div></div>
        <div class="metric-card mc-cyan"><div class="metric-num">{concluidos_tab}</div><div class="metric-lbl">Concluidos</div></div>
        <div class="metric-card mc-amber"><div class="metric-num">{pendente_tab}</div><div class="metric-lbl">Pendencias</div></div>
        <div class="metric-card mc-purple"><div class="metric-num">{taxa_comp}%</div><div class="metric-lbl">Taxa Comparecimento</div></div>
      </div>

      <div class="dash-row">
        <div class="dash-card">
          <div class="dash-card-hdr">Agendamentos — ultimos 7 dias</div>
          <div class="dash-card-body"><div class="bar-chart">{chart_bars}</div></div>
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
            <div class="chat-contacts-title">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#25D366" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              Conversas WhatsApp
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
              <div class="chat-ia-control">
                <div class="chat-ia-badge chat-ia-on" id="conv-ia-badge">
                  <div class="chat-ia-dot"></div>
                  <span id="conv-ia-label">IA ativa</span>
                </div>
                <button class="btn-ia-toggle pause" id="btn-ia-toggle" onclick="toggleChatIA()">Pausar IA</button>
              </div>
            </div>

            <!-- Area de mensagens -->
            <div class="chat-messages" id="chat-messages-area"></div>

            <!-- Banner: IA pausada -->
            <div id="chat-ia-warning-bar" class="chat-ia-warning-bar" style="display:none">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              IA pausada &mdash; voce esta respondendo manualmente para este contato
            </div>

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
        <button class="cfg-tab" data-tab="status" onclick="switchCfgTab('status')">
          <span class="cfg-dirty-dot"></span>
          <svg class="cfg-tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          <span class="cfg-tab-label">Status</span>
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

            <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
              <button class="btn-primary" onclick="saveNotifTemplates(this)">Salvar templates</button>
              <button style="font-size:.78rem;padding:.38rem .85rem;border-radius:var(--radius-sm);border:1px solid var(--border2);background:var(--surface);cursor:pointer;color:var(--text2);font-family:inherit;transition:background .12s" onclick="resetNotifTemplates()">&#8635; Restaurar textos padrao</button>
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
                  <div class="rp-item"><label>Resultados (top_k)</label><input type="number" id="rag-top-k" class="rp-input" min="1" max="20" value="3"></div>
                  <div class="rp-item"><label>Sim. minima (0-1)</label><input type="number" id="rag-min-sim" class="rp-input" min="0" max="1" step="0.05" value="0.75"></div>
                  <div class="rp-item"><label>Tokens contexto</label><input type="number" id="rag-max-ctx" class="rp-input" min="100" max="3000" value="800"></div>
                  <div class="rp-item"><label>Tamanho chunk</label><input type="number" id="rag-chunk-size" class="rp-input" min="50" max="1000" value="400"></div>
                  <div class="rp-item"><label>Sobreposicao</label><input type="number" id="rag-chunk-overlap" class="rp-input" min="0" max="200" value="80"></div>
                </div>
                <button class="btn-primary" style="width:fit-content" onclick="saveRagConfig(this)">Salvar parametros</button>
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

      <!-- PANE: Status do Sistema -->
      <div id="cfg-pane-status" class="cfg-pane">
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
  const PENDING_ITEMS = {pending_json};
  function authHeaders() {{ return {{"Content-Type":"application/json","X-Admin-Token":ADMIN_TOKEN}}; }}

  /* Navigation */
  const PAGE_TITLES = {{dashboard:"Dashboard",agendamentos:"Agendamentos",ia:"Fale com a Liza",clientes:"Clientes",chat:"Chat Cliente",config:"Configuracoes"}};
  function navTo(page) {{
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    const pe = document.getElementById("page-"+page);
    const ne = document.querySelector('.nav-item[data-page="'+page+'"]');
    if (pe) pe.classList.add("active");
    if (ne) ne.classList.add("active");
    document.getElementById("header-title").textContent = PAGE_TITLES[page]||page;
    localStorage.setItem("lastPage", page);
    isPaused = false;
    secs = 30;
    if (page === "config") loadConfigPage();
    if (page === "clientes") loadClients();
    if (page === "chat") {{ loadChatContacts(); startChatPoll(); }} else {{ stopChatPoll(); }}
    // Ajusta overflow do main para o chat (layout fixo)
    const mainEl = document.querySelector("main");
    if (mainEl) mainEl.style.overflow = page === "chat" ? "hidden" : "";
  }}
  function toggleSidebar() {{
    const sb = document.getElementById("sidebar");
    sb.classList.toggle("collapsed");
    localStorage.setItem("sbCollapsed", sb.classList.contains("collapsed") ? "1" : "0");
  }}

  /* Dashboard widgets */
  function renderStatusBreakdown() {{
    const data = [
      {{label:"Confirmado",count:{confirmados_tab},color:"#059669"}},
      {{label:"Cancelado", count:{cancelados_tab}, color:"#dc2626"}},
      {{label:"Concluido", count:{concluidos_tab}, color:"#0891b2"}},
      {{label:"Hoje",      count:{hoje_dia_count}, color:"#2563eb"}},
      {{label:"Pendente",  count:{pendente_tab},   color:"#d97706"}},
    ];
    const mx = Math.max(...data.map(d=>d.count),1);
    const el = document.getElementById("status-breakdown");
    if (!el) return;
    el.innerHTML = data.map(d => {{
      const pct = Math.round(d.count/mx*100);
      return '<div class="status-row"><span class="sr-label">'+d.label+'</span><div class="sr-bar"><div class="sr-fill" style="width:'+pct+'%;background:'+d.color+'"></div></div><span class="sr-count">'+d.count+'</span></div>';
    }}).join("");
  }}
  function renderUpcoming() {{
    const SC = {{scheduled:"#d97706",day_reminder_sent:"#2563eb",reminder_sent:"#7c3aed",response_received:"#7c3aed",confirmed:"#059669",attended:"#0f766e"}};
    const rows = Array.from(document.querySelectorAll("#tbody tr[data-status]"))
      .filter(r => !["cancelled","no_show","completed"].includes(r.dataset.status))
      .sort((a,b) => (a.dataset.date+a.dataset.time).localeCompare(b.dataset.date+b.dataset.time))
      .slice(0,6);
    const el = document.getElementById("upcoming-list");
    if (!el) return;
    if (!rows.length) {{
      el.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--muted);font-size:.84rem;">Nenhum agendamento pendente.</div>';
      return;
    }}
    el.innerHTML = rows.map(r => {{
      const color = SC[r.dataset.status]||"#94a3b8";
      const name  = r.querySelector(".client-name")?.textContent||"—";
      const phone = r.querySelector(".phone-num")?.textContent||"—";
      const badge = r.querySelector(".badge")?.textContent||"";
      const dp = r.dataset.date?r.dataset.date.split("-"):[];
      const ds = dp.length===3?dp[2]+"/"+dp[1]+"/"+dp[0]:r.dataset.date;
      return '<div class="activity-item"><div class="act-dot" style="background:'+color+'"></div><div class="act-info"><div class="act-name">'+name+'</div><div class="act-detail">'+phone+' &middot; '+badge+'</div></div><div class="act-time">'+ds+' '+r.dataset.time+'</div></div>';
    }}).join("");
  }}

  /* Toast */
  function showToast(msg, ok=true) {{
    const t = document.createElement("div");
    t.className = "toast "+(ok?"toast-ok":"toast-err");
    t.innerHTML = (ok?'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>':'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>')+msg;
    document.body.appendChild(t);
    setTimeout(()=>t.remove(),3200);
  }}

  /* Confirm cancel */
  let _pendingCancelBtn=null;
  function openConfirmCancel(btn){{_pendingCancelBtn=btn;document.getElementById("modal-confirm").classList.add("open");isPaused=true;document.getElementById("cd").textContent="Pausado";}}
  function closeConfirmModal(){{document.getElementById("modal-confirm").classList.remove("open");_pendingCancelBtn=null;isPaused=false;secs=30;}}
  async function confirmDoCancel(){{
    const btn=_pendingCancelBtn;closeConfirmModal();if(!btn)return;
    const row=btn.closest("tr");btn.disabled=true;
    const res=await fetch("/admin/cancel",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time}})}});
    if(res.ok){{
      row.dataset.status="cancelled";
      row.querySelector(".badge").className="badge cancelled";row.querySelector(".badge").textContent="Cancelado";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn recover-btn" onclick="recoverApt(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar</button><button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>';
      row.classList.remove("row-today");showToast("Agendamento cancelado.");applyFilter();
    }} else {{btn.disabled=false;showToast("Erro ao cancelar.",false);}}
  }}

  /* Recover */
  async function recoverApt(btn){{
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Recuperando...";
    const res=await fetch("/admin/recover",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time}})}});
    if(res.ok){{
      row.dataset.status="scheduled";row.querySelector(".badge").className="badge scheduled";row.querySelector(".badge").textContent="Aguardando";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn remind-btn" onclick="sendRemind(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button><button class="action-btn edit-btn" onclick="openEditModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button><button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>';
      showToast("Agendamento recuperado!");applyFilter();
    }} else {{btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar';showToast("Erro ao recuperar.",false);}}
  }}

  /* Edit modal */
  function openEditModal(btn){{
    const row=btn.closest("tr");
    document.getElementById("edit-name").value=row.dataset.name;
    document.getElementById("edit-phone").value=row.dataset.phone.replace("@s.whatsapp.net","").replace("@lid","");
    document.getElementById("edit-date").value=row.dataset.date;
    document.getElementById("edit-time").value=row.dataset.time;
    const m=document.getElementById("modal-edit");
    m.dataset.oldPhone=row.dataset.phone;m.dataset.oldDate=row.dataset.date;m.dataset.oldTime=row.dataset.time;m._rowRef=row;
    m.style.display="block";
    if(!m._positioned){{m.style.left=Math.max(0,(window.innerWidth-m.offsetWidth)/2)+"px";m.style.top=Math.max(0,(window.innerHeight-m.offsetHeight)/2)+"px";m._positioned=true;}}
    isPaused=true;document.getElementById("cd").textContent="Pausado";
  }}
  function closeEditModal(){{document.getElementById("modal-edit").style.display="none";isPaused=false;secs=30;}}
  async function submitEdit(e){{
    e.preventDefault();const btn=document.getElementById("btn-submit-edit");btn.disabled=true;btn.textContent="Salvando...";
    const m=document.getElementById("modal-edit");
    const res=await fetch("/admin/edit",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{old_phone:m.dataset.oldPhone,old_date:m.dataset.oldDate,old_time:m.dataset.oldTime,name:document.getElementById("edit-name").value.trim(),phone:document.getElementById("edit-phone").value.trim(),date:document.getElementById("edit-date").value,time:document.getElementById("edit-time").value}})}});
    if(res.ok){{closeEditModal();showToast("Agendamento atualizado!");setTimeout(()=>location.reload(),1200);}}
    else{{btn.disabled=false;btn.textContent="Salvar alteracoes";showToast("Erro ao atualizar.",false);}}
  }}

  /* Remind */
  async function sendRemind(btn){{
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Enviando...";
    const res=await fetch("/admin/remind",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time}})}});
    if(res.ok){{row.dataset.status="reminder_sent";row.querySelector(".badge").className="badge reminder_sent";row.querySelector(".badge").textContent="Lembrete 1h";btn.remove();showToast("Lembrete enviado!");}}
    else{{btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete';showToast("Erro ao enviar lembrete.",false);}}
  }}

  /* New appointment modal */
  function openModal(){{
    document.getElementById("form-new").reset();
    const m=document.getElementById("modal-new");m.style.display="block";
    if(!m._positioned){{m.style.left=Math.max(0,(window.innerWidth-m.offsetWidth)/2)+"px";m.style.top=Math.max(0,(window.innerHeight-m.offsetHeight)/2)+"px";m._positioned=true;}}
    isPaused=true;document.getElementById("cd").textContent="Pausado";
  }}
  function closeModal(){{document.getElementById("modal-new").style.display="none";isPaused=false;secs=30;}}
  async function submitNew(e){{
    e.preventDefault();const btn=document.getElementById("btn-submit-new");btn.disabled=true;btn.textContent="Salvando...";
    const res=await fetch("/admin/appointments",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{name:document.getElementById("new-name").value.trim(),phone:document.getElementById("new-phone").value.trim(),date:document.getElementById("new-date").value,time:document.getElementById("new-time").value}})}});
    if(res.ok){{closeModal();showToast("Agendamento criado!");setTimeout(()=>location.reload(),1200);}}
    else{{btn.disabled=false;btn.textContent="Confirmar agendamento";showToast("Erro ao criar agendamento.",false);}}
  }}

  /* Tabs & filter */
  const TODAY_STR = "{today}";
  const FILTERS = {{
    day:       row => row.dataset.date===TODAY_STR && !["cancelled","no_show","completed"].includes(row.dataset.status),
    confirmed: row => ["confirmed","attended"].includes(row.dataset.status),
    cancelled: row => ["cancelled","no_show"].includes(row.dataset.status),
    completed: row => row.dataset.status==="completed",
    all:       ()  => true,
  }};
  let cur="day";
  function setTab(el){{
    document.querySelectorAll(".tab-nav .tab").forEach(t=>t.classList.remove("active"));
    el.classList.add("active");cur=el.dataset.f;
    const ip=cur==="pending";
    document.getElementById("main-panel").style.display=ip?"none":"";
    document.getElementById("pending-section").style.display=ip?"":"none";
    if(ip)renderPending();else applyFilter();
  }}
  function applyFilter(){{
    if(cur==="pending")return;
    const q=document.getElementById("search").value.toLowerCase();
    const fn=FILTERS[cur]||(()=>true);
    document.querySelectorAll("#tbody tr[data-status]").forEach(row=>{{
      const ok=fn(row)&&(!q||row.textContent.toLowerCase().includes(q));
      row.style.display=ok?"":"none";
    }});
  }}

  /* Theme */
  const MOON='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  const SUN='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  function applyTheme(dark){{document.documentElement.setAttribute("data-theme",dark?"dark":"light");document.getElementById("theme-icon").innerHTML=dark?SUN:MOON;}}
  function toggleTheme(){{const dark=document.documentElement.getAttribute("data-theme")!=="dark";localStorage.setItem("theme",dark?"dark":"light");applyTheme(dark);}}
  applyTheme(localStorage.getItem("theme")==="dark");

  /* Auto-refresh */
  let secs=30,isPaused=true,lastActivity=0;
  const IDLE_MS=15000;
  ["mousemove","mousedown","keydown","scroll","touchstart"].forEach(ev=>document.addEventListener(ev,()=>{{lastActivity=Date.now();}},{{passive:true}}));
  function tick(){{document.getElementById("ts").textContent="Atualizado "+new Date().toLocaleTimeString("pt-BR",{{hour:"2-digit",minute:"2-digit"}});}}
  function countdown(){{
    if(isPaused)return;
    if((Date.now()-lastActivity)<IDLE_MS){{secs=30;document.getElementById("cd").textContent="Pausado";return;}}
    document.getElementById("cd").textContent=secs>0?"Atualiza em "+secs+"s":"Atualizando...";
    if(--secs<0)location.reload();
  }}
  tick();setInterval(countdown,1000);

  /* Mark attended */
  async function markAttended(btn){{
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Salvando...";
    const res=await fetch("/admin/attended",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time}})}});
    if(res.ok){{
      row.dataset.status="attended";row.querySelector(".badge").className="badge attended";row.querySelector(".badge").textContent="Compareceu";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn confirm-btn" onclick="openCompleteModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Concluir</button>';
      showToast("Comparecimento registrado!");applyFilter();
    }} else {{btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="23 11 20 14 18 12"/></svg> Compareceu';showToast("Erro.",false);}}
  }}

  /* Complete modal */
  let _completeRow=null;
  function openCompleteModal(btn){{
    _completeRow=btn.closest("tr");document.getElementById("complete-notes").value="";
    const m=document.getElementById("modal-complete");m.style.display="block";
    if(!m._positioned){{m.style.left=Math.max(0,(window.innerWidth-m.offsetWidth)/2)+"px";m.style.top=Math.max(0,(window.innerHeight-m.offsetHeight)/2)+"px";m._positioned=true;}}
    isPaused=true;document.getElementById("cd").textContent="Pausado";
  }}
  function closeCompleteModal(){{document.getElementById("modal-complete").style.display="none";isPaused=false;secs=30;_completeRow=null;}}
  async function submitComplete(e){{
    e.preventDefault();if(!_completeRow)return;
    const targetRow=_completeRow;const btn=document.getElementById("btn-submit-complete");
    const notes=document.getElementById("complete-notes").value;
    btn.disabled=true;btn.textContent="Encerrando...";
    try{{
      const r1=await fetch("/admin/completed",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:targetRow.dataset.phone,date:targetRow.dataset.date,time:targetRow.dataset.time,notes:notes}})}});
      if(!r1.ok)throw new Error();
      await fetch("/admin/close_protocol",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:targetRow.dataset.phone,date:targetRow.dataset.date,time:targetRow.dataset.time}})}});
      closeCompleteModal();targetRow.remove();showToast("Atendimento encerrado!");
    }}catch(_){{btn.disabled=false;btn.textContent="Encerrar";showToast("Erro ao encerrar.",false);}}
  }}

  /* Close protocol */
  let _pendingCloseProtocolBtn=null;
  function openConfirmCloseProtocol(btn){{_pendingCloseProtocolBtn=btn;document.getElementById("modal-confirm-protocol").classList.add("open");isPaused=true;document.getElementById("cd").textContent="Pausado";}}
  function closeConfirmProtocolModal(){{document.getElementById("modal-confirm-protocol").classList.remove("open");_pendingCloseProtocolBtn=null;isPaused=false;secs=30;}}
  async function confirmDoCloseProtocol(){{
    const btn=_pendingCloseProtocolBtn;closeConfirmProtocolModal();if(!btn)return;
    const row=btn.closest("tr");btn.disabled=true;
    const res=await fetch("/admin/close_protocol",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time}})}});
    if(res.ok){{row.remove();showToast("Protocolo encerrado.");}}
    else{{btn.disabled=false;showToast("Erro ao encerrar protocolo.",false);}}
  }}

  /* Reschedule no-show */
  async function rescheduleApt(btn){{
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Remarcando...";
    const res=await fetch("/admin/reschedule",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time}})}});
    if(res.ok){{
      row.dataset.status="scheduled";row.querySelector(".badge").className="badge scheduled";row.querySelector(".badge").textContent="Aguardando";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn remind-btn" onclick="sendRemind(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button><button class="action-btn edit-btn" onclick="openEditModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button><button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>';
      showToast("Agendamento reaberto!");applyFilter();
    }} else {{btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> Remarcar';showToast("Erro ao remarcar.",false);}}
  }}

  /* Reset session */
  async function _doResetSession(phone,name,btn,lbl){{
    btn.disabled=true;btn.innerHTML="Resetando...";
    const res=await fetch("/admin/reset_session",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{phone}})}});
    if(res.ok)showToast("Historico da IA resetado para "+name+".");
    else showToast("Erro ao resetar.",false);
    btn.disabled=false;btn.innerHTML=lbl;
  }}
  const RESET_LBL='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Resetar IA';
  async function resetSession(btn){{
    const row=btn.closest("tr");const name=row.dataset.name||"este contato";
    if(!confirm("Resetar o historico da IA para "+name+"?\\n\\nA proxima mensagem sera tratada como nova conversa."))return;
    await _doResetSession(row.dataset.phone,name,btn,RESET_LBL);
  }}
  async function resetSessionByPhone(phone,name,btn){{
    if(!confirm("Resetar o historico da IA para "+name+"?\\n\\nA proxima mensagem sera tratada como nova conversa."))return;
    await _doResetSession(phone,name,btn,RESET_LBL);
  }}

  /* Pending */
  function renderPending(){{
    const tbody=document.getElementById("pending-tbody");
    if(!PENDING_ITEMS.length){{tbody.innerHTML='<tr><td colspan="4" class="empty-row"><div class="empty-state"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:.3;margin-bottom:.75rem"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><div>Nenhuma pendencia no momento.</div></div></td></tr>';return;}}
    tbody.innerHTML=PENDING_ITEMS.map(p=>{{
      const phone=(p.phone||"").replace("@s.whatsapp.net","").replace("@lid","");
      const dt=new Date(p.created_at);
      const dtBr=isNaN(dt.getTime())?(p.created_at||""):dt.toLocaleString("pt-BR");
      const note=(p.note||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      return '<tr><td><span class="phone-num">'+phone+'</span></td><td>'+note+'</td><td>'+dtBr+'</td><td><div class="actions-cell"><button class="action-btn reset-session-btn" onclick="resetSessionByPhone('+JSON.stringify(p.phone)+','+JSON.stringify(phone)+',this)">'+RESET_LBL+'</button><button class="action-btn confirm-btn" onclick="concludePending(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Encerrar</button></div></td></tr>';
    }}).join("");
  }}
  async function concludePending(btn){{
    const rows=document.querySelectorAll("#pending-tbody tr");const row=btn.closest("tr");
    let idx=-1;rows.forEach((r,i)=>{{if(r===row)idx=i;}});
    if(idx<0||idx>=PENDING_ITEMS.length)return;
    const item=PENDING_ITEMS[idx];btn.disabled=true;btn.innerHTML="Concluindo...";
    const res=await fetch("/admin/pending/dismiss",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{id:item.id}})}});
    if(res.ok){{PENDING_ITEMS.splice(idx,1);renderPending();showToast("Pendencia concluida.");}}
    else{{btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Encerrar';showToast("Erro ao concluir.",false);}}
  }}

  let _pendingDismissId=null,_pendingDismissBtn=null;
  function dismissPending(id,btn){{_pendingDismissId=id;_pendingDismissBtn=btn;document.getElementById("modal-confirm-dismiss").classList.add("open");isPaused=true;document.getElementById("cd").textContent="Pausado";}}
  function closeConfirmDismissModal(){{document.getElementById("modal-confirm-dismiss").classList.remove("open");_pendingDismissId=null;_pendingDismissBtn=null;isPaused=false;secs=30;}}
  async function confirmDoDismiss(){{
    const id=_pendingDismissId;const btn=_pendingDismissBtn;closeConfirmDismissModal();if(!id)return;
    btn.disabled=true;btn.textContent="Descartando...";
    const res=await fetch("/admin/pending/dismiss",{{method:"POST",headers:authHeaders(),body:JSON.stringify({{id}})}});
    if(res.ok){{btn.closest("tr").remove();const idx=PENDING_ITEMS.findIndex(p=>p.id===id);if(idx>=0)PENDING_ITEMS.splice(idx,1);showToast("Aviso descartado.");}}
    else{{btn.disabled=false;btn.textContent="Descartar";showToast("Erro ao descartar.",false);}}
  }}

  /* Drag modals */
  (function(){{
    [["modal-new","modal-handle"],["modal-complete","modal-complete-handle"],["modal-edit","modal-edit-handle"]].forEach(([mid,hid])=>{{
      const m=document.getElementById(mid),h=document.getElementById(hid);
      if(!m||!h)return;let drag=false,ox=0,oy=0;
      h.addEventListener("mousedown",e=>{{drag=true;const r=m.getBoundingClientRect();ox=e.clientX-r.left;oy=e.clientY-r.top;document.body.style.userSelect="none";}});
      document.addEventListener("mousemove",e=>{{if(!drag||m.style.display==="none")return;m.style.left=Math.max(0,Math.min(window.innerWidth-m.offsetWidth,e.clientX-ox))+"px";m.style.top=Math.max(0,Math.min(window.innerHeight-m.offsetHeight,e.clientY-oy))+"px";}});
      document.addEventListener("mouseup",()=>{{if(drag){{drag=false;document.body.style.userSelect="";}}}});
    }});
  }})();

  /* Resize calendar panel */
  (function(){{
    const handle=document.getElementById("resize-handle");const right=document.querySelector(".layout-right");
    if(!handle||!right)return;
    const saved=localStorage.getItem("cal-panel-width");if(saved)right.style.width=parseInt(saved)+"px";
    let dragging=false,startX=0,startW=0;
    handle.addEventListener("mousedown",e=>{{dragging=true;startX=e.clientX;startW=right.offsetWidth;handle.classList.add("dragging");document.body.style.cursor="col-resize";document.body.style.userSelect="none";e.preventDefault();}});
    document.addEventListener("mousemove",e=>{{if(!dragging)return;const newW=Math.min(900,Math.max(260,startW+(startX-e.clientX)));right.style.width=newW+"px";}});
    document.addEventListener("mouseup",()=>{{if(!dragging)return;dragging=false;handle.classList.remove("dragging");document.body.style.cursor="";document.body.style.userSelect="";localStorage.setItem("cal-panel-width",right.offsetWidth);}});
  }})();

  /* ── CONFIG PAGE ─────────────────────────────────────────────────────── */
  const DAYS_BR = ["Segunda","Terca","Quarta","Quinta","Sexta","Sabado","Domingo"];
  const TYPE_LABELS = {{faq:"FAQ",policy:"Politica",product_catalog:"Catalogo",script:"Script",manual:"Manual"}};

  /* ── Dirty-state tracking ───────────────────────────────────────────────── */
  const _dirtyTabs = new Set();
  function markDirty(tab) {{
    if (!tab) return;
    _dirtyTabs.add(tab);
    const bt = document.querySelector('.cfg-tab[data-tab="'+tab+'"]');
    if (bt) bt.classList.add("has-dirty");
  }}
  function clearDirty(tab) {{
    if (!tab) return;
    _dirtyTabs.delete(tab);
    const bt = document.querySelector('.cfg-tab[data-tab="'+tab+'"]');
    if (bt) bt.classList.remove("has-dirty");
  }}
  function _activeConfigTab() {{
    return document.querySelector(".cfg-tab.active")?.dataset?.tab || null;
  }}

  /* ── Button loading spinner ─────────────────────────────────────────────── */
  function setBtnLoading(btn, loading) {{
    if (!btn) return;
    if (loading) {{
      btn._savedHTML = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="btn-spinner"></span>Salvando...';
    }} else {{
      btn.disabled = false;
      if (btn._savedHTML !== undefined) {{ btn.innerHTML = btn._savedHTML; btn._savedHTML = undefined; }}
    }}
  }}

  function switchCfgTab(tab) {{
    document.querySelectorAll(".cfg-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".cfg-pane").forEach(p => p.classList.remove("active"));
    const bt = document.querySelector('.cfg-tab[data-tab="'+tab+'"]');
    const pn = document.getElementById("cfg-pane-"+tab);
    if (bt) bt.classList.add("active");
    if (pn) pn.classList.add("active");
    localStorage.setItem("cfgTab", tab);
    if (tab === "status") {{
      loadStatusData();
      _startStatusAutoRefresh();
    }} else {{
      _stopStatusAutoRefresh();
    }}
  }}

  async function loadConfigPage() {{
    const saved = localStorage.getItem("cfgTab") || "loja";
    switchCfgTab(saved);
    await Promise.all([loadBotConfig(), loadBusinessHours(), loadFaqItems(), loadRagConfig(), loadRagDocs(), loadRagLogs(), loadSystemPrompt()]);
    _attachDirtyListeners();
    if (!window._cfgCtrlSAttached) {{
      window._cfgCtrlSAttached = true;
      document.addEventListener("keydown", e => {{
        if ((e.ctrlKey || e.metaKey) && e.key === "s") {{
          const pg = document.querySelector(".page.active");
          if (pg?.id === "page-config") {{
            e.preventDefault();
            _saveCfgActiveTab();
          }}
        }}
      }});
    }}
  }}

  function _attachDirtyListeners() {{
    const trackedPanes = ["loja", "identidade", "horarios", "notificacoes", "avancado"];
    trackedPanes.forEach(tab => {{
      const pane = document.getElementById("cfg-pane-" + tab);
      if (!pane || pane._dirtyAttached) return;
      pane._dirtyAttached = true;
      pane.addEventListener("input",  () => markDirty(tab));
      pane.addEventListener("change", () => markDirty(tab));
    }});
  }}

  function _saveCfgActiveTab() {{
    const tab = _activeConfigTab();
    if (!tab) return;
    // Aba notificacoes tem botão próprio — buscar especificamente
    if (tab === "notificacoes") {{
      const btn = document.querySelector('#cfg-pane-notificacoes .btn-primary');
      if (btn) btn.click();
      return;
    }}
    const paneBtn = document.querySelector('#cfg-pane-' + tab + ' .btn-primary');
    if (paneBtn) paneBtn.click();
  }}

  /* Bot Config */
  async function loadBotConfig() {{
    try {{
      const r = await fetch("/admin/bot-config", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const d = await r.json();
      const set = (id, v) => {{ const el = document.getElementById(id); if (el && v !== undefined) el.value = v || ""; }};
      set("bc-store-name", d.store_name);
      set("bc-store-phone", d.store_phone);
      set("bc-store-address", d.store_address);
      set("bc-store-services", d.store_services);
      set("bc-store-notes", d.store_notes);
      set("bc-bot-name", d.bot_name);
      set("bc-bot-personality", d.bot_personality);
      set("bc-bot-greeting", d.bot_greeting);
      set("bc-bot-extra-rules", d.bot_extra_rules);
      const tone = document.getElementById("bc-bot-tone");
      if (tone) tone.value = d.bot_tone || "informal";
      // Slot settings (exibidos na aba Horarios)
      const slotDurEl  = document.getElementById("bh-slot-duration");
      const slotIntvEl = document.getElementById("bh-slot-interval");
      if (slotDurEl  && d.slot_duration_minutes  != null) slotDurEl.value  = String(d.slot_duration_minutes);
      if (slotIntvEl && d.slot_interval_minutes   != null) slotIntvEl.value = String(d.slot_interval_minutes);
      // Templates de notificação (aba Notificacoes)
      _loadNotifTa(d);
    }} catch(e) {{ console.error("loadBotConfig", e); }}
  }}

  async function saveBotConfig(btn) {{
    setBtnLoading(btn, true);
    const g = id => (document.getElementById(id)?.value || "").trim();
    const body = {{
      store_name: g("bc-store-name"),
      store_phone: g("bc-store-phone"),
      store_address: g("bc-store-address"),
      store_services: g("bc-store-services"),
      store_notes: g("bc-store-notes"),
      bot_name: g("bc-bot-name"),
      bot_tone: document.getElementById("bc-bot-tone")?.value || "informal",
      bot_personality: g("bc-bot-personality"),
      bot_greeting: g("bc-bot-greeting"),
      bot_extra_rules: g("bc-bot-extra-rules"),
    }};
    try {{
      const r = await fetch("/admin/bot-config", {{method:"POST",headers:authHeaders(),body:JSON.stringify(body)}});
      if (r.ok) {{
        clearDirty(_activeConfigTab());
        showToast("Configuracoes salvas e prompt atualizado!");
        loadSystemPrompt();
      }} else showToast("Erro ao salvar.", false);
    }} catch(e) {{ showToast("Erro: " + e.message, false); }}
    setBtnLoading(btn, false);
  }}

  /* Business Hours */
  async function loadBusinessHours() {{
    try {{
      const r = await fetch("/admin/business-hours", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const data = await r.json();
      const grid = document.getElementById("bh-grid");
      if (!grid) return;
      grid.innerHTML = data.map(row => {{
        const ot = row.open_time || "";
        const ct = row.close_time || "";
        const dis = row.is_open ? "" : " disabled";
        return '<div class="bh-row">'
          + '<span class="bh-day">' + DAYS_BR[row.day_of_week] + '</span>'
          + '<label class="toggle-switch" title="Aberto"><input type="checkbox" class="bh-open" data-day="' + row.day_of_week + '" ' + (row.is_open ? "checked" : "") + ' onchange="updateBhRow(' + row.day_of_week + ')"><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
          + '<label class="toggle-switch" title="Mediante encaixe"><input type="checkbox" class="bh-flex" data-day="' + row.day_of_week + '" ' + (row.is_flexible ? "checked" : "") + '><span class="toggle-track"><span class="toggle-thumb"></span></span></label>'
          + '<span class="bh-flex-lbl">Encaixe</span>'
          + '<input type="time" class="rp-input bh-ot" data-day="' + row.day_of_week + '" value="' + ot + '"' + dis + '>'
          + '<span style="color:var(--muted);font-size:.8rem">&#8211;</span>'
          + '<input type="time" class="rp-input bh-ct" data-day="' + row.day_of_week + '" value="' + ct + '"' + dis + '>'
          + '</div>';
      }}).join("");
    }} catch(e) {{ console.error("loadBusinessHours", e); }}
  }}

  function updateBhRow(day) {{
    const isOpen = document.querySelector('.bh-open[data-day="' + day + '"]').checked;
    document.querySelector('.bh-ot[data-day="' + day + '"]').disabled = !isOpen;
    document.querySelector('.bh-ct[data-day="' + day + '"]').disabled = !isOpen;
  }}

  async function saveBusinessHours(btn) {{
    setBtnLoading(btn, true);
    const rows = [];
    [0,1,2,3,4,5,6].forEach(day => {{
      const isOpen = document.querySelector('.bh-open[data-day="'+day+'"]')?.checked || false;
      const isFlex = document.querySelector('.bh-flex[data-day="'+day+'"]')?.checked || false;
      const ot = document.querySelector('.bh-ot[data-day="'+day+'"]')?.value || null;
      const ct = document.querySelector('.bh-ct[data-day="'+day+'"]')?.value || null;
      rows.push({{day_of_week:day, is_open:isOpen, is_flexible:isFlex, open_time:ot||null, close_time:ct||null}});
    }});
    const slotDur  = parseInt(document.getElementById("bh-slot-duration")?.value  || "30");
    const slotIntv = parseInt(document.getElementById("bh-slot-interval")?.value  || "0");
    try {{
      const [r1, r2] = await Promise.all([
        fetch("/admin/business-hours", {{method:"POST",headers:authHeaders(),body:JSON.stringify(rows)}}),
        fetch("/admin/bot-config", {{method:"POST",headers:authHeaders(),body:JSON.stringify({{slot_duration_minutes:slotDur, slot_interval_minutes:slotIntv}})}})
      ]);
      if (r1.ok && r2.ok) {{ clearDirty("horarios"); showToast("Horarios e duracoes salvos!"); }}
      else showToast("Erro ao salvar.", false);
    }} catch(e) {{ showToast("Erro: " + e.message, false); }}
    setBtnLoading(btn, false);
  }}

  /* FAQ */
  let _faqMap = {{}};

  function openFaqById(id) {{ openFaqModal(_faqMap[id] || null); }}

  async function loadFaqItems() {{
    try {{
      const r = await fetch("/admin/faq", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const items = await r.json();
      _faqMap = {{}};
      items.forEach(f => _faqMap[f.id] = f);
      const tbody = document.getElementById("faq-tbody");
      const ex = document.getElementById("faq-ex-box");
      if (!tbody) return;
      if (!items.length) {{
        tbody.innerHTML = '<tr><td colspan="4" class="empty-row"><div class="empty-state">Nenhum FAQ cadastrado. Adicione um para comecar.</div></td></tr>';
        if (ex) ex.style.display = "block";
        return;
      }}
      if (ex) ex.style.display = "none";
      tbody.innerHTML = items.map(f => {{
        const q = (f.question || "").replace(/</g,"&lt;");
        const a = (f.answer || "").replace(/</g,"&lt;");
        const badge = f.is_active
          ? '<span class="config-badge ok">&#10003; Ativo</span>'
          : '<span class="config-badge err">&#10007; Inativo</span>';
        const tog = f.is_active
          ? '<button class="action-btn cancel-btn" onclick="toggleFaq(' + f.id + ',false)">Desativar</button>'
          : '<button class="action-btn confirm-btn" onclick="toggleFaq(' + f.id + ',true)">Ativar</button>';
        return '<tr>'
          + '<td style="max-width:220px;word-break:break-word">' + q + '</td>'
          + '<td style="max-width:260px;word-break:break-word;color:var(--text2);font-size:.82rem">' + a + '</td>'
          + '<td>' + badge + '</td>'
          + '<td><div class="actions-cell">'
          + '<button class="action-btn edit-btn" onclick="openFaqById(' + f.id + ')">Editar</button>'
          + tog
          + '<button class="action-btn close-protocol-btn" onclick="deleteFaq(' + f.id + ')">Excluir</button>'
          + '</div></td></tr>';
      }}).join("");
    }} catch(e) {{ console.error("loadFaqItems", e); }}
  }}

  function openFaqModal(item) {{
    document.getElementById("form-faq").reset();
    const titleEl = document.getElementById("faq-modal-title");
    const idEl = document.getElementById("faq-edit-id");
    if (item && item.id) {{
      if (titleEl) titleEl.textContent = "Editar FAQ";
      idEl.value = item.id;
      document.getElementById("faq-question").value = item.question || "";
      document.getElementById("faq-answer").value = item.answer || "";
    }} else {{
      if (titleEl) titleEl.textContent = "Adicionar FAQ";
      idEl.value = "";
    }}
    const m = document.getElementById("modal-faq");
    m.style.display = "block";
    if (!m._positioned) {{
      m.style.left = Math.max(0,(window.innerWidth-m.offsetWidth)/2) + "px";
      m.style.top  = Math.max(0,(window.innerHeight-m.offsetHeight)/2) + "px";
      m._positioned = true;
    }}
  }}
  function closeFaqModal() {{ document.getElementById("modal-faq").style.display = "none"; }}

  async function submitFaq(e) {{
    e.preventDefault();
    const btn = document.getElementById("btn-submit-faq");
    btn.disabled = true; btn.textContent = "Salvando...";
    const editId = document.getElementById("faq-edit-id").value;
    const body = {{
      question: document.getElementById("faq-question").value.trim(),
      answer:   document.getElementById("faq-answer").value.trim(),
      sort_order: 0,
    }};
    try {{
      const url = editId ? "/admin/faq/" + editId : "/admin/faq";
      const method = editId ? "PUT" : "POST";
      const r = await fetch(url, {{method,headers:authHeaders(),body:JSON.stringify(body)}});
      if (r.ok) {{ closeFaqModal(); loadFaqItems(); showToast("FAQ salvo!"); }}
      else showToast("Erro ao salvar FAQ.", false);
    }} catch(ex) {{ showToast("Erro: " + ex.message, false); }}
    btn.disabled = false; btn.textContent = "Salvar";
  }}

  async function toggleFaq(id, state) {{
    const r = await fetch("/admin/faq/" + id + "/toggle", {{method:"PATCH",headers:authHeaders(),body:JSON.stringify({{is_active:state}})}});
    if (r.ok) {{ loadFaqItems(); showToast("FAQ atualizado!"); }}
    else showToast("Erro.", false);
  }}

  async function deleteFaq(id) {{
    if (!confirm("Excluir este FAQ?")) return;
    const r = await fetch("/admin/faq/" + id, {{method:"DELETE",headers:authHeaders()}});
    if (r.ok) {{ loadFaqItems(); showToast("FAQ excluido."); }}
    else showToast("Erro ao excluir.", false);
  }}

  /* System Prompt */
  async function loadSystemPrompt() {{
    try {{
      const r = await fetch("/admin/system-prompt", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const data = await r.json();
      const ta = document.getElementById("system-prompt-ta");
      if (ta) ta.value = data.prompt;
    }} catch(e) {{ console.error("loadSystemPrompt", e); }}
  }}

  async function savePrompt(btn) {{
    setBtnLoading(btn, true);
    const prompt = document.getElementById("system-prompt-ta").value;
    try {{
      const r = await fetch("/admin/system-prompt", {{method:"POST",headers:authHeaders(),body:JSON.stringify({{prompt}})}});
      if (r.ok) {{ clearDirty("avancado"); showToast("Prompt salvo!"); }}
      else showToast("Erro ao salvar.", false);
    }} catch(e) {{ showToast("Erro: " + e.message, false); }}
    setBtnLoading(btn, false);
  }}

  /* ── Notification Templates ─────────────────────────────────────────────── */
  const NOTIF_DEFAULTS = {{
    msg_lembrete_dia:  "Olá, {{nome}}! Aqui é a Liza da LenzÓtica 👓\\n\\nPassando para lembrar que *amanhã* você tem consulta marcada para as *{{hora}}h* ({{data}}).\\n\\nQualquer dúvida é só nos chamar. Te esperamos!",
    msg_lembrete_hora: "Olá, {{nome}}! Aqui é a Liza da LenzÓtica 👓\\n\\nSua consulta está marcada para *{{data}}* às *{{hora}}h*.\\n\\nVocê confirma sua presença? Responda *SIM* para confirmar ou *NÃO* caso precise reagendar.",
    msg_cancelamento:  "Olá, {{nome}}. Seu agendamento para *{{data}}* às *{{hora}}h* foi cancelado pois não recebemos confirmação de presença.\\n\\nDeseja reagendar? É só nos enviar uma mensagem 😊",
    msg_retorno:       "Olá, {{nome}}! Aqui é a Liza da LenzÓtica 👓\\n\\nPassando para lembrar que está na hora do seu retorno na ótica! Que tal agendarmos uma consulta? É só responder *SIM* que eu marco para você 😊",
  }};

  /* Insere variável na posição do cursor do textarea */
  function insertVar(taId, variable) {{
    const ta = document.getElementById(taId);
    if (!ta) return;
    const s = ta.selectionStart ?? ta.value.length;
    const e = ta.selectionEnd   ?? ta.value.length;
    ta.value = ta.value.slice(0, s) + variable + ta.value.slice(e);
    ta.selectionStart = ta.selectionEnd = s + variable.length;
    ta.focus();
    markDirty("notificacoes");
    ta.dispatchEvent(new Event("input"));
  }}

  /* Contador de caracteres por textarea */
  function updateCharCount(ta, counterId) {{
    const n = ta.value.length;
    const el = document.getElementById(counterId);
    if (!el) return;
    el.textContent = n + " caractere" + (n !== 1 ? "s" : "");
    el.className = "notif-char-count" + (n > 1000 ? " over" : n > 700 ? " warn" : "");
  }}

  /* Carrega templates no pane (chamado do loadBotConfig) */
  function _loadNotifTa(d) {{
    const pairs = [
      ["notif-ta-lembrete-dia",  "msg_lembrete_dia",  "notif-cc-lembrete-dia"],
      ["notif-ta-lembrete-hora", "msg_lembrete_hora", "notif-cc-lembrete-hora"],
      ["notif-ta-cancelamento",  "msg_cancelamento",  "notif-cc-cancelamento"],
      ["notif-ta-retorno",       "msg_retorno",       "notif-cc-retorno"],
    ];
    pairs.forEach(([taId, key, ccId]) => {{
      const ta = document.getElementById(taId);
      if (!ta) return;
      ta.value = (d[key] && d[key].trim()) ? d[key] : "";
      const cc = document.getElementById(ccId);
      if (cc) updateCharCount(ta, ccId);
    }});
  }}

  async function saveNotifTemplates(btn) {{
    setBtnLoading(btn, true);
    const g = id => document.getElementById(id)?.value || "";
    const body = {{
      msg_lembrete_dia:  g("notif-ta-lembrete-dia"),
      msg_lembrete_hora: g("notif-ta-lembrete-hora"),
      msg_cancelamento:  g("notif-ta-cancelamento"),
      msg_retorno:       g("notif-ta-retorno"),
    }};
    try {{
      const r = await fetch("/admin/bot-config", {{method:"POST",headers:authHeaders(),body:JSON.stringify(body)}});
      if (r.ok) {{ clearDirty("notificacoes"); showToast("Templates salvos!"); }}
      else showToast("Erro ao salvar.", false);
    }} catch(e) {{ showToast("Erro: " + e.message, false); }}
    setBtnLoading(btn, false);
  }}

  /* ── System Status ──────────────────────────────────────────────────────── */
  let _statusInterval   = null;
  let _statusCountdown  = 30;
  const _STATUS_INTERVAL = 30; // segundos

  const _STATUS_ICONS = {{
    server:   '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
    postgres: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
    pgvector: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    calendar: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    whatsapp: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.63 3.42 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
  }};

  const _STATUS_BADGE_LABELS = {{ ok:"OK", warn:"Aviso", error:"Erro", loading:"...", unknown:"—" }};

  function _updateNextRefreshLabel() {{
    const el = document.getElementById("status-next-refresh");
    if (el) el.textContent = _statusCountdown;
  }}

  function _startStatusAutoRefresh() {{
    _stopStatusAutoRefresh();
    _statusCountdown = _STATUS_INTERVAL;
    _updateNextRefreshLabel();
    _statusInterval = setInterval(() => {{
      _statusCountdown--;
      _updateNextRefreshLabel();
      if (_statusCountdown <= 0) {{
        _statusCountdown = _STATUS_INTERVAL;
        loadStatusData();
      }}
    }}, 1000);
  }}

  function _stopStatusAutoRefresh() {{
    if (_statusInterval) {{ clearInterval(_statusInterval); _statusInterval = null; }}
  }}

  function _renderStatusChecks(data) {{
    const grid = document.getElementById("status-grid");
    if (!grid) return;
    const checks = data.checks || [];
    if (!checks.length) {{
      grid.innerHTML = '<div style="padding:2rem 1.25rem;font-size:.84rem;color:var(--muted)">Nenhum dado disponivel.</div>';
      return;
    }}
    grid.innerHTML = checks.map(c => {{
      const icon   = _STATUS_ICONS[c.key] || _STATUS_ICONS.server;
      const badge  = _STATUS_BADGE_LABELS[c.status] || c.status;
      const latHtml = c.latency_ms != null
        ? '<span class="status-latency">' + c.latency_ms + ' ms</span>'
        : '';
      return '<div class="status-row ' + (c.status || 'unknown') + '">'
        + '<div class="status-row-icon">' + icon + '</div>'
        + '<div class="status-row-name">' + c.label + '</div>'
        + '<div class="status-row-detail">' + (c.detail || '') + '</div>'
        + '<div class="status-row-right">' + latHtml
        + '<span class="status-badge ' + (c.status || 'unknown') + '">' + badge + '</span>'
        + '</div></div>';
    }}).join('');
  }}

  async function loadStatusData() {{
    const grid = document.getElementById("status-grid");
    if (!grid) return;
    try {{
      const r = await fetch("/admin/system-status", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      _renderStatusChecks(data);
      const el = document.getElementById("status-last-check");
      if (el) {{
        const d = new Date(data.checked_at);
        el.textContent = "Ultima verificacao: " + d.toLocaleTimeString("pt-BR");
        el.style.color = "";
      }}
    }} catch(e) {{
      grid.innerHTML = '<div style="padding:1.25rem;font-size:.83rem;color:#dc2626">Erro ao verificar: ' + e.message + '</div>';
    }}
  }}

  async function refreshStatus(btn) {{
    if (btn) {{
      btn._origInner = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="animation:btn-spin .65s linear infinite"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Verificando...';
    }}
    _statusCountdown = _STATUS_INTERVAL;
    _updateNextRefreshLabel();
    await loadStatusData();
    if (btn) {{ btn.disabled = false; btn.innerHTML = btn._origInner; }}
  }}

  function resetNotifTemplates() {{
    if (!confirm("Restaurar todos os templates para o texto padrão do sistema?\\n\\nEsta ação substituirá seus textos personalizados.")) return;
    const pairs = [
      ["notif-ta-lembrete-dia",  "msg_lembrete_dia",  "notif-cc-lembrete-dia"],
      ["notif-ta-lembrete-hora", "msg_lembrete_hora", "notif-cc-lembrete-hora"],
      ["notif-ta-cancelamento",  "msg_cancelamento",  "notif-cc-cancelamento"],
      ["notif-ta-retorno",       "msg_retorno",       "notif-cc-retorno"],
    ];
    pairs.forEach(([taId, key, ccId]) => {{
      const ta = document.getElementById(taId);
      if (!ta) return;
      ta.value = NOTIF_DEFAULTS[key] || "";
      updateCharCount(ta, ccId);
    }});
    markDirty("notificacoes");
    showToast("Templates restaurados. Clique em Salvar para confirmar.");
  }}

  async function rebuildPrompt() {{
    const r = await fetch("/admin/build-prompt", {{method:"POST",headers:authHeaders()}});
    if (r.ok) {{ showToast("Prompt regenerado com sucesso!"); loadSystemPrompt(); }}
    else showToast("Erro ao regenerar prompt.", false);
  }}

  /* RAG Config */
  async function loadRagConfig() {{
    try {{
      const r = await fetch("/admin/rag/config", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const cfg = await r.json();
      const set = (id, v) => {{ const el = document.getElementById(id); if (el) el.value = v; }};
      const chk = (id, v) => {{ const el = document.getElementById(id); if (el) el.checked = v; }};
      chk("rag-enabled", cfg.enabled);
      set("rag-top-k", cfg.top_k);
      set("rag-min-sim", cfg.min_similarity);
      set("rag-max-ctx", cfg.max_context_tokens);
      set("rag-chunk-size", cfg.chunk_size);
      set("rag-chunk-overlap", cfg.chunk_overlap);
    }} catch(e) {{ console.error("loadRagConfig", e); }}
  }}

  async function saveRagEnabled() {{
    const enabled = document.getElementById("rag-enabled").checked;
    await fetch("/admin/rag/config", {{method:"POST",headers:authHeaders(),body:JSON.stringify({{enabled}})}});
    showToast(enabled ? "RAG ativado." : "RAG desativado.");
  }}

  async function saveRagConfig(btn) {{
    setBtnLoading(btn, true);
    const cfg = {{
      top_k: parseInt(document.getElementById("rag-top-k").value),
      min_similarity: parseFloat(document.getElementById("rag-min-sim").value),
      max_context_tokens: parseInt(document.getElementById("rag-max-ctx").value),
      chunk_size: parseInt(document.getElementById("rag-chunk-size").value),
      chunk_overlap: parseInt(document.getElementById("rag-chunk-overlap").value),
    }};
    try {{
      const r = await fetch("/admin/rag/config", {{method:"POST",headers:authHeaders(),body:JSON.stringify(cfg)}});
      if (r.ok) {{ clearDirty("avancado"); showToast("Parametros salvos!"); }}
      else showToast("Erro ao salvar.", false);
    }} catch(e) {{ showToast("Erro: " + e.message, false); }}
    setBtnLoading(btn, false);
  }}

  /* RAG Documents */
  const TYPE_ICONS = {{faq:"&#128172;",policy:"&#128196;",product_catalog:"&#128722;",script:"&#127908;",manual:"&#128214;"}};
  const TYPE_DESCS = {{faq:"Perguntas e respostas",policy:"Regras da loja",product_catalog:"Produtos e precos",script:"Roteiro de atendimento",manual:"Outras informacoes"}};

  function _updateRagStats(docs) {{
    const statsRow = document.getElementById("rag-stats-row");
    const docsEl   = document.getElementById("rag-stat-docs");
    const chunksEl = document.getElementById("rag-stat-chunks");
    if (!statsRow || !docsEl || !chunksEl) return;
    const active = docs.filter(d => d.is_active).length;
    const chunks = docs.reduce((s,d) => s + (d.chunk_count||0), 0);
    docsEl.textContent   = active + " doc" + (active !== 1 ? "s" : "") + " ativo" + (active !== 1 ? "s" : "");
    chunksEl.textContent = chunks + " chunk" + (chunks !== 1 ? "s" : "");
    statsRow.style.display = docs.length ? "flex" : "none";
  }}

  const RAG_EXAMPLES = [
    {{"title":"Politica de cancelamento","type":"policy","content":"Cancelamentos devem ser feitos com pelo menos 2 horas de antecedencia. Apos esse prazo, o horario e liberado mas pode nao ser substituido no mesmo dia."}},
    {{"title":"Tabela de precos","type":"product_catalog","content":"Armações a partir de R$149,90. Lentes simples a partir de R$99,90. Lentes anti-reflexo a partir de R$149,90. Oculos de sol a partir de R$89,90."}},
    {{"title":"Prazo de confeccao","type":"faq","content":"O prazo medio de confeccao e de 5 a 7 dias uteis apos a aprovacao do pedido e pagamento. Lentes especiais podem levar ate 15 dias."}},
    {{"title":"Formas de pagamento","type":"faq","content":"Aceitamos dinheiro, PIX, cartao de debito e credito (ate 6x sem juros). Nao aceitamos cheque."}},
  ];

  async function loadRagDocs() {{
    try {{
      const r = await fetch("/admin/rag/documents", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const docs = await r.json();
      const tbody = document.getElementById("doc-tbody");
      if (!tbody) return;
      _updateRagStats(docs);
      if (!docs.length) {{
        const examples = RAG_EXAMPLES.map(ex =>
          '<span class="rag-example-item" onclick="_fillDocExample('+JSON.stringify(ex.title)+','+JSON.stringify(ex.type)+','+JSON.stringify(ex.content)+')" title="Clique para usar como base">'
          + (TYPE_ICONS[ex.type]||"&#128196;") + " " + ex.title + '</span>'
        ).join("");
        tbody.innerHTML = '<tr><td colspan="5" class="empty-row">'
          + '<div class="rag-empty-box">'
          + '<div class="rag-empty-icon">&#128218;</div>'
          + '<div class="rag-empty-title">Nenhum documento ainda</div>'
          + '<div class="rag-empty-sub">Adicione documentos para que a IA responda com informacoes reais da sua loja — precos, prazos, politicas, horarios e muito mais.</div>'
          + '<div class="rag-example-grid">' + examples + '</div>'
          + '<div style="font-size:.72rem;color:var(--muted);margin-top:.25rem">&#8593; Clique num exemplo para comecar com um modelo pre-preenchido</div>'
          + '</div></td></tr>';
        return;
      }}
      tbody.innerHTML = docs.map(d => {{
        const title  = (d.title || "").replace(/</g,"&lt;");
        const icon   = TYPE_ICONS[d.source_type] || "&#128196;";
        const lbl    = TYPE_LABELS[d.source_type] || d.source_type;
        const desc   = TYPE_DESCS[d.source_type]  || "";
        const chunks = d.chunk_count || 0;
        const chunkColor = chunks === 0 ? "color:#dc2626" : chunks < 3 ? "color:#d97706" : "color:#059669";
        const badge = d.is_active
          ? '<span class="config-badge ok">&#10003; Ativo</span>'
          : '<span class="config-badge err">&#10007; Inativo</span>';
        const toggleBtn = d.is_active
          ? '<button class="action-btn cancel-btn" onclick="toggleDoc(' + d.id + ',false)">Desativar</button>'
          : '<button class="action-btn confirm-btn" onclick="toggleDoc(' + d.id + ',true)">Ativar</button>';
        return '<tr>'
          + '<td><strong style="font-size:.84rem">' + title + '</strong></td>'
          + '<td><span class="rag-type-chip" style="cursor:default" title="' + desc + '">' + icon + ' ' + lbl + '</span></td>'
          + '<td><span style="font-weight:600;' + chunkColor + '">' + chunks + '</span>'
          + (chunks === 0 ? ' <span style="font-size:.7rem;color:#dc2626">(vazio)</span>' : '') + '</td>'
          + '<td>' + badge + '</td>'
          + '<td><div class="actions-cell">' + toggleBtn
          + '<button class="action-btn close-protocol-btn" onclick="deleteDoc(' + d.id + ')">Excluir</button>'
          + '</div></td></tr>';
      }}).join("");
    }} catch(e) {{ console.error("loadRagDocs", e); }}
  }}

  function _fillDocExample(title, type, content) {{
    openDocModal();
    setTimeout(() => {{
      const t = document.getElementById("doc-title");
      const tp = document.getElementById("doc-type");
      const c = document.getElementById("doc-content");
      if (t) t.value = title;
      if (tp) tp.value = type;
      if (c) c.value = content;
    }}, 80);
  }}

  async function toggleDoc(id, newState) {{
    const r = await fetch("/admin/rag/documents/" + id + "/toggle", {{method:"PATCH",headers:authHeaders(),body:JSON.stringify({{is_active:newState}})}});
    if (r.ok) {{ loadRagDocs(); showToast(newState ? "Documento ativado!" : "Documento desativado."); }}
    else showToast("Erro.", false);
  }}

  async function deleteDoc(id) {{
    if (!confirm("Excluir este documento e todos os seus chunks?\\n\\nEsta acao nao pode ser desfeita.")) return;
    const r = await fetch("/admin/rag/documents/" + id, {{method:"DELETE",headers:authHeaders()}});
    if (r.ok) {{ loadRagDocs(); showToast("Documento excluido."); }}
    else showToast("Erro ao excluir.", false);
  }}

  /* Doc Modal */
  function openDocModal() {{
    document.getElementById("form-doc").reset();
    const m = document.getElementById("modal-doc");
    m.style.display = "block";
    if (!m._positioned) {{
      m.style.left = Math.max(0,(window.innerWidth-m.offsetWidth)/2) + "px";
      m.style.top  = Math.max(0,(window.innerHeight-m.offsetHeight)/2) + "px";
      m._positioned = true;
    }}
  }}
  function closeDocModal() {{ document.getElementById("modal-doc").style.display = "none"; }}

  async function submitDoc(e) {{
    e.preventDefault();
    const btn = document.getElementById("btn-submit-doc");
    btn.disabled = true; btn.textContent = "Indexando...";
    const body = {{
      title:       document.getElementById("doc-title").value.trim(),
      source_type: document.getElementById("doc-type").value,
      content:     document.getElementById("doc-content").value.trim(),
    }};
    try {{
      const r = await fetch("/admin/rag/documents", {{method:"POST",headers:authHeaders(),body:JSON.stringify(body)}});
      if (r.ok) {{ const data = await r.json(); closeDocModal(); loadRagDocs(); showToast("Documento indexado (" + data.chunk_count + " chunks)!"); }}
      else showToast("Erro ao indexar.", false);
    }} catch(ex) {{ showToast("Erro: " + ex.message, false); }}
    btn.disabled = false; btn.textContent = "Indexar e Salvar";
  }}

  /* RAG Logs */
  async function loadRagLogs() {{
    try {{
      const r = await fetch("/admin/rag/logs", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const logs = await r.json();
      const tbody = document.getElementById("rag-log-tbody");
      if (!tbody) return;
      if (!logs.length) {{
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row">'
          + '<div class="rag-empty-box">'
          + '<div class="rag-empty-icon">&#128203;</div>'
          + '<div class="rag-empty-title">Nenhuma consulta registrada ainda</div>'
          + '<div class="rag-empty-sub">Quando clientes enviarem mensagens e o RAG estiver ativo, cada busca sera registrada aqui — voce vera quais perguntas acionaram a base de conhecimento e com qual similaridade.</div>'
          + '</div></td></tr>';
        return;
      }}
      tbody.innerHTML = logs.map(l => {{
        const phone = (l.phone || "").replace("@s.whatsapp.net","").replace("@lid","");
        const dt    = new Date(l.created_at);
        const dtBr  = isNaN(dt.getTime()) ? (l.created_at || "") : dt.toLocaleString("pt-BR");
        const simVal = (l.top_similarity !== null && l.top_similarity !== undefined) ? l.top_similarity * 100 : null;
        let simHtml;
        if (simVal === null) {{
          simHtml = '<span style="color:var(--muted)">&#8212;</span>';
        }} else {{
          const cls = simVal >= 75 ? "sim-cell-high" : simVal >= 50 ? "sim-cell-mid" : "sim-cell-low";
          const dot = simVal >= 75 ? "sim-high"      : simVal >= 50 ? "sim-mid"      : "sim-low";
          simHtml = '<span class="' + cls + '"><span class="rag-sim-dot ' + dot + '" style="display:inline-block;margin-right:.3rem;vertical-align:middle"></span>' + simVal.toFixed(1) + '%</span>';
        }}
        const lat   = l.latency_ms ? l.latency_ms + "ms" : "&#8212;";
        const query = (l.query_text || "").replace(/</g,"&lt;").substring(0, 65);
        const fullQ = (l.query_text || "").replace(/"/g,"&quot;");
        const chunks = l.chunks_returned || 0;
        const chunkStyle = chunks === 0 ? 'style="color:#dc2626"' : '';
        return '<tr>'
          + '<td><span class="phone-num">' + phone + '</span></td>'
          + '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + fullQ + '">' + query + (query.length >= 65 ? '…' : '') + '</td>'
          + '<td ' + chunkStyle + '>' + chunks + '</td>'
          + '<td>' + simHtml + '</td>'
          + '<td style="color:var(--text2);font-size:.8rem">' + lat + '</td>'
          + '<td style="font-size:.8rem;color:var(--muted)">' + dtBr + '</td>'
          + '</tr>';
      }}).join("");
    }} catch(e) {{ console.error("loadRagLogs", e); }}
  }}

  /* ── CLIENTES ───────────────────────────────────────────────────────────── */
  let _clientsData = [];
  let _clientFilter = "all";
  let _deletingClientId = null;
  let _notifyingClientId = null;
  let _clientSort = {{col: null, dir: 1}};

  /* Retorna label e CSS class para status de retorno */
  function clientReturnStatus(returnDate) {{
    if (!returnDate) return {{cls:"return-none", label:"Sem retorno"}};
    const today = new Date(); today.setHours(0,0,0,0);
    const rd = new Date(returnDate + "T00:00:00");
    const diffDays = Math.round((rd - today) / 86400000);
    if (diffDays < 0)  return {{cls:"return-overdue",  label:"Atrasado " + Math.abs(diffDays) + "d"}};
    if (diffDays <= 30) return {{cls:"return-upcoming", label:"Em " + diffDays + " dia" + (diffDays !== 1 ? "s" : "")}};
    const months = Math.round(diffDays / 30);
    return {{cls:"return-ok", label:"Em ~" + months + " mes" + (months !== 1 ? "es" : "")}};
  }}

  function _fmtDate(iso) {{
    if (!iso) return "—";
    const [y,m,d] = iso.split("-");
    return d + "/" + m + "/" + y;
  }}

  async function loadClients() {{
    try {{
      const [cr, sr] = await Promise.all([
        fetch("/admin/clients", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}}),
        fetch("/admin/clients/stats", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}})
      ]);
      if (!cr.ok) return;
      _clientsData = await cr.json();
      if (sr.ok) {{
        const s = await sr.json();
        const set = (id, v) => {{ const el = document.getElementById(id); if (el) el.textContent = v ?? "—"; }};
        set("cm-total",    s.total    ?? "—");
        set("cm-new",      s.new_this_month ?? "—");
        set("cm-upcoming", s.upcoming ?? "—");
        set("cm-overdue",  s.overdue  ?? "—");
        // Atualiza badge da sidebar
        const badge = document.querySelector('.nav-item[data-page="clientes"] .nav-badge');
        if (badge) badge.textContent = s.total ?? 0;
      }}
      filterClients();
    }} catch(e) {{ console.error("loadClients", e); }}
  }}

  function setClientFilter(btn) {{
    document.querySelectorAll(".filter-chip").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _clientFilter = btn.dataset.cf;
    filterClients();
  }}

  function filterClients() {{
    const q = (document.getElementById("client-search")?.value || "").toLowerCase();
    let filtered = _clientsData.filter(c => {{
      const text = ((c.first_name||"") + " " + (c.last_name||"") + " " + (c.phone||"")).toLowerCase();
      if (q && !text.includes(q)) return false;
      if (_clientFilter !== "all") {{
        const st = clientReturnStatus(c.return_date);
        if (_clientFilter === "overdue"  && !st.cls.includes("overdue"))  return false;
        if (_clientFilter === "upcoming" && !st.cls.includes("upcoming")) return false;
        if (_clientFilter === "ok"       && !st.cls.includes("ok"))       return false;
      }}
      return true;
    }});
    // Ordenação
    if (_clientSort.col) {{
      filtered = _applySortClients(filtered);
    }} else {{
      // Ordenação padrão inteligente: atrasados → próximos → ok → sem retorno
      filtered = filtered.slice().sort((a, b) => {{
        const oa = _returnStatusOrder(a.return_date);
        const ob = _returnStatusOrder(b.return_date);
        if (oa !== ob) return oa - ob;
        return (a.first_name||"").localeCompare(b.first_name||"");
      }});
    }}
    renderClientsTable(filtered);
  }}

  function _applySortClients(list) {{
    const col = _clientSort.col;
    const dir = _clientSort.dir;
    return list.slice().sort((a, b) => {{
      let va, vb;
      if (col === "return_status_order") {{
        va = _returnStatusOrder(a.return_date);
        vb = _returnStatusOrder(b.return_date);
      }} else if (col === "visit_count") {{
        va = a.visit_count || 0;
        vb = b.visit_count || 0;
      }} else {{
        va = (a[col] || "");
        vb = (b[col] || "");
      }}
      if (va < vb) return -1 * dir;
      if (va > vb) return  1 * dir;
      return 0;
    }});
  }}

  function sortClients(col) {{
    if (_clientSort.col === col) {{
      _clientSort.dir *= -1;
    }} else {{
      _clientSort.col = col;
      _clientSort.dir = 1;
    }}
    // Atualiza ícones
    document.querySelectorAll(".sortable-th").forEach(th => {{
      th.classList.remove("sort-asc","sort-desc");
    }});
    const th = document.getElementById("sh-" + col);
    if (th) th.classList.add(_clientSort.dir === 1 ? "sort-asc" : "sort-desc");
    filterClients();
  }}

  function _returnStatusOrder(returnDate) {{
    if (!returnDate) return 3;
    const today = new Date(); today.setHours(0,0,0,0);
    const rd = new Date(returnDate + "T00:00:00");
    const diff = Math.round((rd - today) / 86400000);
    if (diff < 0)  return 0; // overdue
    if (diff <= 30) return 1; // upcoming
    return 2; // ok
  }}

  function renderClientsTable(clients) {{
    const tbody = document.getElementById("clients-tbody");
    if (!tbody) return;
    if (!clients.length) {{
      const emptyMsg = _clientsData.length === 0
        ? "<div class='clients-empty'><div class='clients-empty-icon'>&#128100;</div><div>Nenhum cliente cadastrado.<br>Clique em <strong>Novo Cliente</strong> para comecar.</div></div>"
        : "<div class='clients-empty'><div class='clients-empty-icon'>&#128269;</div><div>Nenhum cliente encontrado com os filtros atuais.</div></div>";
      tbody.innerHTML = '<tr><td colspan="10" class="empty-row">' + emptyMsg + '</td></tr>';
      return;
    }}
    tbody.innerHTML = clients.map(c => {{
      const st = clientReturnStatus(c.return_date);
      const phone = (c.phone || "").replace("@s.whatsapp.net","").replace("@lid","");
      const phoneLink = phone
        ? '<a class="client-phone-link" href="https://wa.me/' + phone + '" target="_blank" title="Abrir no WhatsApp">' + phone + '</a>'
        : '<span style="color:var(--muted)">—</span>';
      const notesEsc = (c.notes || "").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      const notesShort = notesEsc.length > 40 ? notesEsc.substring(0,40) + "…" : (notesEsc || "—");
      const notifyDisabled = !phone ? " disabled title='Sem telefone'" : "";
      const visits = c.visit_count || 0;
      const visitBadge = '<span class="visit-badge' + (visits > 0 ? " has-visits" : "") + '">' + visits + '</span>';
      const birthFmt = c.birth_date ? _fmtDate(c.birth_date) : '<span style="color:var(--muted)">—</span>';
      return '<tr data-client-id="' + c.id + '">'
        + '<td><span class="client-name">' + (c.first_name || "") + '</span></td>'
        + '<td>' + (c.last_name || '<span style="color:var(--muted)">—</span>') + '</td>'
        + '<td>' + phoneLink + '</td>'
        + '<td style="text-align:center">' + visitBadge + '</td>'
        + '<td>' + _fmtDate(c.last_appointment_date) + '</td>'
        + '<td>' + birthFmt + '</td>'
        + '<td>' + (c.return_date ? _fmtDate(c.return_date) : '<span style="color:var(--muted)">—</span>') + '</td>'
        + '<td><span class="return-badge ' + st.cls + '">' + st.label + '</span></td>'
        + '<td><span class="notes-cell" title="' + notesEsc + '">' + notesShort + '</span></td>'
        + '<td><div class="actions-cell">'
        + '<button class="action-btn edit-btn" onclick="openClientModal(' + c.id + ')"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button>'
        + '<button class="action-btn notify-btn"' + notifyDisabled + ' onclick="openNotifyModal(' + c.id + ')"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Notificar</button>'
        + '<button class="action-btn delete-btn" onclick="openClientDelModal(' + c.id + ',' + JSON.stringify((c.first_name||"")+" "+(c.last_name||"")).replace(/"/g,"&quot;") + ')"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/></svg> Excluir</button>'
        + '</div></td></tr>';
    }}).join("");
  }}

  /* Abre modal de add/edit */
  function openClientModal(id) {{
    const m = document.getElementById("modal-client");
    const titleEl = document.getElementById("client-modal-title");
    const idEl = document.getElementById("client-edit-id");
    document.getElementById("form-client").reset();
    document.getElementById("return-parse-hint").style.display = "none";
    if (id) {{
      const c = _clientsData.find(x => x.id === id);
      if (!c) return;
      if (titleEl) titleEl.textContent = "Editar Cliente";
      idEl.value = id;
      document.getElementById("client-first-name").value  = c.first_name || "";
      document.getElementById("client-last-name").value   = c.last_name  || "";
      const phone = (c.phone||"").replace("@s.whatsapp.net","").replace("@lid","");
      document.getElementById("client-phone").value       = phone;
      document.getElementById("client-apt-date").value    = c.last_appointment_date || "";
      document.getElementById("client-birth-date").value  = c.birth_date || "";
      document.getElementById("client-notes").value       = c.notes || "";
      document.getElementById("client-return-months").value = c.return_period_months || "";
      document.getElementById("client-return-date").value   = c.return_date || "";
    }} else {{
      if (titleEl) titleEl.textContent = "Novo Cliente";
      idEl.value = "";
    }}
    m.style.display = "block";
    if (!m._positioned) {{
      m.style.left = Math.max(0,(window.innerWidth-m.offsetWidth)/2) + "px";
      m.style.top  = Math.max(0,(window.innerHeight-m.offsetHeight)/2) + "px";
      m._positioned = true;
    }}
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }}

  function closeClientModal() {{
    document.getElementById("modal-client").style.display = "none";
    isPaused = false; secs = 30;
  }}

  /* Salvar (POST ou PUT) */
  async function submitClient(e) {{
    e.preventDefault();
    const btn = document.getElementById("btn-submit-client");
    btn.disabled = true; btn.textContent = "Salvando...";
    const editId = document.getElementById("client-edit-id").value;
    const body = {{
      first_name:            document.getElementById("client-first-name").value.trim(),
      last_name:             document.getElementById("client-last-name").value.trim(),
      phone:                 document.getElementById("client-phone").value.trim(),
      last_appointment_date: document.getElementById("client-apt-date").value || null,
      birth_date:            document.getElementById("client-birth-date").value || null,
      notes:                 document.getElementById("client-notes").value.trim(),
      return_period_months:  document.getElementById("client-return-months").value || null,
      return_date:           document.getElementById("client-return-date").value || null,
    }};
    try {{
      const url    = editId ? "/admin/clients/" + editId : "/admin/clients";
      const method = editId ? "PUT" : "POST";
      const r = await fetch(url, {{method, headers:authHeaders(), body:JSON.stringify(body)}});
      if (r.ok) {{ closeClientModal(); await loadClients(); showToast(editId ? "Cliente atualizado!" : "Cliente cadastrado!"); }}
      else {{ const d = await r.json().catch(()=>({{}})); showToast("Erro: " + (d.detail||"falha ao salvar"), false); }}
    }} catch(ex) {{ showToast("Erro: " + ex.message, false); }}
    btn.disabled = false; btn.textContent = "Salvar";
  }}

  /* Excluir */
  function openClientDelModal(id, name) {{
    _deletingClientId = id;
    const msg = document.getElementById("client-del-msg");
    if (msg) msg.textContent = 'Deseja excluir o cliente "' + name.trim() + '"? Esta acao nao pode ser desfeita.';
    document.getElementById("modal-confirm-client-del").classList.add("open");
    isPaused = true; document.getElementById("cd").textContent = "Pausado";
  }}
  function closeClientDelModal() {{
    document.getElementById("modal-confirm-client-del").classList.remove("open");
    _deletingClientId = null; isPaused = false; secs = 30;
  }}
  async function confirmDeleteClient() {{
    if (!_deletingClientId) return;
    const id = _deletingClientId;
    closeClientDelModal();
    const r = await fetch("/admin/clients/" + id, {{method:"DELETE",headers:authHeaders()}});
    if (r.ok) {{ await loadClients(); showToast("Cliente excluido."); }}
    else showToast("Erro ao excluir.", false);
  }}

  /* Exportar CSV */
  function exportClientsCSV() {{
    if (!_clientsData.length) {{ showToast("Nenhum cliente para exportar.", false); return; }}
    const cols = ["ID","Nome","Sobrenome","Telefone","Visitas","Ultima Consulta","Nasc.","Data Retorno","Status Retorno","Observacoes"];
    const rows = _clientsData.map(c => {{
      const st = clientReturnStatus(c.return_date);
      const phone = (c.phone||"").replace("@s.whatsapp.net","").replace("@lid","");
      const esc = v => '"' + String(v||"").replace(/"/g,'""') + '"';
      return [
        c.id,
        esc(c.first_name||""),
        esc(c.last_name||""),
        esc(phone),
        c.visit_count||0,
        esc(c.last_appointment_date||""),
        esc(c.birth_date||""),
        esc(c.return_date||""),
        esc(st.label),
        esc(c.notes||""),
      ].join(",");
    }});
    const csv = [cols.join(","), ...rows].join("\\n");
    const blob = new Blob(["﻿" + csv], {{type:"text/csv;charset=utf-8"}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "clientes_lenzótica_" + new Date().toISOString().split("T")[0] + ".csv";
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
    showToast("CSV exportado com " + _clientsData.length + " clientes!");
  }}

  /* Notificar retorno via WhatsApp */
  function openNotifyModal(id) {{
    _notifyingClientId = id;
    const c = _clientsData.find(x => x.id === id);
    const name = c ? (c.first_name + " " + (c.last_name||"")).trim() : "este cliente";
    const msg = document.getElementById("client-notify-msg");
    if (msg) msg.textContent = 'Enviar lembrete de retorno via WhatsApp para ' + name + '?';
    document.getElementById("modal-confirm-client-notify").classList.add("open");
    isPaused = true; document.getElementById("cd").textContent = "Pausado";
  }}
  function closeNotifyModal() {{
    document.getElementById("modal-confirm-client-notify").classList.remove("open");
    _notifyingClientId = null; isPaused = false; secs = 30;
  }}
  async function confirmNotifyClient() {{
    if (!_notifyingClientId) return;
    const id = _notifyingClientId;
    const c = _clientsData.find(x => x.id === id);
    const name = c ? (c.first_name + " " + (c.last_name||"")).trim() : "este cliente";
    closeNotifyModal();
    const r = await fetch("/admin/clients/" + id + "/notify-return", {{method:"POST",headers:authHeaders()}});
    if (r.ok) showToast("Lembrete enviado para " + name + "!");
    else {{ const d = await r.json().catch(()=>({{}})); showToast("Erro: " + (d.detail||"falha ao enviar"), false); }}
  }}

  /* Auto-calcular data de retorno a partir dos meses */
  function calcReturnDateFromMonths() {{
    const months = parseInt(document.getElementById("client-return-months").value);
    if (!months || months < 1) return;
    const aptDate = document.getElementById("client-apt-date").value;
    const base = aptDate ? new Date(aptDate + "T00:00:00") : new Date();
    base.setMonth(base.getMonth() + months);
    document.getElementById("client-return-date").value = base.toISOString().split("T")[0];
  }}

  function suggestReturnDate() {{
    // Recalcula retorno se ja tiver meses preenchido
    const months = parseInt(document.getElementById("client-return-months").value);
    if (months && months > 0) calcReturnDateFromMonths();
  }}

  /* Tenta parsear "retorno em X meses" nas observacoes */
  function parseReturnFromNotes() {{
    const notes = document.getElementById("client-notes").value.toLowerCase();
    const hint  = document.getElementById("return-parse-hint");
    const match = notes.match(/retorno\\s+em\\s+(\\d+)\\s*mes/);
    if (match) {{
      const months = parseInt(match[1]);
      const monthsEl = document.getElementById("client-return-months");
      if (!monthsEl.value) {{
        monthsEl.value = months;
        calcReturnDateFromMonths();
      }}
      if (hint) {{
        hint.style.display = "block";
        hint.textContent = "✓ Detectado: retorno em " + months + " meses — data sugerida.";
      }}
    }} else {{
      if (hint) hint.style.display = "none";
    }}
  }}

  /* Drag modal-client */
  (function(){{
    const m = document.getElementById("modal-client");
    const h = document.getElementById("modal-client-handle");
    if (!m || !h) return;
    let drag=false, ox=0, oy=0;
    h.addEventListener("mousedown", e => {{
      drag=true;
      const r=m.getBoundingClientRect(); ox=e.clientX-r.left; oy=e.clientY-r.top;
      document.body.style.userSelect="none";
    }});
    document.addEventListener("mousemove", e => {{
      if (!drag || m.style.display==="none") return;
      m.style.left = Math.max(0,Math.min(window.innerWidth-m.offsetWidth,  e.clientX-ox)) + "px";
      m.style.top  = Math.max(0,Math.min(window.innerHeight-m.offsetHeight, e.clientY-oy)) + "px";
    }});
    document.addEventListener("mouseup", () => {{ if(drag){{ drag=false; document.body.style.userSelect=""; }} }});
  }})();

  /* Drag modal-doc and modal-faq */
  (function(){{
    [["modal-doc","modal-doc-handle"],["modal-faq","modal-faq-handle"]].forEach(([mid,hid])=>{{
      const m=document.getElementById(mid),h=document.getElementById(hid);
      if(!m||!h)return;let drag=false,ox=0,oy=0;
      h.addEventListener("mousedown",e=>{{drag=true;const r=m.getBoundingClientRect();ox=e.clientX-r.left;oy=e.clientY-r.top;document.body.style.userSelect="none";}});
      document.addEventListener("mousemove",e=>{{if(!drag||m.style.display==="none")return;m.style.left=Math.max(0,Math.min(window.innerWidth-m.offsetWidth,e.clientX-ox))+"px";m.style.top=Math.max(0,Math.min(window.innerHeight-m.offsetHeight,e.clientY-oy))+"px";}});
      document.addEventListener("mouseup",()=>{{if(drag){{drag=false;document.body.style.userSelect="";}}}});
    }});
  }})();

  /* ── CHAT CLIENTE ──────────────────────────────────────────────────────────── */
  var _chatContacts = [];
  var _chatContactFilter = "all";
  var _currentChatPhone = null;
  var _chatPollTimer = null;
  var _chatLastMsgCount = 0;

  var _AVATAR_COLORS = ["#2563eb","#7c3aed","#db2777","#ea580c","#16a34a","#0891b2","#d97706","#dc2626","#0e7490","#4f46e5"];
  function _avatarColor(str) {{
    var h = 0;
    for (var i = 0; i < str.length; i++) h = str.charCodeAt(i) + ((h << 5) - h);
    return _AVATAR_COLORS[Math.abs(h) % _AVATAR_COLORS.length];
  }}
  function _avatarInitials(name) {{
    var parts = (name||"?").trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length-1][0]).toUpperCase();
    return (parts[0].slice(0,2)||"?").toUpperCase();
  }}
  function _chatRelTime(iso) {{
    if (!iso) return "";
    var d = new Date(iso), now = new Date(), diff = now - d;
    if (diff < 60000) return "agora";
    if (diff < 3600000) return Math.floor(diff/60000) + " min";
    if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString("pt-BR",{{hour:"2-digit",minute:"2-digit"}});
    var yd = new Date(now); yd.setDate(yd.getDate()-1);
    if (d.toDateString() === yd.toDateString()) return "ontem";
    return d.toLocaleDateString("pt-BR",{{day:"2-digit",month:"2-digit"}});
  }}
  function _chatDateLabel(iso) {{
    if (!iso) return "Sem data";
    var d = new Date(iso), now = new Date();
    if (d.toDateString() === now.toDateString()) return "Hoje";
    var yd = new Date(now); yd.setDate(yd.getDate()-1);
    if (d.toDateString() === yd.toDateString()) return "Ontem";
    return d.toLocaleDateString("pt-BR",{{day:"2-digit",month:"2-digit",year:"numeric"}});
  }}
  function _chatMsgTime(iso) {{
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString("pt-BR",{{hour:"2-digit",minute:"2-digit"}});
  }}
  function _escHtml(s) {{
    return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }}

  async function loadChatContacts() {{
    try {{
      var r = await fetch("/admin/chat/contacts", {{headers:authHeaders()}});
      if (!r.ok) return;
      _chatContacts = await r.json();
      renderChatContacts();
      // Atualiza badge de nao lidas no sidebar
      var total = _chatContacts.reduce(function(s,c){{ return s + (c.unread_count||0); }}, 0);
      var badge = document.getElementById("chat-unread-badge");
      if (badge) {{ badge.textContent = total; badge.style.display = total > 0 ? "inline-block" : "none"; }}
      // Se conversa aberta e ha novas mensagens, recarrega
      if (_currentChatPhone) {{
        var contact = _chatContacts.find(function(c){{ return c.phone === _currentChatPhone; }});
        if (contact && contact.unread_count > 0) {{
          await loadChatMessages(_currentChatPhone, false);
          await fetch("/admin/chat/read/" + encodeURIComponent(_currentChatPhone), {{method:"POST",headers:authHeaders()}});
          contact.unread_count = 0;
          renderChatContacts();
        }}
      }}
    }} catch(e) {{ /* silent */ }}
  }}

  function renderChatContacts() {{
    var q = ((document.getElementById("chat-search")||{{}}).value||"").toLowerCase();
    var cf = _chatContactFilter;
    var list = _chatContacts.filter(function(c) {{
      if (cf === "unread" && !c.unread_count) return false;
      if (cf === "ia-off" && c.ia_enabled !== false) return false;
      if (q && !c.name.toLowerCase().includes(q) && !c.display_phone.includes(q)) return false;
      return true;
    }});
    var el = document.getElementById("chat-contact-list");
    if (!el) return;
    if (!list.length) {{
      el.innerHTML = '<div class="chat-empty-contacts">Nenhum contato encontrado.</div>';
      return;
    }}
    el.innerHTML = list.map(function(c) {{
      var color    = _avatarColor(c.name);
      var initials = _avatarInitials(c.name);
      var active   = c.phone === _currentChatPhone ? "active" : "";
      var preview  = _escHtml((c.last_message_role === "user" ? "" : "🤖 ") + (c.last_message||""));
      var unreadHtml = c.unread_count > 0 ? '<span class="chat-unread-badge">' + c.unread_count + '</span>' : "";
      var iaDot    = c.ia_enabled === false ? '<span title="IA pausada" style="color:#ef4444;font-size:.7rem">⏸</span>' : "";
      return '<div class="chat-contact-item ' + active + '" onclick="openChat(\\'' + c.phone + '\\')" data-phone="' + _escHtml(c.phone) + '">' +
        '<div class="chat-avatar" style="background:' + color + '">' + initials + '</div>' +
        '<div class="chat-contact-info">' +
          '<div class="chat-contact-name">' + _escHtml(c.name) + ' ' + iaDot + '</div>' +
          '<div class="chat-contact-preview">' + preview + '</div>' +
        '</div>' +
        '<div class="chat-contact-meta">' +
          '<span class="chat-contact-time">' + _chatRelTime(c.last_message_at) + '</span>' +
          unreadHtml +
        '</div>' +
      '</div>';
    }}).join("");
  }}

  function filterChatContacts() {{ renderChatContacts(); }}
  function setChatContactFilter(btn) {{
    document.querySelectorAll(".chat-filter-btn").forEach(function(b){{ b.classList.remove("active"); }});
    btn.classList.add("active");
    _chatContactFilter = btn.dataset.cf;
    renderChatContacts();
  }}

  async function openChat(phone) {{
    _currentChatPhone = phone;
    _chatLastMsgCount = 0;
    // Marca contato como ativo na lista
    document.querySelectorAll(".chat-contact-item").forEach(function(el){{
      el.classList.toggle("active", el.dataset.phone === phone);
    }});
    // Exibe painel de conversa
    var emptyEl  = document.getElementById("chat-conv-empty");
    var activeEl = document.getElementById("chat-active-conv");
    if (emptyEl)  emptyEl.style.display  = "none";
    if (activeEl) activeEl.style.display = "flex";
    document.getElementById("chat-layout").classList.add("conv-open");
    // Preenche header
    var contact  = _chatContacts.find(function(c){{ return c.phone === phone; }});
    var name     = (contact && contact.name) || phone.replace("@s.whatsapp.net","").replace("@lid","");
    var color    = _avatarColor(name);
    var initials = _avatarInitials(name);
    var avatarEl = document.getElementById("conv-avatar");
    if (avatarEl) {{ avatarEl.textContent = initials; avatarEl.style.background = color; }}
    var nameEl   = document.getElementById("conv-name");
    var phoneEl  = document.getElementById("conv-phone");
    if (nameEl)  nameEl.textContent  = name;
    if (phoneEl) phoneEl.textContent = (contact && contact.display_phone) || "";
    // Atualiza badge IA
    var iaEnabled = !contact || contact.ia_enabled !== false;
    _updateIABadge(iaEnabled);
    // Carrega mensagens
    await loadChatMessages(phone, true);
    // Marca como lida
    await fetch("/admin/chat/read/" + encodeURIComponent(phone), {{method:"POST",headers:authHeaders()}});
    if (contact) {{ contact.unread_count = 0; renderChatContacts(); }}
    var inputEl = document.getElementById("chat-input");
    if (inputEl) inputEl.focus();
  }}

  function _updateIABadge(enabled) {{
    var badge = document.getElementById("conv-ia-badge");
    var label = document.getElementById("conv-ia-label");
    var btn   = document.getElementById("btn-ia-toggle");
    var warn  = document.getElementById("chat-ia-warning-bar");
    if (!badge) return;
    badge.className = "chat-ia-badge " + (enabled ? "chat-ia-on" : "chat-ia-off");
    if (label) label.textContent = enabled ? "IA ativa" : "IA pausada";
    if (btn)   {{ btn.className = "btn-ia-toggle " + (enabled ? "pause" : "resume"); btn.textContent = enabled ? "Pausar IA" : "Retomar IA"; }}
    if (warn)  warn.style.display = enabled ? "none" : "flex";
  }}

  async function loadChatMessages(phone, scroll) {{
    var area = document.getElementById("chat-messages-area");
    if (!area) return;
    var atBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 80;
    try {{
      var r = await fetch("/admin/chat/messages/" + encodeURIComponent(phone), {{headers:authHeaders()}});
      if (!r.ok) return;
      var msgs = await r.json();
      if (msgs.length === _chatLastMsgCount && !scroll) return;
      _chatLastMsgCount = msgs.length;
      area.innerHTML = _renderMsgBubbles(msgs);
      if (scroll || atBottom) area.scrollTop = area.scrollHeight;
    }} catch(e) {{ /* silent */ }}
  }}

  function _renderMsgBubbles(msgs) {{
    var html = "", lastDate = "";
    msgs.forEach(function(msg) {{
      var dl = _chatDateLabel(msg.created_at);
      if (dl !== lastDate) {{
        html += '<div class="chat-date-sep">' + _escHtml(dl) + '</div>';
        lastDate = dl;
      }}
      var isUser = msg.role === "user";
      var isOp   = msg.sent_by_operator;
      var cls    = isUser ? "received" : (isOp ? "operator" : "sent");
      var time   = _chatMsgTime(msg.created_at);
      var tick   = !isUser ? '<span class="chat-tick">&#10003;&#10003;</span>' : "";
      if (!isUser) {{
        var subCls  = isOp ? "chat-sub-label op" : "chat-sub-label";
        var subText = isOp ? "&#9997; Operador" : "&#129302; Liza";
        html += '<div class="' + subCls + '">' + subText + '</div>';
      }}
      html += '<div class="chat-bubble ' + cls + '">' +
        _escHtml(msg.content) +
        '<div class="chat-bubble-meta">' +
          '<span class="chat-bubble-time">' + time + '</span>' + tick +
        '</div>' +
      '</div>';
    }});
    return html || '<div style="text-align:center;color:var(--muted);font-size:.82rem;padding:2rem">Nenhuma mensagem ainda.</div>';
  }}

  async function sendChatMsg() {{
    var input = document.getElementById("chat-input");
    var text  = (input ? input.value : "").trim();
    if (!text || !_currentChatPhone) return;
    var btn   = document.getElementById("chat-send-btn");
    if (btn) btn.disabled = true;
    input.value = "";
    chatInputResize(input);
    try {{
      var r = await fetch("/admin/chat/send", {{
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({{phone: _currentChatPhone, text: text}})
      }});
      if (r.ok) {{
        await loadChatMessages(_currentChatPhone, true);
        await loadChatContacts();
      }} else {{
        showToast("Erro ao enviar mensagem.", false);
        input.value = text;
        chatInputResize(input);
      }}
    }} catch(e) {{
      showToast("Erro: " + e.message, false);
      input.value = text;
      chatInputResize(input);
    }}
    if (btn) btn.disabled = false;
    if (input) input.focus();
  }}

  async function toggleChatIA() {{
    if (!_currentChatPhone) return;
    var contact   = _chatContacts.find(function(c){{ return c.phone === _currentChatPhone; }});
    var newEnabled = !(contact && contact.ia_enabled !== false ? true : false);
    // Se contact.ia_enabled === false => estava desligado => newEnabled = true
    if (contact) newEnabled = !(contact.ia_enabled !== false);
    var r = await fetch("/admin/chat/ia-mode/" + encodeURIComponent(_currentChatPhone), {{
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({{ia_enabled: newEnabled}})
    }});
    if (r.ok) {{
      if (contact) contact.ia_enabled = newEnabled;
      _updateIABadge(newEnabled);
      renderChatContacts();
      showToast(newEnabled ? "IA retomada para este contato." : "IA pausada — voce esta no controle.");
    }} else showToast("Erro ao alterar modo da IA.", false);
  }}

  function chatKeydown(e) {{
    if (e.key === "Enter" && !e.shiftKey) {{ e.preventDefault(); sendChatMsg(); }}
  }}
  function chatInputResize(el) {{
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 130) + "px";
  }}

  function startChatPoll() {{
    stopChatPoll();
    _chatPollTimer = setInterval(loadChatContacts, 3000);
  }}
  function stopChatPoll() {{
    if (_chatPollTimer) {{ clearInterval(_chatPollTimer); _chatPollTimer = null; }}
  }}

  /* Init */
  (function(){{
    const lp=localStorage.getItem("lastPage")||"dashboard";navTo(lp);
    if(localStorage.getItem("sbCollapsed")==="1")document.getElementById("sidebar").classList.add("collapsed");
    renderStatusBreakdown();renderUpcoming();
  }})();
</script>
</body>
</html>"""
