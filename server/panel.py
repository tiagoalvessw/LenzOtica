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

    /* CONFIG SUB-TABS */
    .cfg-tabs{{display:flex;gap:.35rem;margin-bottom:1.25rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.35rem;box-shadow:var(--shadow-sm)}}
    .cfg-tab{{flex:1;padding:.52rem .75rem;border-radius:var(--radius-sm);font-size:.8rem;font-weight:600;font-family:inherit;cursor:pointer;border:none;background:none;color:var(--text2);transition:background .12s,color .12s;white-space:nowrap;text-align:center}}
    .cfg-tab:hover{{background:var(--surface2);color:var(--text)}}
    .cfg-tab.active{{background:var(--primary);color:#fff}}
    .cfg-pane{{display:none}}
    .cfg-pane.active{{display:block}}
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
      <span class="nav-label">Agente IA</span>
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
          <div class="page-title">Agente IA</div>
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

    <!-- CONFIGURACOES -->
    <section id="page-config" class="page">
      <div class="page-header">
        <div>
          <div class="page-title">Configuracoes</div>
          <div class="page-subtitle">Configure o agente IA e as informacoes da loja</div>
        </div>
      </div>

      <div class="cfg-tabs">
        <button class="cfg-tab active" data-tab="loja" onclick="switchCfgTab('loja')">Loja</button>
        <button class="cfg-tab" data-tab="identidade" onclick="switchCfgTab('identidade')">Identidade</button>
        <button class="cfg-tab" data-tab="horarios" onclick="switchCfgTab('horarios')">Horarios</button>
        <button class="cfg-tab" data-tab="faq" onclick="switchCfgTab('faq')">FAQ</button>
        <button class="cfg-tab" data-tab="conhecimento" onclick="switchCfgTab('conhecimento')">Conhecimento</button>
        <button class="cfg-tab" data-tab="avancado" onclick="switchCfgTab('avancado')">Avancado</button>
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
            <div><button class="btn-primary" onclick="saveBotConfig()">Salvar informacoes da loja</button></div>
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
            <div><button class="btn-primary" onclick="saveBotConfig()">Salvar identidade</button></div>
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
              <div id="bh-grid" class="bh-grid"><span style="font-size:.8rem;color:var(--muted)">Carregando...</span></div>
              <button class="btn-primary" style="width:fit-content;margin-top:.25rem" onclick="saveBusinessHours()">Salvar horarios</button>
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
        <div class="config-section">
          <div class="config-section-hdr rag-section-hdr">
            <span>Base de Conhecimento (RAG)</span>
            <label class="toggle-switch" title="Ativar/desativar RAG">
              <input type="checkbox" id="rag-enabled" onchange="saveRagEnabled()">
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
              <span style="font-size:.75rem;color:var(--text2)">Ativo</span>
            </label>
          </div>
          <div class="config-body">
            <div class="config-row" style="flex-direction:column;align-items:stretch;gap:.75rem;border-bottom:1px solid var(--border);padding-bottom:1rem">
              <p class="bcf-hint" style="padding-top:.35rem">Adicione documentos para a IA consultar durante as conversas. Ideal para politicas, catalogo de produtos, scripts de atendimento, etc.</p>
              <div style="display:flex;align-items:center;justify-content:space-between">
                <span style="font-size:.84rem;font-weight:600">Documentos</span>
                <button class="btn-new" onclick="openDocModal()">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  Adicionar Documento
                </button>
              </div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Titulo</th><th>Tipo</th><th>Chunks</th><th>Status</th><th>Acoes</th></tr></thead>
                  <tbody id="doc-tbody"><tr><td colspan="5" class="empty-row"><div class="empty-state">Carregando...</div></td></tr></tbody>
                </table>
              </div>
            </div>
            <div class="config-row" style="flex-direction:column;align-items:stretch;gap:.5rem;padding-top:.75rem">
              <span style="font-size:.82rem;font-weight:600;color:var(--text)">Log de Consultas RAG</span>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Telefone</th><th>Query</th><th>Chunks</th><th>Similaridade</th><th>Latencia</th><th>Quando</th></tr></thead>
                  <tbody id="rag-log-tbody"><tr><td colspan="6" class="empty-row"><div class="empty-state">Carregando...</div></td></tr></tbody>
                </table>
              </div>
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
                <button class="btn-primary" style="width:fit-content" onclick="saveRagConfig()">Salvar parametros</button>
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
              <button class="btn-primary" style="width:fit-content" onclick="savePrompt()">Salvar prompt direto</button>
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

<script>
  const ADMIN_TOKEN = "{admin_token}";
  const PENDING_ITEMS = {pending_json};
  function authHeaders() {{ return {{"Content-Type":"application/json","X-Admin-Token":ADMIN_TOKEN}}; }}

  /* Navigation */
  const PAGE_TITLES = {{dashboard:"Dashboard",agendamentos:"Agendamentos",ia:"Agente IA",config:"Configuracoes"}};
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

  function switchCfgTab(tab) {{
    document.querySelectorAll(".cfg-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".cfg-pane").forEach(p => p.classList.remove("active"));
    const bt = document.querySelector('.cfg-tab[data-tab="'+tab+'"]');
    const pn = document.getElementById("cfg-pane-"+tab);
    if (bt) bt.classList.add("active");
    if (pn) pn.classList.add("active");
    localStorage.setItem("cfgTab", tab);
  }}

  async function loadConfigPage() {{
    const saved = localStorage.getItem("cfgTab") || "loja";
    switchCfgTab(saved);
    await Promise.all([loadBotConfig(), loadBusinessHours(), loadFaqItems(), loadRagConfig(), loadRagDocs(), loadRagLogs(), loadSystemPrompt()]);
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
    }} catch(e) {{ console.error("loadBotConfig", e); }}
  }}

  async function saveBotConfig() {{
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
    const r = await fetch("/admin/bot-config", {{method:"POST",headers:authHeaders(),body:JSON.stringify(body)}});
    if (r.ok) {{ showToast("Configuracoes salvas e prompt atualizado!"); loadSystemPrompt(); }}
    else showToast("Erro ao salvar.", false);
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

  async function saveBusinessHours() {{
    const rows = [];
    [0,1,2,3,4,5,6].forEach(day => {{
      const isOpen = document.querySelector('.bh-open[data-day="'+day+'"]')?.checked || false;
      const isFlex = document.querySelector('.bh-flex[data-day="'+day+'"]')?.checked || false;
      const ot = document.querySelector('.bh-ot[data-day="'+day+'"]')?.value || null;
      const ct = document.querySelector('.bh-ct[data-day="'+day+'"]')?.value || null;
      rows.push({{day_of_week:day, is_open:isOpen, is_flexible:isFlex, open_time:ot||null, close_time:ct||null}});
    }});
    const r = await fetch("/admin/business-hours", {{method:"POST",headers:authHeaders(),body:JSON.stringify(rows)}});
    showToast(r.ok ? "Horarios salvos!" : "Erro ao salvar.", r.ok);
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

  async function savePrompt() {{
    const prompt = document.getElementById("system-prompt-ta").value;
    const r = await fetch("/admin/system-prompt", {{method:"POST",headers:authHeaders(),body:JSON.stringify({{prompt}})}});
    showToast(r.ok ? "Prompt salvo!" : "Erro ao salvar.", r.ok);
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

  async function saveRagConfig() {{
    const cfg = {{
      top_k: parseInt(document.getElementById("rag-top-k").value),
      min_similarity: parseFloat(document.getElementById("rag-min-sim").value),
      max_context_tokens: parseInt(document.getElementById("rag-max-ctx").value),
      chunk_size: parseInt(document.getElementById("rag-chunk-size").value),
      chunk_overlap: parseInt(document.getElementById("rag-chunk-overlap").value),
    }};
    const r = await fetch("/admin/rag/config", {{method:"POST",headers:authHeaders(),body:JSON.stringify(cfg)}});
    showToast(r.ok ? "Parametros salvos!" : "Erro ao salvar.", r.ok);
  }}

  /* RAG Documents */
  async function loadRagDocs() {{
    try {{
      const r = await fetch("/admin/rag/documents", {{headers:{{"X-Admin-Token":ADMIN_TOKEN}}}});
      if (!r.ok) return;
      const docs = await r.json();
      const tbody = document.getElementById("doc-tbody");
      if (!tbody) return;
      if (!docs.length) {{
        tbody.innerHTML = '<tr><td colspan="5" class="empty-row"><div class="empty-state">Nenhum documento. Adicione um para comecar.</div></td></tr>';
        return;
      }}
      tbody.innerHTML = docs.map(d => {{
        const title = (d.title || "").replace(/</g,"&lt;");
        const lbl = TYPE_LABELS[d.source_type] || d.source_type;
        const badge = d.is_active
          ? '<span class="config-badge ok">&#10003; Ativo</span>'
          : '<span class="config-badge err">&#10007; Inativo</span>';
        const toggleBtn = d.is_active
          ? '<button class="action-btn cancel-btn" onclick="toggleDoc(' + d.id + ',false)">Desativar</button>'
          : '<button class="action-btn confirm-btn" onclick="toggleDoc(' + d.id + ',true)">Ativar</button>';
        return '<tr>'
          + '<td>' + title + '</td><td>' + lbl + '</td>'
          + '<td>' + (d.chunk_count || 0) + '</td>'
          + '<td>' + badge + '</td>'
          + '<td><div class="actions-cell">' + toggleBtn
          + '<button class="action-btn close-protocol-btn" onclick="deleteDoc(' + d.id + ')">Excluir</button>'
          + '</div></td></tr>';
      }}).join("");
    }} catch(e) {{ console.error("loadRagDocs", e); }}
  }}

  async function toggleDoc(id, newState) {{
    const r = await fetch("/admin/rag/documents/" + id + "/toggle", {{method:"PATCH",headers:authHeaders(),body:JSON.stringify({{is_active:newState}})}});
    if (r.ok) {{ loadRagDocs(); showToast("Documento atualizado!"); }}
    else showToast("Erro.", false);
  }}

  async function deleteDoc(id) {{
    if (!confirm("Excluir este documento e todos os seus chunks?")) return;
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
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row"><div class="empty-state">Nenhuma consulta RAG registrada.</div></td></tr>';
        return;
      }}
      tbody.innerHTML = logs.map(l => {{
        const phone = (l.phone || "").replace("@s.whatsapp.net","").replace("@lid","");
        const dt = new Date(l.created_at);
        const dtBr = isNaN(dt.getTime()) ? (l.created_at || "") : dt.toLocaleString("pt-BR");
        const sim = (l.top_similarity !== null && l.top_similarity !== undefined) ? (l.top_similarity * 100).toFixed(1) + "%" : "&#8212;";
        const lat = l.latency_ms ? l.latency_ms + "ms" : "&#8212;";
        const query = (l.query_text || "").replace(/</g,"&lt;").substring(0, 60);
        return '<tr>'
          + '<td><span class="phone-num">' + phone + '</span></td>'
          + '<td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + (l.query_text||"").replace(/"/g,"&quot;") + '">' + query + '</td>'
          + '<td>' + l.chunks_returned + '</td><td>' + sim + '</td><td>' + lat + '</td><td>' + dtBr + '</td>'
          + '</tr>';
      }}).join("");
    }} catch(e) {{ console.error("loadRagLogs", e); }}
  }}

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

  /* Init */
  (function(){{
    const lp=localStorage.getItem("lastPage")||"dashboard";navTo(lp);
    if(localStorage.getItem("sbCollapsed")==="1")document.getElementById("sidebar").classList.add("collapsed");
    renderStatusBreakdown();renderUpcoming();
  }})();
</script>
</body>
</html>"""
