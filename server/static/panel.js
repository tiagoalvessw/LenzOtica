  function authHeaders() { return {"Content-Type":"application/json","X-Admin-Token":ADMIN_TOKEN}; }

  /* Navigation */
  const PAGE_TITLES = {dashboard:"Dashboard",agendamentos:"Agendamentos",ia:"Fale com a Liza",clientes:"Clientes",chat:"Chat Cliente",config:"Configuracoes"};
  function navTo(page) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    const pe = document.getElementById("page-"+page);
    const ne = document.querySelector('.nav-item[data-page="'+page+'"]');
    if (pe) pe.classList.add("active");
    if (ne) ne.classList.add("active");
    document.getElementById("header-title").textContent = PAGE_TITLES[page]||page;
    localStorage.setItem("lastPage", page);
    if (window.innerWidth <= 768) closeMobileSidebar();
    isPaused = false;
    secs = 30;
    if (page === "config") loadConfigPage();
    if (page === "clientes") loadClients();
    if (page === "agendamentos") { applyFilter(); initAgendWidgets(); }
    if (page === "chat") { loadChatContacts(); loadGlobalIAStatus(); startChatPoll(); } else { stopChatPoll(); }
    const _fab = document.getElementById("fab-new");
    if (_fab) _fab.style.display = (page === "agendamentos" && window.innerWidth <= 768) ? "flex" : "none";
    // Ajusta overflow do main para o chat (layout fixo)
    const mainEl = document.querySelector("main");
    if (mainEl) mainEl.style.overflow = page === "chat" ? "hidden" : "";
  }
  function toggleSidebar() {
    const sb = document.getElementById("sidebar");
    const backdrop = document.getElementById("sb-backdrop");
    if (window.innerWidth <= 768) {
      const isOpen = sb.classList.toggle("mobile-open");
      if (backdrop) backdrop.classList.toggle("open", isOpen);
    } else {
      sb.classList.toggle("collapsed");
      localStorage.setItem("sbCollapsed", sb.classList.contains("collapsed") ? "1" : "0");
    }
  }
  function closeMobileSidebar() {
    const sb = document.getElementById("sidebar");
    const backdrop = document.getElementById("sb-backdrop");
    sb.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("open");
  }

  /* Dashboard widgets */
  function renderStatusBreakdown() {
    const data = [
      {label:"Confirmado",count:_PANEL_DATA.confirmados,color:"#059669"},
      {label:"Cancelado", count:_PANEL_DATA.cancelados, color:"#dc2626"},
      {label:"Concluido", count:_PANEL_DATA.concluidos, color:"#0891b2"},
      {label:"Hoje",      count:_PANEL_DATA.hoje, color:"#2563eb"},
      {label:"Pendente",  count:_PANEL_DATA.pendente,   color:"#d97706"},
    ];
    const mx = Math.max(...data.map(d=>d.count),1);
    const el = document.getElementById("status-breakdown");
    if (!el) return;
    el.innerHTML = data.map(d => {
      const pct = Math.round(d.count/mx*100);
      return '<div class="status-row"><span class="sr-label">'+d.label+'</span><div class="sr-bar"><div class="sr-fill" style="width:'+pct+'%;background:'+d.color+'"></div></div><span class="sr-count">'+d.count+'</span></div>';
    }).join("");
  }
  function renderUpcoming() {
    const SC = {scheduled:"#d97706",day_reminder_sent:"#2563eb",reminder_sent:"#7c3aed",response_received:"#7c3aed",confirmed:"#059669",attended:"#0f766e"};
    const SL = {scheduled:"Aguardando",day_reminder_sent:"Lembrete 1d",reminder_sent:"Lembrete 1h",response_received:"Respondeu",confirmed:"Confirmado",attended:"Compareceu"};
    const SK = {confirmed:"act-st-confirmed",attended:"act-st-confirmed",reminder_sent:"act-st-reminder",response_received:"act-st-reminder",scheduled:"act-st-scheduled",day_reminder_sent:"act-st-scheduled"};
    const rows = Array.from(document.querySelectorAll("#tbody tr[data-status]"))
      .filter(r => !["cancelled","no_show","completed"].includes(r.dataset.status))
      .sort((a,b) => (a.dataset.date+a.dataset.time).localeCompare(b.dataset.date+b.dataset.time))
      .slice(0,6);
    const el = document.getElementById("upcoming-list");
    if (!el) return;
    if (!rows.length) {
      el.innerHTML = '<div class="upcoming-empty">Nenhum agendamento pendente.</div>';
      return;
    }
    el.innerHTML = rows.map(r => {
      const color = SC[r.dataset.status]||"#94a3b8";
      const stLbl = SL[r.dataset.status]||r.dataset.status;
      const stCls = SK[r.dataset.status]||"act-st-scheduled";
      const name  = r.querySelector(".client-name")?.textContent||"—";
      const phone = r.querySelector(".phone-num")?.textContent||"—";
      const dp    = r.dataset.date?r.dataset.date.split("-"):[];
      const ds    = dp.length===3?dp[2]+"/"+dp[1]+"/"+dp[0]:r.dataset.date;
      return '<div class="activity-item" onclick="navToTab(\'agendamentos\',\'day\')">'
        +'<div class="act-dot" style="background:'+color+'"></div>'
        +'<div class="act-info"><div class="act-name">'+name+'</div><div class="act-detail">'+phone+'</div></div>'
        +'<span class="act-status '+stCls+'">'+stLbl+'</span>'
        +'<div class="act-time">'+ds+' '+r.dataset.time+'</div>'
        +'</div>';
    }).join("");
  }

  /* Toast */
  function showToast(msg, ok=true) {
    const t = document.createElement("div");
    t.className = "toast "+(ok?"toast-ok":"toast-err");
    t.innerHTML = (ok?'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>':'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>')+msg;
    document.body.appendChild(t);
    setTimeout(()=>t.remove(),3200);
  }

  /* Confirm cancel */
  let _pendingCancelBtn=null;
  function openConfirmCancel(btn){_pendingCancelBtn=btn;document.getElementById("modal-confirm").classList.add("open");isPaused=true;document.getElementById("cd").textContent="Pausado";}
  function closeConfirmModal(){document.getElementById("modal-confirm").classList.remove("open");_pendingCancelBtn=null;isPaused=false;secs=30;}
  async function confirmDoCancel(){
    const btn=_pendingCancelBtn;closeConfirmModal();if(!btn)return;
    const row=btn.closest("tr");btn.disabled=true;
    const res=await fetch("/admin/cancel",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time})});
    if(res.ok){
      row.dataset.status="cancelled";
      row.querySelector(".badge").className="badge cancelled";row.querySelector(".badge").textContent="Cancelado";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn recover-btn" onclick="recoverApt(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar</button><button class="action-btn close-protocol-btn" onclick="openConfirmCloseProtocol(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg> Encerrar Protocolo</button>';
      row.classList.remove("row-today");showToast("Agendamento cancelado.");applyFilter();
    } else {btn.disabled=false;showToast("Erro ao cancelar.",false);}
  }

  /* Recover */
  async function recoverApt(btn){
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Recuperando...";
    const res=await fetch("/admin/recover",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time})});
    if(res.ok){
      row.dataset.status="scheduled";row.querySelector(".badge").className="badge scheduled";row.querySelector(".badge").textContent="Aguardando";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn remind-btn" onclick="sendRemind(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button><button class="action-btn edit-btn" onclick="openEditModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button><button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>';
      showToast("Agendamento recuperado!");applyFilter();
    } else {btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Recuperar';showToast("Erro ao recuperar.",false);}
  }

  /* Edit modal */
  function openEditModal(btn){
    const row=btn.closest("tr");
    document.getElementById("edit-name").value=row.dataset.name;
    document.getElementById("edit-phone").value=row.dataset.phone.replace("@s.whatsapp.net","").replace("@lid","");
    document.getElementById("edit-date").value=row.dataset.date;
    document.getElementById("edit-time").value=row.dataset.time;
    const m=document.getElementById("modal-edit");
    m.dataset.oldPhone=row.dataset.phone;m.dataset.oldDate=row.dataset.date;m.dataset.oldTime=row.dataset.time;m._rowRef=row;
    m.style.display="block";
    if(!m._positioned){m.style.left=Math.max(0,(window.innerWidth-m.offsetWidth)/2)+"px";m.style.top=Math.max(0,(window.innerHeight-m.offsetHeight)/2)+"px";m._positioned=true;}
    isPaused=true;document.getElementById("cd").textContent="Pausado";
  }
  function closeEditModal(){document.getElementById("modal-edit").style.display="none";isPaused=false;secs=30;}
  async function submitEdit(e){
    e.preventDefault();const btn=document.getElementById("btn-submit-edit");btn.disabled=true;btn.textContent="Salvando...";
    const m=document.getElementById("modal-edit");
    const res=await fetch("/admin/edit",{method:"POST",headers:authHeaders(),body:JSON.stringify({old_phone:m.dataset.oldPhone,old_date:m.dataset.oldDate,old_time:m.dataset.oldTime,name:document.getElementById("edit-name").value.trim(),phone:document.getElementById("edit-phone").value.trim(),date:document.getElementById("edit-date").value,time:document.getElementById("edit-time").value,notify:document.getElementById("edit-notify").checked})});
    if(res.ok){closeEditModal();showToast("Agendamento atualizado!");setTimeout(()=>location.reload(),1200);}
    else{btn.disabled=false;btn.textContent="Salvar alteracoes";showToast("Erro ao atualizar.",false);}
  }

  /* Remind */
  async function sendRemind(btn){
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Enviando...";
    const res=await fetch("/admin/remind",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time})});
    if(res.ok){row.dataset.status="reminder_sent";row.querySelector(".badge").className="badge reminder_sent";row.querySelector(".badge").textContent="Lembrete 1h";btn.remove();showToast("Lembrete enviado!");}
    else{btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete';showToast("Erro ao enviar lembrete.",false);}
  }

  /* New appointment modal */
  function openModal(){
    document.getElementById("form-new").reset();
    const m=document.getElementById("modal-new");m.style.display="block";
    if(!m._positioned){m.style.left=Math.max(0,(window.innerWidth-m.offsetWidth)/2)+"px";m.style.top=Math.max(0,(window.innerHeight-m.offsetHeight)/2)+"px";m._positioned=true;}
    isPaused=true;document.getElementById("cd").textContent="Pausado";
  }
  function closeModal(){document.getElementById("modal-new").style.display="none";isPaused=false;secs=30;}
  async function submitNew(e){
    e.preventDefault();const btn=document.getElementById("btn-submit-new");btn.disabled=true;btn.textContent="Salvando...";
    const res=await fetch("/admin/appointments",{method:"POST",headers:authHeaders(),body:JSON.stringify({name:document.getElementById("new-name").value.trim(),phone:document.getElementById("new-phone").value.trim(),date:document.getElementById("new-date").value,time:document.getElementById("new-time").value,notify:document.getElementById("new-notify").checked})});
    if(res.ok){closeModal();showToast("Agendamento criado!");setTimeout(()=>location.reload(),1200);}
    else{btn.disabled=false;btn.textContent="Confirmar agendamento";showToast("Erro ao criar agendamento.",false);}
  }

  /* Tabs & filter */
  const FILTERS = {
    day:       row => row.dataset.date===TODAY_STR && !["cancelled","no_show","completed"].includes(row.dataset.status),
    confirmed: row => ["confirmed","attended"].includes(row.dataset.status),
    cancelled: row => ["cancelled","no_show"].includes(row.dataset.status),
    completed: row => row.dataset.status==="completed",
    all:       ()  => true,
  };
  let cur="day";
  function setTab(el){
    document.querySelectorAll(".tab-nav .tab").forEach(t=>t.classList.remove("active"));
    el.classList.add("active");cur=el.dataset.f;
    const ip=cur==="pending";
    document.getElementById("main-panel").style.display=ip?"none":"";
    document.getElementById("pending-section").style.display=ip?"":"none";
    if(ip)renderPending();else applyFilter();
  }
  /* ── Paginação ─────────────────────────────────────────────────────────── */
  const PAGE_SIZE = 25;
  let _pgCur = 1;
  let _pgVisible = [];   // linhas que passaram pelos filtros (referências aos <tr>)

  function onDateFilterChange(){
    const from=document.getElementById("filter-date-from").value;
    const to=document.getElementById("filter-date-to").value;
    const btn=document.getElementById("btn-clear-dates");
    if(from||to)btn.classList.add("visible"); else btn.classList.remove("visible");
    applyFilter();
  }
  function clearDateFilter(){
    document.getElementById("filter-date-from").value="";
    document.getElementById("filter-date-to").value="";
    document.getElementById("btn-clear-dates").classList.remove("visible");
    applyFilter();
  }

  function applyFilter(){
    if(cur==="pending")return;
    const q=document.getElementById("search").value.toLowerCase();
    const from=document.getElementById("filter-date-from").value;
    const to=document.getElementById("filter-date-to").value;
    const fn=FILTERS[cur]||(()=>true);
    _pgVisible=[];
    document.querySelectorAll("#tbody tr[data-status]").forEach(row=>{
      const d=row.dataset.date||"";
      const dateOk=(!from||d>=from)&&(!to||d<=to);
      if(fn(row)&&dateOk&&(!q||row.textContent.toLowerCase().includes(q))){
        _pgVisible.push(row);
      }
      row.style.display="none";
    });
    _applyApptSortInternal();
    goPage(1);
    updateNextApptBanner();
    updateAgendKPIs();
  }

  function goPage(p){
    const total=_pgVisible.length;
    const pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
    _pgCur=Math.min(Math.max(p,1),pages);
    const start=(_pgCur-1)*PAGE_SIZE;
    const end=start+PAGE_SIZE;
    _pgVisible.forEach((row,i)=>{ row.style.display=(i>=start&&i<end)?"":"none"; });
    _renderPagination(total,pages);
    renderMobileCards(start,end);
  }

  function _renderPagination(total,pages){
    const info=document.getElementById("pg-info");
    const btns=document.getElementById("pg-btns");
    if(total===0){ info.textContent="Nenhum registro encontrado"; btns.innerHTML=""; return; }
    const start=(_pgCur-1)*PAGE_SIZE+1;
    const end=Math.min(_pgCur*PAGE_SIZE,total);
    info.textContent=`Exibindo ${start}–${end} de ${total} • Pág ${_pgCur}/${pages}`;
    let html="";
    html+=`<button class="pg-btn" onclick="goPage(${_pgCur-1})" ${_pgCur===1?"disabled":""}>&#8249;</button>`;
    const WINDOW=2;
    for(let i=1;i<=pages;i++){
      if(i===1||i===pages||Math.abs(i-_pgCur)<=WINDOW){
        html+=`<button class="pg-btn${i===_pgCur?" active":""}" onclick="goPage(${i})">${i}</button>`;
      } else if(Math.abs(i-_pgCur)===WINDOW+1){
        html+=`<span style="color:var(--muted);padding:0 .2rem">…</span>`;
      }
    }
    html+=`<button class="pg-btn" onclick="goPage(${_pgCur+1})" ${_pgCur===pages?"disabled":""}>&#8250;</button>`;
    if(pages>1) html+=`<input class="pg-jump-input" type="number" min="1" max="${pages}" value="${_pgCur}" title="Ir para página" onchange="goPage(parseInt(this.value)||1)" style="margin-left:.35rem">`;
    btns.innerHTML=html;
  }

  /* Theme */
  const MOON='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  const SUN='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  function applyTheme(dark){document.documentElement.setAttribute("data-theme",dark?"dark":"light");document.getElementById("theme-icon").innerHTML=dark?SUN:MOON;}
  function toggleTheme(){const dark=document.documentElement.getAttribute("data-theme")!=="dark";localStorage.setItem("theme",dark?"dark":"light");applyTheme(dark);}
  applyTheme(localStorage.getItem("theme")==="dark");

  /* Auto-refresh */
  let secs=30,isPaused=true,lastActivity=0;
  const IDLE_MS=15000;
  ["mousemove","mousedown","keydown","scroll","touchstart"].forEach(ev=>document.addEventListener(ev,()=>{lastActivity=Date.now();},{passive:true}));
  function tick(){document.getElementById("ts").textContent="Atualizado "+new Date().toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});}
  function countdown(){
    if(isPaused)return;
    if((Date.now()-lastActivity)<IDLE_MS){secs=30;document.getElementById("cd").textContent="Pausado";return;}
    document.getElementById("cd").textContent=secs>0?"Atualiza em "+secs+"s":"Atualizando...";
    if(--secs<0)location.reload();
  }
  tick();setInterval(countdown,1000);

  /* Mark attended */
  async function markAttended(btn){
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Salvando...";
    const res=await fetch("/admin/attended",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time})});
    if(res.ok){
      row.dataset.status="attended";row.querySelector(".badge").className="badge attended";row.querySelector(".badge").textContent="Compareceu";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn confirm-btn" onclick="openCompleteModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Concluir</button>';
      showToast("Comparecimento registrado!");applyFilter();
    } else {btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="23 11 20 14 18 12"/></svg> Compareceu';showToast("Erro.",false);}
  }

  /* Complete modal */
  let _completeRow=null;
  function openCompleteModal(btn){
    _completeRow=btn.closest("tr");document.getElementById("complete-notes").value="";
    const m=document.getElementById("modal-complete");m.style.display="block";
    if(!m._positioned){m.style.left=Math.max(0,(window.innerWidth-m.offsetWidth)/2)+"px";m.style.top=Math.max(0,(window.innerHeight-m.offsetHeight)/2)+"px";m._positioned=true;}
    isPaused=true;document.getElementById("cd").textContent="Pausado";
  }
  function closeCompleteModal(){document.getElementById("modal-complete").style.display="none";isPaused=false;secs=30;_completeRow=null;}
  async function submitComplete(e){
    e.preventDefault();if(!_completeRow)return;
    const targetRow=_completeRow;const btn=document.getElementById("btn-submit-complete");
    const notes=document.getElementById("complete-notes").value;
    btn.disabled=true;btn.textContent="Encerrando...";
    try{
      const r1=await fetch("/admin/completed",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:targetRow.dataset.phone,date:targetRow.dataset.date,time:targetRow.dataset.time,notes:notes})});
      if(!r1.ok)throw new Error();
      await fetch("/admin/close_protocol",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:targetRow.dataset.phone,date:targetRow.dataset.date,time:targetRow.dataset.time})});
      closeCompleteModal();targetRow.remove();showToast("Atendimento encerrado!");
    }catch(_){btn.disabled=false;btn.textContent="Encerrar";showToast("Erro ao encerrar.",false);}
  }

  /* Close protocol */
  let _pendingCloseProtocolBtn=null;
  function openConfirmCloseProtocol(btn){_pendingCloseProtocolBtn=btn;document.getElementById("modal-confirm-protocol").classList.add("open");isPaused=true;document.getElementById("cd").textContent="Pausado";}
  function closeConfirmProtocolModal(){document.getElementById("modal-confirm-protocol").classList.remove("open");_pendingCloseProtocolBtn=null;isPaused=false;secs=30;}
  async function confirmDoCloseProtocol(){
    const btn=_pendingCloseProtocolBtn;closeConfirmProtocolModal();if(!btn)return;
    const row=btn.closest("tr");btn.disabled=true;
    const res=await fetch("/admin/close_protocol",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time})});
    if(res.ok){row.remove();showToast("Protocolo encerrado.");}
    else{btn.disabled=false;showToast("Erro ao encerrar protocolo.",false);}
  }

  /* Reschedule no-show */
  async function rescheduleApt(btn){
    const row=btn.closest("tr");btn.disabled=true;btn.innerHTML="Remarcando...";
    const res=await fetch("/admin/reschedule",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone:row.dataset.phone,date:row.dataset.date,time:row.dataset.time})});
    if(res.ok){
      row.dataset.status="scheduled";row.querySelector(".badge").className="badge scheduled";row.querySelector(".badge").textContent="Aguardando";
      row.querySelector(".actions-cell").innerHTML='<button class="action-btn remind-btn" onclick="sendRemind(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Lembrete</button><button class="action-btn edit-btn" onclick="openEditModal(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button><button class="action-btn cancel-btn" onclick="openConfirmCancel(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Cancelar</button>';
      showToast("Agendamento reaberto!");applyFilter();
    } else {btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> Remarcar';showToast("Erro ao remarcar.",false);}
  }

  /* Reset session */
  async function _doResetSession(phone,name,btn,lbl){
    btn.disabled=true;btn.innerHTML="Resetando...";
    const res=await fetch("/admin/reset_session",{method:"POST",headers:authHeaders(),body:JSON.stringify({phone})});
    if(res.ok)showToast("Historico da IA resetado para "+name+".");
    else showToast("Erro ao resetar.",false);
    btn.disabled=false;btn.innerHTML=lbl;
  }
  const RESET_LBL='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Resetar IA';
  async function resetSession(btn){
    const row=btn.closest("tr");const name=row.dataset.name||"este contato";
    if(!confirm("Resetar o historico da IA para "+name+"?\\n\\nA proxima mensagem sera tratada como nova conversa."))return;
    await _doResetSession(row.dataset.phone,name,btn,RESET_LBL);
  }
  async function resetSessionByPhone(phone,name,btn){
    if(!confirm("Resetar o historico da IA para "+name+"?\\n\\nA proxima mensagem sera tratada como nova conversa."))return;
    await _doResetSession(phone,name,btn,RESET_LBL);
  }

  /* Pending */
  function renderPending(){
    const tbody=document.getElementById("pending-tbody");
    if(!PENDING_ITEMS.length){tbody.innerHTML='<tr><td colspan="4" class="empty-row"><div class="empty-state"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:.3;margin-bottom:.75rem"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><div>Nenhuma pendencia no momento.</div></div></td></tr>';return;}
    tbody.innerHTML=PENDING_ITEMS.map(p=>{
      const phone=(p.phone||"").replace("@s.whatsapp.net","").replace("@lid","");
      const dt=new Date(p.created_at);
      const dtBr=isNaN(dt.getTime())?(p.created_at||""):dt.toLocaleString("pt-BR");
      const note=(p.note||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      return '<tr><td><span class="phone-num">'+phone+'</span></td><td>'+note+'</td><td>'+dtBr+'</td><td><div class="actions-cell"><button class="action-btn reset-session-btn" onclick="resetSessionByPhone('+JSON.stringify(p.phone)+','+JSON.stringify(phone)+',this)">'+RESET_LBL+'</button><button class="action-btn confirm-btn" onclick="concludePending(this)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Encerrar</button></div></td></tr>';
    }).join("");
  }
  async function concludePending(btn){
    const rows=document.querySelectorAll("#pending-tbody tr");const row=btn.closest("tr");
    let idx=-1;rows.forEach((r,i)=>{if(r===row)idx=i;});
    if(idx<0||idx>=PENDING_ITEMS.length)return;
    const item=PENDING_ITEMS[idx];btn.disabled=true;btn.innerHTML="Concluindo...";
    const res=await fetch("/admin/pending/dismiss",{method:"POST",headers:authHeaders(),body:JSON.stringify({id:item.id})});
    if(res.ok){PENDING_ITEMS.splice(idx,1);renderPending();showToast("Pendencia concluida.");}
    else{btn.disabled=false;btn.innerHTML='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Encerrar';showToast("Erro ao concluir.",false);}
  }

  let _pendingDismissId=null,_pendingDismissBtn=null;
  function dismissPending(id,btn){_pendingDismissId=id;_pendingDismissBtn=btn;document.getElementById("modal-confirm-dismiss").classList.add("open");isPaused=true;document.getElementById("cd").textContent="Pausado";}
  function closeConfirmDismissModal(){document.getElementById("modal-confirm-dismiss").classList.remove("open");_pendingDismissId=null;_pendingDismissBtn=null;isPaused=false;secs=30;}
  async function confirmDoDismiss(){
    const id=_pendingDismissId;const btn=_pendingDismissBtn;closeConfirmDismissModal();if(!id)return;
    btn.disabled=true;btn.textContent="Descartando...";
    const res=await fetch("/admin/pending/dismiss",{method:"POST",headers:authHeaders(),body:JSON.stringify({id})});
    if(res.ok){btn.closest("tr").remove();const idx=PENDING_ITEMS.findIndex(p=>p.id===id);if(idx>=0)PENDING_ITEMS.splice(idx,1);showToast("Aviso descartado.");}
    else{btn.disabled=false;btn.textContent="Descartar";showToast("Erro ao descartar.",false);}
  }

  /* Drag modals */
  (function(){
    [["modal-new","modal-handle"],["modal-complete","modal-complete-handle"],["modal-edit","modal-edit-handle"]].forEach(([mid,hid])=>{
      const m=document.getElementById(mid),h=document.getElementById(hid);
      if(!m||!h)return;let drag=false,ox=0,oy=0;
      h.addEventListener("mousedown",e=>{drag=true;const r=m.getBoundingClientRect();ox=e.clientX-r.left;oy=e.clientY-r.top;document.body.style.userSelect="none";});
      document.addEventListener("mousemove",e=>{if(!drag||m.style.display==="none")return;m.style.left=Math.max(0,Math.min(window.innerWidth-m.offsetWidth,e.clientX-ox))+"px";m.style.top=Math.max(0,Math.min(window.innerHeight-m.offsetHeight,e.clientY-oy))+"px";});
      document.addEventListener("mouseup",()=>{if(drag){drag=false;document.body.style.userSelect="";}});
    });
  })();

  /* Resize calendar panel */
  (function(){
    const handle=document.getElementById("resize-handle");const right=document.querySelector(".layout-right");
    if(!handle||!right)return;
    const saved=localStorage.getItem("cal-panel-width");if(saved)right.style.width=parseInt(saved)+"px";
    let dragging=false,startX=0,startW=0;
    handle.addEventListener("mousedown",e=>{dragging=true;startX=e.clientX;startW=right.offsetWidth;handle.classList.add("dragging");document.body.style.cursor="col-resize";document.body.style.userSelect="none";e.preventDefault();});
    document.addEventListener("mousemove",e=>{if(!dragging)return;const newW=Math.min(900,Math.max(260,startW+(startX-e.clientX)));right.style.width=newW+"px";});
    document.addEventListener("mouseup",()=>{if(!dragging)return;dragging=false;handle.classList.remove("dragging");document.body.style.cursor="";document.body.style.userSelect="";localStorage.setItem("cal-panel-width",right.offsetWidth);});
  })();

  /* ── CONFIG PAGE ─────────────────────────────────────────────────────── */
  const DAYS_BR = ["Segunda","Terca","Quarta","Quinta","Sexta","Sabado","Domingo"];
  const TYPE_LABELS = {faq:"FAQ",policy:"Politica",product_catalog:"Catalogo",script:"Script",manual:"Manual"};

  /* ── Dirty-state tracking ───────────────────────────────────────────────── */
  const _dirtyTabs = new Set();
  function markDirty(tab) {
    if (!tab) return;
    _dirtyTabs.add(tab);
    const bt = document.querySelector('.cfg-tab[data-tab="'+tab+'"]');
    if (bt) bt.classList.add("has-dirty");
  }
  function clearDirty(tab) {
    if (!tab) return;
    _dirtyTabs.delete(tab);
    const bt = document.querySelector('.cfg-tab[data-tab="'+tab+'"]');
    if (bt) bt.classList.remove("has-dirty");
  }
  function _activeConfigTab() {
    return document.querySelector(".cfg-tab.active")?.dataset?.tab || null;
  }

  /* ── Button loading spinner ─────────────────────────────────────────────── */
  function setBtnLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
      btn._savedHTML = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="btn-spinner"></span>Salvando...';
    } else {
      btn.disabled = false;
      if (btn._savedHTML !== undefined) { btn.innerHTML = btn._savedHTML; btn._savedHTML = undefined; }
    }
  }

  function switchCfgTab(tab) {
    document.querySelectorAll(".cfg-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".cfg-pane").forEach(p => p.classList.remove("active"));
    const bt = document.querySelector('.cfg-tab[data-tab="'+tab+'"]');
    const pn = document.getElementById("cfg-pane-"+tab);
    if (bt) bt.classList.add("active");
    if (pn) pn.classList.add("active");
    localStorage.setItem("cfgTab", tab);
    if (tab === "monitoramento") {
      loadStatusData();
      loadErrorLogs();
      _startStatusAutoRefresh();
    } else {
      _stopStatusAutoRefresh();
    }
  }

  async function loadConfigPage() {
    const saved = localStorage.getItem("cfgTab") || "loja";
    switchCfgTab(saved);
    await Promise.all([loadBotConfig(), loadBusinessHours(), loadFaqItems(), loadRagConfig(), loadRagDocs(), loadRagLogs(), loadSystemPrompt(), loadCustomTpls()]);
    _attachDirtyListeners();
    if (!window._cfgCtrlSAttached) {
      window._cfgCtrlSAttached = true;
      document.addEventListener("keydown", e => {
        if ((e.ctrlKey || e.metaKey) && e.key === "s") {
          const pg = document.querySelector(".page.active");
          if (pg?.id === "page-config") {
            e.preventDefault();
            _saveCfgActiveTab();
          }
        }
        if (e.key === "Escape") {
          if (document.getElementById("client-drawer")?.classList.contains("open")) {
            closeClientDrawer();
          }
        }
      });
    }
  }

  function _attachDirtyListeners() {
    const trackedPanes = ["loja", "identidade", "horarios", "notificacoes", "avancado"];
    trackedPanes.forEach(tab => {
      const pane = document.getElementById("cfg-pane-" + tab);
      if (!pane || pane._dirtyAttached) return;
      pane._dirtyAttached = true;
      pane.addEventListener("input",  () => markDirty(tab));
      pane.addEventListener("change", () => markDirty(tab));
    });
  }

  function _saveCfgActiveTab() {
    const tab = _activeConfigTab();
    if (!tab) return;
    // Aba notificacoes tem botão próprio — buscar especificamente
    if (tab === "notificacoes") {
      const btn = document.querySelector('#cfg-pane-notificacoes .btn-primary');
      if (btn) btn.click();
      return;
    }
    const paneBtn = document.querySelector('#cfg-pane-' + tab + ' .btn-primary');
    if (paneBtn) paneBtn.click();
  }

  /* Bot Config */
  async function loadBotConfig() {
    try {
      const r = await fetch("/admin/bot-config", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const d = await r.json();
      const set = (id, v) => { const el = document.getElementById(id); if (el && v !== undefined) el.value = v || ""; };
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
    } catch(e) { console.error("loadBotConfig", e); }
  }

  async function saveBotConfig(btn) {
    setBtnLoading(btn, true);
    const g = id => (document.getElementById(id)?.value || "").trim();
    const body = {
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
    };
    try {
      const r = await fetch("/admin/bot-config", {method:"POST",headers:authHeaders(),body:JSON.stringify(body)});
      if (r.ok) {
        clearDirty(_activeConfigTab());
        showToast("Configuracoes salvas e prompt atualizado!");
        loadSystemPrompt();
      } else showToast("Erro ao salvar.", false);
    } catch(e) { showToast("Erro: " + e.message, false); }
    setBtnLoading(btn, false);
  }

  /* Business Hours */
  async function loadBusinessHours() {
    try {
      const r = await fetch("/admin/business-hours", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const data = await r.json();
      const grid = document.getElementById("bh-grid");
      if (!grid) return;
      grid.innerHTML = data.map(row => {
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
      }).join("");
    } catch(e) { console.error("loadBusinessHours", e); }
  }

  function updateBhRow(day) {
    const isOpen = document.querySelector('.bh-open[data-day="' + day + '"]').checked;
    document.querySelector('.bh-ot[data-day="' + day + '"]').disabled = !isOpen;
    document.querySelector('.bh-ct[data-day="' + day + '"]').disabled = !isOpen;
  }

  async function saveBusinessHours(btn) {
    setBtnLoading(btn, true);
    const rows = [];
    [0,1,2,3,4,5,6].forEach(day => {
      const isOpen = document.querySelector('.bh-open[data-day="'+day+'"]')?.checked || false;
      const isFlex = document.querySelector('.bh-flex[data-day="'+day+'"]')?.checked || false;
      const ot = document.querySelector('.bh-ot[data-day="'+day+'"]')?.value || null;
      const ct = document.querySelector('.bh-ct[data-day="'+day+'"]')?.value || null;
      rows.push({day_of_week:day, is_open:isOpen, is_flexible:isFlex, open_time:ot||null, close_time:ct||null});
    });
    const slotDur  = parseInt(document.getElementById("bh-slot-duration")?.value  || "30");
    const slotIntv = parseInt(document.getElementById("bh-slot-interval")?.value  || "0");
    try {
      const [r1, r2] = await Promise.all([
        fetch("/admin/business-hours", {method:"POST",headers:authHeaders(),body:JSON.stringify(rows)}),
        fetch("/admin/bot-config", {method:"POST",headers:authHeaders(),body:JSON.stringify({slot_duration_minutes:slotDur, slot_interval_minutes:slotIntv})})
      ]);
      if (r1.ok && r2.ok) { clearDirty("horarios"); showToast("Horarios e duracoes salvos!"); }
      else showToast("Erro ao salvar.", false);
    } catch(e) { showToast("Erro: " + e.message, false); }
    setBtnLoading(btn, false);
  }

  /* FAQ */
  let _faqMap = {};

  function openFaqById(id) { openFaqModal(_faqMap[id] || null); }

  async function loadFaqItems() {
    try {
      const r = await fetch("/admin/faq", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const items = await r.json();
      _faqMap = {};
      items.forEach(f => _faqMap[f.id] = f);
      const tbody = document.getElementById("faq-tbody");
      const ex = document.getElementById("faq-ex-box");
      if (!tbody) return;
      if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-row"><div class="empty-state">Nenhum FAQ cadastrado. Adicione um para comecar.</div></td></tr>';
        if (ex) ex.style.display = "block";
        return;
      }
      if (ex) ex.style.display = "none";
      tbody.innerHTML = items.map(f => {
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
      }).join("");
    } catch(e) { console.error("loadFaqItems", e); }
  }

  function openFaqModal(item) {
    document.getElementById("form-faq").reset();
    const titleEl = document.getElementById("faq-modal-title");
    const idEl = document.getElementById("faq-edit-id");
    if (item && item.id) {
      if (titleEl) titleEl.textContent = "Editar FAQ";
      idEl.value = item.id;
      document.getElementById("faq-question").value = item.question || "";
      document.getElementById("faq-answer").value = item.answer || "";
    } else {
      if (titleEl) titleEl.textContent = "Adicionar FAQ";
      idEl.value = "";
    }
    const m = document.getElementById("modal-faq");
    m.style.display = "block";
    if (!m._positioned) {
      m.style.left = Math.max(0,(window.innerWidth-m.offsetWidth)/2) + "px";
      m.style.top  = Math.max(0,(window.innerHeight-m.offsetHeight)/2) + "px";
      m._positioned = true;
    }
  }
  function closeFaqModal() { document.getElementById("modal-faq").style.display = "none"; }

  async function submitFaq(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-faq");
    btn.disabled = true; btn.textContent = "Salvando...";
    const editId = document.getElementById("faq-edit-id").value;
    const body = {
      question: document.getElementById("faq-question").value.trim(),
      answer:   document.getElementById("faq-answer").value.trim(),
      sort_order: 0,
    };
    try {
      const url = editId ? "/admin/faq/" + editId : "/admin/faq";
      const method = editId ? "PUT" : "POST";
      const r = await fetch(url, {method,headers:authHeaders(),body:JSON.stringify(body)});
      if (r.ok) { closeFaqModal(); loadFaqItems(); showToast("FAQ salvo!"); }
      else showToast("Erro ao salvar FAQ.", false);
    } catch(ex) { showToast("Erro: " + ex.message, false); }
    btn.disabled = false; btn.textContent = "Salvar";
  }

  async function toggleFaq(id, state) {
    const r = await fetch("/admin/faq/" + id + "/toggle", {method:"PATCH",headers:authHeaders(),body:JSON.stringify({is_active:state})});
    if (r.ok) { loadFaqItems(); showToast("FAQ atualizado!"); }
    else showToast("Erro.", false);
  }

  async function deleteFaq(id) {
    if (!confirm("Excluir este FAQ?")) return;
    const r = await fetch("/admin/faq/" + id, {method:"DELETE",headers:authHeaders()});
    if (r.ok) { loadFaqItems(); showToast("FAQ excluido."); }
    else showToast("Erro ao excluir.", false);
  }

  /* System Prompt */
  async function loadSystemPrompt() {
    try {
      const r = await fetch("/admin/system-prompt", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const data = await r.json();
      const ta = document.getElementById("system-prompt-ta");
      if (ta) ta.value = data.prompt;
    } catch(e) { console.error("loadSystemPrompt", e); }
  }

  async function savePrompt(btn) {
    setBtnLoading(btn, true);
    const prompt = document.getElementById("system-prompt-ta").value;
    try {
      const r = await fetch("/admin/system-prompt", {method:"POST",headers:authHeaders(),body:JSON.stringify({prompt})});
      if (r.ok) { clearDirty("avancado"); showToast("Prompt salvo!"); }
      else showToast("Erro ao salvar.", false);
    } catch(e) { showToast("Erro: " + e.message, false); }
    setBtnLoading(btn, false);
  }

  /* ── Notification Templates ─────────────────────────────────────────────── */
  const NOTIF_DEFAULTS = {
    msg_lembrete_dia:  "Olá, {nome}! Aqui é a Liza da LenzÓtica 👓\\n\\nPassando para lembrar que *amanhã* você tem consulta marcada para as *{hora}h* ({data}).\\n\\nQualquer dúvida é só nos chamar. Te esperamos!",
    msg_lembrete_hora: "Olá, {nome}! Aqui é a Liza da LenzÓtica 👓\\n\\nSua consulta está marcada para *{data}* às *{hora}h*.\\n\\nVocê confirma sua presença? Responda *SIM* para confirmar ou *NÃO* caso precise reagendar.",
    msg_cancelamento:  "Olá, {nome}. Seu agendamento para *{data}* às *{hora}h* foi cancelado pois não recebemos confirmação de presença.\\n\\nDeseja reagendar? É só nos enviar uma mensagem 😊",
    msg_retorno:       "Olá, {nome}! Aqui é a Liza da LenzÓtica 👓\\n\\nPassando para lembrar que está na hora do seu retorno na ótica! Que tal agendarmos uma consulta? É só responder *SIM* que eu marco para você 😊",
  };

  /* Insere variável na posição do cursor do textarea */
  function insertVar(taId, variable) {
    const ta = document.getElementById(taId);
    if (!ta) return;
    const s = ta.selectionStart ?? ta.value.length;
    const e = ta.selectionEnd   ?? ta.value.length;
    ta.value = ta.value.slice(0, s) + variable + ta.value.slice(e);
    ta.selectionStart = ta.selectionEnd = s + variable.length;
    ta.focus();
    markDirty("notificacoes");
    ta.dispatchEvent(new Event("input"));
  }

  /* Contador de caracteres por textarea */
  function updateCharCount(ta, counterId) {
    const n = ta.value.length;
    const el = document.getElementById(counterId);
    if (!el) return;
    el.textContent = n + " caractere" + (n !== 1 ? "s" : "");
    el.className = "notif-char-count" + (n > 1000 ? " over" : n > 700 ? " warn" : "");
  }

  /* Carrega templates no pane (chamado do loadBotConfig) */
  function _loadNotifTa(d) {
    const pairs = [
      ["notif-ta-lembrete-dia",  "msg_lembrete_dia",  "notif-cc-lembrete-dia"],
      ["notif-ta-lembrete-hora", "msg_lembrete_hora", "notif-cc-lembrete-hora"],
      ["notif-ta-cancelamento",  "msg_cancelamento",  "notif-cc-cancelamento"],
      ["notif-ta-retorno",       "msg_retorno",       "notif-cc-retorno"],
      ["notif-ta-campanha",      "campaign_message",  "notif-cc-campanha"],
    ];
    pairs.forEach(([taId, key, ccId]) => {
      const ta = document.getElementById(taId);
      if (!ta) return;
      ta.value = (d[key] && d[key].trim()) ? d[key] : "";
      const cc = document.getElementById(ccId);
      if (cc) updateCharCount(ta, ccId);
    });
    // Campos de input simples
    const setInput = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ""; };
    setInput("notif-confirmation-type",    d.confirmation_appointment_type);
    setInput("notif-confirmation-address", d.confirmation_address);
    setInput("notif-confirmation-footer",  d.confirmation_footer);
    setInput("notif-media-audio",    d.msg_media_audio);
    setInput("notif-media-image",    d.msg_media_image);
    setInput("notif-media-video",    d.msg_media_video);
    setInput("notif-media-document", d.msg_media_document);
    setInput("notif-media-sticker",  d.msg_media_sticker);
    // Toggle campanha
    const campEl = document.getElementById("notif-campaign-enabled");
    if (campEl) campEl.checked = d.campaign_enabled !== false;
  }

  async function saveNotifTemplates(btn) {
    setBtnLoading(btn, true);
    const g  = id => document.getElementById(id)?.value || "";
    const body = {
      msg_lembrete_dia:  g("notif-ta-lembrete-dia"),
      msg_lembrete_hora: g("notif-ta-lembrete-hora"),
      msg_cancelamento:  g("notif-ta-cancelamento"),
      msg_retorno:       g("notif-ta-retorno"),
      // Confirmação de agendamento
      confirmation_appointment_type: g("notif-confirmation-type"),
      confirmation_address:          g("notif-confirmation-address"),
      confirmation_footer:           g("notif-confirmation-footer"),
      // Campanha
      campaign_message: g("notif-ta-campanha"),
      // Respostas a mídias
      msg_media_audio:    g("notif-media-audio"),
      msg_media_image:    g("notif-media-image"),
      msg_media_video:    g("notif-media-video"),
      msg_media_document: g("notif-media-document"),
      msg_media_sticker:  g("notif-media-sticker"),
    };
    try {
      const r = await fetch("/admin/bot-config", {method:"POST",headers:authHeaders(),body:JSON.stringify(body)});
      if (r.ok) { clearDirty("notificacoes"); showToast("Templates salvos!"); }
      else showToast("Erro ao salvar.", false);
    } catch(e) { showToast("Erro: " + e.message, false); }
    setBtnLoading(btn, false);
  }

  async function saveCampaignEnabled() {
    const enabled = document.getElementById("notif-campaign-enabled")?.checked ?? true;
    try {
      await fetch("/admin/bot-config", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ campaign_enabled: enabled }),
      });
      showToast(enabled ? "Campanha ativada!" : "Campanha desativada.");
    } catch(e) { showToast("Erro: " + e.message, false); }
  }

  /* ── Templates Personalizados ──────────────────────────────────────────── */
  async function loadCustomTpls() {
    const list = document.getElementById("ctpl-list");
    if (!list) return;
    try {
      const r = await fetch("/admin/custom-templates", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) throw new Error("HTTP " + r.status);
      const tpls = await r.json();
      _renderCustomTpls(tpls);
    } catch(e) {
      list.innerHTML = '<div class="ctpl-empty"><div class="ctpl-empty-icon">&#9888;</div><div>Erro ao carregar templates.</div></div>';
    }
  }

  function _renderCustomTpls(tpls) {
    const list = document.getElementById("ctpl-list");
    if (!list) return;
    if (!tpls.length) {
      list.innerHTML =
        '<div class="ctpl-empty">'
        + '<div class="ctpl-empty-icon">&#128172;</div>'
        + '<div style="font-weight:600;color:var(--text)">Nenhum template ainda</div>'
        + '<div style="font-size:.8rem;max-width:320px;text-align:center">Clique em <strong>Novo template</strong> para criar sua primeira mensagem reutilizavel.</div>'
        + '</div>';
      return;
    }
    list.innerHTML = tpls.map(t => {
      const preview = _escHtml((t.content || "").replace(/\\n/g, " "));
      const name    = _escHtml(t.name);
      const dataStr = t.updated_at ? new Date(t.updated_at).toLocaleDateString("pt-BR") : "";
      return '<div class="ctpl-card" data-id="' + t.id + '">'
        + '<div class="ctpl-card-hdr">'
        +   '<div class="ctpl-card-icon">&#128172;</div>'
        +   '<div class="ctpl-card-name" title="' + name + '">' + name + '</div>'
        +   (dataStr ? '<span style="font-size:.67rem;color:var(--muted);white-space:nowrap">' + dataStr + '</span>' : '')
        +   '<div class="ctpl-card-actions">'
        +     '<button class="action-btn edit-btn" onclick="openCustomTplModal(' + JSON.stringify(t) + ')">'
        +       '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
        +       ' Editar</button>'
        +     '<button class="action-btn cancel-btn" onclick="confirmDeleteCustomTpl(' + t.id + ', ' + JSON.stringify(name) + ')">'
        +       '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/></svg>'
        +       ' Excluir</button>'
        +   '</div>'
        + '</div>'
        + '<div class="ctpl-card-body">'
        +   '<div class="ctpl-preview">' + preview + '</div>'
        + '</div>'
        + '</div>';
    }).join("");
  }

  function openCustomTplModal(tpl) {
    const m     = document.getElementById("modal-custom-tpl");
    const title = document.getElementById("custom-tpl-modal-title");
    const idEl  = document.getElementById("custom-tpl-edit-id");
    const nameEl= document.getElementById("custom-tpl-name");
    const taEl  = document.getElementById("custom-tpl-content");
    document.getElementById("form-custom-tpl").reset();
    if (tpl && tpl.id) {
      title.textContent    = "Editar Template";
      idEl.value           = tpl.id;
      nameEl.value         = tpl.name || "";
      taEl.value           = tpl.content || "";
    } else {
      title.textContent    = "Novo Template";
      idEl.value           = "";
    }
    updateCharCount(taEl, "custom-tpl-cc");
    m.style.display = "block";
    if (!m._positioned) {
      m.style.left = Math.max(0,(window.innerWidth  - m.offsetWidth ) / 2) + "px";
      m.style.top  = Math.max(0,(window.innerHeight - m.offsetHeight) / 2) + "px";
      m._positioned = true;
    }
    setTimeout(() => nameEl.focus(), 80);
  }

  function closeCustomTplModal() {
    document.getElementById("modal-custom-tpl").style.display = "none";
  }

  async function submitCustomTpl(e) {
    e.preventDefault();
    const btn     = document.getElementById("btn-submit-custom-tpl");
    const editId  = document.getElementById("custom-tpl-edit-id").value;
    const name    = document.getElementById("custom-tpl-name").value.trim();
    const content = document.getElementById("custom-tpl-content").value.trim();
    setBtnLoading(btn, true);
    try {
      let r;
      if (editId) {
        r = await fetch("/admin/custom-templates/" + editId,
          {method:"PUT", headers:authHeaders(), body:JSON.stringify({name, content})});
      } else {
        r = await fetch("/admin/custom-templates",
          {method:"POST", headers:authHeaders(), body:JSON.stringify({name, content})});
      }
      if (r.ok) {
        closeCustomTplModal();
        loadCustomTpls();
        showToast(editId ? "Template atualizado!" : "Template criado!");
      } else {
        const err = await r.json().catch(() => ({}));
        showToast("Erro: " + (err.detail || r.status), false);
      }
    } catch(ex) { showToast("Erro: " + ex.message, false); }
    setBtnLoading(btn, false);
  }

  function confirmDeleteCustomTpl(id, name) {
    const msg = document.getElementById("ctpl-del-msg");
    const btn = document.getElementById("btn-confirm-ctpl-del");
    if (msg) msg.textContent = 'Excluir o template "' + name + '"? Esta acao nao pode ser desfeita.';
    if (btn) btn.onclick = () => _doDeleteCustomTpl(id);
    document.getElementById("modal-confirm-ctpl-del").classList.add("open");
  }

  async function _doDeleteCustomTpl(id) {
    document.getElementById("modal-confirm-ctpl-del").classList.remove("open");
    try {
      const r = await fetch("/admin/custom-templates/" + id,
        {method:"DELETE", headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (r.ok) { loadCustomTpls(); showToast("Template excluido."); }
      else showToast("Erro ao excluir.", false);
    } catch(e) { showToast("Erro: " + e.message, false); }
  }

  /* ── System Status ──────────────────────────────────────────────────────── */
  let _statusInterval   = null;
  let _statusCountdown  = 30;
  const _STATUS_INTERVAL = 30; // segundos

  const _STATUS_ICONS = {
    server:   '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
    postgres: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
    pgvector: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    calendar: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    whatsapp: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.63 3.42 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
  };

  const _STATUS_BADGE_LABELS = { ok:"OK", warn:"Aviso", error:"Erro", loading:"...", unknown:"—" };

  function _updateNextRefreshLabel() {
    const el = document.getElementById("status-next-refresh");
    if (el) el.textContent = _statusCountdown;
  }

  function _startStatusAutoRefresh() {
    _stopStatusAutoRefresh();
    _statusCountdown = _STATUS_INTERVAL;
    _updateNextRefreshLabel();
    _statusInterval = setInterval(() => {
      _statusCountdown--;
      _updateNextRefreshLabel();
      if (_statusCountdown <= 0) {
        _statusCountdown = _STATUS_INTERVAL;
        loadStatusData();
        loadErrorLogs();
      }
    }, 1000);
  }

  function _stopStatusAutoRefresh() {
    if (_statusInterval) { clearInterval(_statusInterval); _statusInterval = null; }
  }

  function _renderStatusChecks(data) {
    const grid = document.getElementById("status-grid");
    if (!grid) return;
    const checks = data.checks || [];
    if (!checks.length) {
      grid.innerHTML = '<div style="padding:2rem 1.25rem;font-size:.84rem;color:var(--muted)">Nenhum dado disponivel.</div>';
      return;
    }
    grid.innerHTML = checks.map(c => {
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
    }).join('');
  }

  async function loadStatusData() {
    const grid = document.getElementById("status-grid");
    if (!grid) return;
    try {
      const r = await fetch("/admin/system-status", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      _renderStatusChecks(data);
      const el = document.getElementById("status-last-check");
      if (el) {
        const d = new Date(data.checked_at);
        el.textContent = "Ultima verificacao: " + d.toLocaleTimeString("pt-BR");
        el.style.color = "";
      }
    } catch(e) {
      grid.innerHTML = '<div style="padding:1.25rem;font-size:.83rem;color:#dc2626">Erro ao verificar: ' + e.message + '</div>';
    }
  }

  async function refreshStatus(btn) {
    if (btn) {
      btn._origInner = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="animation:btn-spin .65s linear infinite"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg> Verificando...';
    }
    _statusCountdown = _STATUS_INTERVAL;
    _updateNextRefreshLabel();
    await loadStatusData();
    await loadErrorLogs();
    if (btn) { btn.disabled = false; btn.innerHTML = btn._origInner; }
  }

  /* ── Registros — acordeao ──────────────────────────────────────────────── */
  let _logAccOpen = false;

  function toggleLogAccordion() {
    _logAccOpen = !_logAccOpen;
    const body = document.getElementById("log-accordion-body");
    const btn  = document.getElementById("log-acc-btn");
    if (!body || !btn) return;
    if (_logAccOpen) {
      body.classList.add("open");
      btn.classList.add("open");
      btn.querySelector("svg:first-of-type + svg, svg.acc-arrow") && (btn.querySelector(".acc-arrow") || btn.querySelectorAll("svg")[1]);
      loadErrorLogs();
    } else {
      body.classList.remove("open");
      btn.classList.remove("open");
    }
  }

  /* ── Log de Erros ───────────────────────────────────────────────────────── */
  let _logFilter      = "all";
  let _logSearchTimer = null;

  function setLogFilter(btn, lvl) {
    _logFilter = lvl;
    // Remove active de todos, aplica no clicado
    document.querySelectorAll(".log-filter-btn").forEach(b => delete b.dataset.lfActive);
    btn.dataset.lfActive = lvl;
    loadErrorLogs();
  }

  function _schedLogSearch() {
    clearTimeout(_logSearchTimer);
    _logSearchTimer = setTimeout(loadErrorLogs, 380);
  }

  async function loadErrorLogs() {
    if (!_logAccOpen) return;          // só carrega quando o acordeao esta aberto
    const tbody = document.getElementById("log-tbody");
    if (!tbody) return;
    const search = (document.getElementById("log-search")?.value || "").trim();
    const limit  = document.getElementById("log-limit")?.value || "5";
    const params = new URLSearchParams({ level: _logFilter, limit });
    if (search) params.set("search", search);
    try {
      const r = await fetch("/admin/error-logs?" + params, { headers: {"X-Admin-Token": ADMIN_TOKEN} });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      _renderLogTable(data);
    } catch(e) {
      if (tbody) tbody.innerHTML =
        '<tr><td colspan="4" class="log-empty" style="color:#dc2626">Erro ao carregar logs: '
        + _escHtml(e.message) + '</td></tr>';
    }
  }

  function _renderLogTable(data) {
    const tbody  = document.getElementById("log-tbody");
    const ceEl   = document.getElementById("log-count-error");
    const cwEl   = document.getElementById("log-count-warn");
    const fcEl   = document.getElementById("log-footer-count");
    const fmEl   = document.getElementById("log-footer-meta");
    if (!tbody) return;

    // Contadores no header
    if (ceEl) ceEl.textContent = (data.count_error || 0) + " erro" + (data.count_error !== 1 ? "s" : "");
    if (cwEl) cwEl.textContent = (data.count_warn  || 0) + " aviso" + (data.count_warn  !== 1 ? "s" : "");

    const entries = data.entries || [];
    const todayStr = new Date().toISOString().slice(0, 10);

    // Rodapé
    if (fcEl) fcEl.textContent = "Exibindo " + entries.length
      + " de " + (data.total_lines || 0) + " linhas"
      + (data.last_error_at ? " · Ultimo erro: " + data.last_error_at : "");
    if (fmEl) fmEl.textContent = "Arquivo: " + (data.log_size_kb || 0) + " KB";

    if (!entries.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="log-empty">Nenhuma entrada encontrada para o filtro selecionado.</td></tr>';
      return;
    }

    const icons = { ERROR: "🔴", WARN: "🟡", INFO: "🔵" };
    tbody.innerHTML = entries.map(e => {
      const timeLabel = (e.date && e.date !== todayStr) ? e.date + " " + e.time : e.time;
      return '<tr>'
        + '<td class="log-time">'  + _escHtml(timeLabel) + '</td>'
        + '<td><span class="log-level ' + (e.level || "INFO") + '">'
        +   (icons[e.level] || "⚪") + " " + (e.level || "—") + '</span></td>'
        + '<td><span class="log-module">' + _escHtml(e.module || "SYSTEM") + '</span></td>'
        + '<td class="log-msg">'   + _escHtml(e.message) + '</td>'
        + '</tr>';
    }).join("");
  }

  function _escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  async function clearLogs() {
    if (!confirm("Apagar todo o arquivo de log?\\n\\nEsta acao nao pode ser desfeita.")) return;
    const btn = document.getElementById("btn-clear-logs");
    if (btn) { btn.disabled = true; }
    try {
      const r = await fetch("/admin/error-logs/clear",
        { method: "POST", headers: {"X-Admin-Token": ADMIN_TOKEN} });
      if (r.ok) { showToast("Log limpo com sucesso!"); loadErrorLogs(); }
      else       showToast("Erro ao limpar o log.", false);
    } catch(e) { showToast("Erro: " + e.message, false); }
    if (btn) { btn.disabled = false; }
  }

  function exportLogs() {
    // Abre o endpoint /debug em nova aba para download
    const a = document.createElement("a");
    a.href     = "/debug";
    a.target   = "_blank";
    a.download = "debug_" + new Date().toISOString().slice(0,10) + ".log";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  function resetNotifTemplates() {
    if (!confirm("Restaurar todos os templates para o texto padrão do sistema?\\n\\nEsta ação substituirá seus textos personalizados.")) return;
    const pairs = [
      ["notif-ta-lembrete-dia",  "msg_lembrete_dia",  "notif-cc-lembrete-dia"],
      ["notif-ta-lembrete-hora", "msg_lembrete_hora", "notif-cc-lembrete-hora"],
      ["notif-ta-cancelamento",  "msg_cancelamento",  "notif-cc-cancelamento"],
      ["notif-ta-retorno",       "msg_retorno",       "notif-cc-retorno"],
    ];
    pairs.forEach(([taId, key, ccId]) => {
      const ta = document.getElementById(taId);
      if (!ta) return;
      ta.value = NOTIF_DEFAULTS[key] || "";
      updateCharCount(ta, ccId);
    });
    markDirty("notificacoes");
    showToast("Templates restaurados. Clique em Salvar para confirmar.");
  }

  async function rebuildPrompt() {
    const r = await fetch("/admin/build-prompt", {method:"POST",headers:authHeaders()});
    if (r.ok) { showToast("Prompt regenerado com sucesso!"); loadSystemPrompt(); }
    else showToast("Erro ao regenerar prompt.", false);
  }

  /* RAG Config */
  async function loadRagConfig() {
    try {
      const r = await fetch("/admin/rag/config", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const cfg = await r.json();
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
      const chk = (id, v) => { const el = document.getElementById(id); if (el) el.checked = v; };
      chk("rag-enabled", cfg.enabled);
      set("rag-top-k", cfg.top_k);
      set("rag-min-sim", cfg.min_similarity);
      set("rag-max-ctx", cfg.max_context_tokens);
      set("rag-chunk-size", cfg.chunk_size);
      set("rag-chunk-overlap", cfg.chunk_overlap);
    } catch(e) { console.error("loadRagConfig", e); }
  }

  async function saveRagEnabled() {
    const enabled = document.getElementById("rag-enabled").checked;
    await fetch("/admin/rag/config", {method:"POST",headers:authHeaders(),body:JSON.stringify({enabled})});
    showToast(enabled ? "RAG ativado." : "RAG desativado.");
  }

  function rpStep(id, delta, min, max, decimals=0) {
    const el = document.getElementById(id);
    if (!el) return;
    let val = parseFloat(el.value) + delta;
    val = Math.min(max, Math.max(min, val));
    el.value = decimals ? val.toFixed(decimals) : String(Math.round(val));
    markDirty("avancado");
  }

  async function saveRagConfig(btn) {
    setBtnLoading(btn, true);
    const cfg = {
      top_k: parseInt(document.getElementById("rag-top-k").value),
      min_similarity: parseFloat(document.getElementById("rag-min-sim").value),
      max_context_tokens: parseInt(document.getElementById("rag-max-ctx").value),
      chunk_size: parseInt(document.getElementById("rag-chunk-size").value),
      chunk_overlap: parseInt(document.getElementById("rag-chunk-overlap").value),
    };
    try {
      const r = await fetch("/admin/rag/config", {method:"POST",headers:authHeaders(),body:JSON.stringify(cfg)});
      if (r.ok) { clearDirty("avancado"); showToast("Parametros salvos!"); }
      else showToast("Erro ao salvar.", false);
    } catch(e) { showToast("Erro: " + e.message, false); }
    setBtnLoading(btn, false);
  }

  /* RAG Documents */
  const TYPE_ICONS = {faq:"&#128172;",policy:"&#128196;",product_catalog:"&#128722;",script:"&#127908;",manual:"&#128214;"};
  const TYPE_DESCS = {faq:"Perguntas e respostas",policy:"Regras da loja",product_catalog:"Produtos e precos",script:"Roteiro de atendimento",manual:"Outras informacoes"};

  function _updateRagStats(docs) {
    const statsRow = document.getElementById("rag-stats-row");
    const docsEl   = document.getElementById("rag-stat-docs");
    const chunksEl = document.getElementById("rag-stat-chunks");
    if (!statsRow || !docsEl || !chunksEl) return;
    const active = docs.filter(d => d.is_active).length;
    const chunks = docs.reduce((s,d) => s + (d.chunk_count||0), 0);
    docsEl.textContent   = active + " doc" + (active !== 1 ? "s" : "") + " ativo" + (active !== 1 ? "s" : "");
    chunksEl.textContent = chunks + " chunk" + (chunks !== 1 ? "s" : "");
    statsRow.style.display = docs.length ? "flex" : "none";
  }

  const RAG_EXAMPLES = [
    {"title":"Politica de cancelamento","type":"policy","content":"Cancelamentos devem ser feitos com pelo menos 2 horas de antecedencia. Apos esse prazo, o horario e liberado mas pode nao ser substituido no mesmo dia."},
    {"title":"Tabela de precos","type":"product_catalog","content":"Armações a partir de R$149,90. Lentes simples a partir de R$99,90. Lentes anti-reflexo a partir de R$149,90. Oculos de sol a partir de R$89,90."},
    {"title":"Prazo de confeccao","type":"faq","content":"O prazo medio de confeccao e de 5 a 7 dias uteis apos a aprovacao do pedido e pagamento. Lentes especiais podem levar ate 15 dias."},
    {"title":"Formas de pagamento","type":"faq","content":"Aceitamos dinheiro, PIX, cartao de debito e credito (ate 6x sem juros). Nao aceitamos cheque."},
  ];

  async function loadRagDocs() {
    try {
      const r = await fetch("/admin/rag/documents", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const docs = await r.json();
      const tbody = document.getElementById("doc-tbody");
      if (!tbody) return;
      _updateRagStats(docs);
      if (!docs.length) {
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
      }
      tbody.innerHTML = docs.map(d => {
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
      }).join("");
    } catch(e) { console.error("loadRagDocs", e); }
  }

  function _fillDocExample(title, type, content) {
    openDocModal();
    setTimeout(() => {
      const t = document.getElementById("doc-title");
      const tp = document.getElementById("doc-type");
      const c = document.getElementById("doc-content");
      if (t) t.value = title;
      if (tp) tp.value = type;
      if (c) c.value = content;
    }, 80);
  }

  async function toggleDoc(id, newState) {
    const r = await fetch("/admin/rag/documents/" + id + "/toggle", {method:"PATCH",headers:authHeaders(),body:JSON.stringify({is_active:newState})});
    if (r.ok) { loadRagDocs(); showToast(newState ? "Documento ativado!" : "Documento desativado."); }
    else showToast("Erro.", false);
  }

  async function deleteDoc(id) {
    if (!confirm("Excluir este documento e todos os seus chunks?\\n\\nEsta acao nao pode ser desfeita.")) return;
    const r = await fetch("/admin/rag/documents/" + id, {method:"DELETE",headers:authHeaders()});
    if (r.ok) { loadRagDocs(); showToast("Documento excluido."); }
    else showToast("Erro ao excluir.", false);
  }

  /* Doc Modal */
  function openDocModal() {
    document.getElementById("form-doc").reset();
    const m = document.getElementById("modal-doc");
    m.style.display = "block";
    if (!m._positioned) {
      m.style.left = Math.max(0,(window.innerWidth-m.offsetWidth)/2) + "px";
      m.style.top  = Math.max(0,(window.innerHeight-m.offsetHeight)/2) + "px";
      m._positioned = true;
    }
  }
  function closeDocModal() { document.getElementById("modal-doc").style.display = "none"; }

  async function submitDoc(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-doc");
    btn.disabled = true; btn.textContent = "Indexando...";
    const body = {
      title:       document.getElementById("doc-title").value.trim(),
      source_type: document.getElementById("doc-type").value,
      content:     document.getElementById("doc-content").value.trim(),
    };
    try {
      const r = await fetch("/admin/rag/documents", {method:"POST",headers:authHeaders(),body:JSON.stringify(body)});
      if (r.ok) { const data = await r.json(); closeDocModal(); loadRagDocs(); showToast("Documento indexado (" + data.chunk_count + " chunks)!"); }
      else showToast("Erro ao indexar.", false);
    } catch(ex) { showToast("Erro: " + ex.message, false); }
    btn.disabled = false; btn.textContent = "Indexar e Salvar";
  }

  /* RAG Logs */
  async function loadRagLogs() {
    try {
      const r = await fetch("/admin/rag/logs", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const logs = await r.json();
      const tbody = document.getElementById("rag-log-tbody");
      if (!tbody) return;
      if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row">'
          + '<div class="rag-empty-box">'
          + '<div class="rag-empty-icon">&#128203;</div>'
          + '<div class="rag-empty-title">Nenhuma consulta registrada ainda</div>'
          + '<div class="rag-empty-sub">Quando clientes enviarem mensagens e o RAG estiver ativo, cada busca sera registrada aqui — voce vera quais perguntas acionaram a base de conhecimento e com qual similaridade.</div>'
          + '</div></td></tr>';
        return;
      }
      tbody.innerHTML = logs.map(l => {
        const phone = (l.phone || "").replace("@s.whatsapp.net","").replace("@lid","");
        const dt    = new Date(l.created_at);
        const dtBr  = isNaN(dt.getTime()) ? (l.created_at || "") : dt.toLocaleString("pt-BR");
        const simVal = (l.top_similarity !== null && l.top_similarity !== undefined) ? l.top_similarity * 100 : null;
        let simHtml;
        if (simVal === null) {
          simHtml = '<span style="color:var(--muted)">&#8212;</span>';
        } else {
          const cls = simVal >= 75 ? "sim-cell-high" : simVal >= 50 ? "sim-cell-mid" : "sim-cell-low";
          const dot = simVal >= 75 ? "sim-high"      : simVal >= 50 ? "sim-mid"      : "sim-low";
          simHtml = '<span class="' + cls + '"><span class="rag-sim-dot ' + dot + '" style="display:inline-block;margin-right:.3rem;vertical-align:middle"></span>' + simVal.toFixed(1) + '%</span>';
        }
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
      }).join("");
    } catch(e) { console.error("loadRagLogs", e); }
  }

  /* ── CLIENTES ───────────────────────────────────────────────────────────── */
  let _clientsData = [];
  let _clientFilter = "all";
  let _deletingClientId = null;
  let _notifyingClientId = null;
  let _clientSort = {col: null, dir: 1};
  let _clientViewMode = "table";
  let _drawerClientId = null;

  /* Retorna label e CSS class para status de retorno */
  function clientReturnStatus(returnDate) {
    if (!returnDate) return {cls:"return-none", label:"Sem retorno"};
    const today = new Date(); today.setHours(0,0,0,0);
    const rd = new Date(returnDate + "T00:00:00");
    const diffDays = Math.round((rd - today) / 86400000);
    if (diffDays < 0)  return {cls:"return-overdue",  label:"Atrasado " + Math.abs(diffDays) + "d"};
    if (diffDays <= 30) return {cls:"return-upcoming", label:"Em " + diffDays + " dia" + (diffDays !== 1 ? "s" : "")};
    const months = Math.round(diffDays / 30);
    return {cls:"return-ok", label:"Em ~" + months + " mes" + (months !== 1 ? "es" : "")};
  }

  function _fmtDate(iso) {
    if (!iso) return "—";
    const [y,m,d] = iso.split("-");
    return d + "/" + m + "/" + y;
  }

  function _applyViewMode() {
    const tw = document.getElementById("clients-table-wrap");
    const cg = document.getElementById("clients-cards");
    const btn = document.getElementById("btn-view-toggle");
    const isCards = _clientViewMode === "cards";
    if (tw) tw.style.display = isCards ? "none" : "";
    if (cg) cg.style.display = isCards ? "" : "none";
    if (btn) {
      const lbl = btn.querySelector(".vt-label");
      if (lbl) lbl.textContent = isCards ? "Tabela" : "Cards";
      btn.title = isCards ? "Mudar para tabela" : "Mudar para cards";
    }
  }

  function toggleClientView() {
    _clientViewMode = _clientViewMode === "table" ? "cards" : "table";
    try { localStorage.setItem("clientViewMode", _clientViewMode); } catch(e) {}
    _applyViewMode();
    filterClients();
  }

  async function loadClients() {
    try {
      // Inicializa modo de visualizacao (salvo ou baseado em tela)
      try {
        const saved = localStorage.getItem("clientViewMode");
        _clientViewMode = saved || (window.innerWidth < 640 ? "cards" : "table");
      } catch(e) {
        _clientViewMode = window.innerWidth < 640 ? "cards" : "table";
      }
      _applyViewMode();
      const [cr, sr] = await Promise.all([
        fetch("/admin/clients", {headers:{"X-Admin-Token":ADMIN_TOKEN}}),
        fetch("/admin/clients/stats", {headers:{"X-Admin-Token":ADMIN_TOKEN}})
      ]);
      if (!cr.ok) return;
      _clientsData = await cr.json();
      if (sr.ok) {
        const s = await sr.json();
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v ?? "—"; };
        set("cm-total",    s.total    ?? "—");
        set("cm-new",      s.new_this_month ?? "—");
        set("cm-upcoming", s.upcoming ?? "—");
        set("cm-overdue",  s.overdue  ?? "—");
        // Aniversarios do mes
        const bdayCount = _countBirthdaysThisMonth(_clientsData);
        set("cm-birthday", bdayCount);
        // Pulso no card de atrasados
        const overdueCard = document.getElementById("mc-overdue-card");
        if (overdueCard) overdueCard.classList.toggle("overdue-pulse", (s.overdue || 0) > 0);
        // Badge da sidebar
        const badge = document.querySelector('.nav-item[data-page="clientes"] .nav-badge');
        if (badge) badge.textContent = s.total ?? 0;
      }
      renderDistBar(_clientsData);
      renderBirthdayBanner(_clientsData);
      filterClients();
    } catch(e) { console.error("loadClients", e); }
  }

  function setClientFilter(btn) {
    document.querySelectorAll(".filter-chip").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _clientFilter = btn.dataset.cf;
    filterClients();
  }

  function filterClients() {
    const q = (document.getElementById("client-search")?.value || "").toLowerCase();
    let filtered = _clientsData.filter(c => {
      const text = ((c.first_name||"") + " " + (c.last_name||"") + " " + (c.phone||"")).toLowerCase();
      if (q && !text.includes(q)) return false;
      if (_clientFilter !== "all") {
        if (_clientFilter === "birthday") {
          if (!c.birth_date) return false;
          const bday = new Date(c.birth_date + "T00:00:00");
          if (bday.getMonth() !== new Date().getMonth()) return false;
        } else {
          const st = clientReturnStatus(c.return_date);
          if (_clientFilter === "overdue"  && !st.cls.includes("overdue"))  return false;
          if (_clientFilter === "upcoming" && !st.cls.includes("upcoming")) return false;
          if (_clientFilter === "ok"       && !st.cls.includes("ok"))       return false;
        }
      }
      return true;
    });
    // Ordenação
    if (_clientSort.col) {
      filtered = _applySortClients(filtered);
    } else {
      // Ordenação padrão inteligente: atrasados → próximos → ok → sem retorno
      filtered = filtered.slice().sort((a, b) => {
        const oa = _returnStatusOrder(a.return_date);
        const ob = _returnStatusOrder(b.return_date);
        if (oa !== ob) return oa - ob;
        return (a.first_name||"").localeCompare(b.first_name||"");
      });
    }
    if (_clientViewMode === "cards") renderClientsCards(filtered);
    else renderClientsTable(filtered);
    const hint = document.getElementById("client-count-hint");
    if (hint) hint.textContent = filtered.length + " cliente" + (filtered.length !== 1 ? "s" : "");
  }

  function _applySortClients(list) {
    const col = _clientSort.col;
    const dir = _clientSort.dir;
    return list.slice().sort((a, b) => {
      let va, vb;
      if (col === "return_status_order") {
        va = _returnStatusOrder(a.return_date);
        vb = _returnStatusOrder(b.return_date);
      } else if (col === "visit_count") {
        va = a.visit_count || 0;
        vb = b.visit_count || 0;
      } else {
        va = (a[col] || "");
        vb = (b[col] || "");
      }
      if (va < vb) return -1 * dir;
      if (va > vb) return  1 * dir;
      return 0;
    });
  }

  function sortClients(col) {
    if (_clientSort.col === col) {
      _clientSort.dir *= -1;
    } else {
      _clientSort.col = col;
      _clientSort.dir = 1;
    }
    // Atualiza ícones
    document.querySelectorAll(".sortable-th").forEach(th => {
      th.classList.remove("sort-asc","sort-desc");
    });
    const th = document.getElementById("sh-" + col);
    if (th) th.classList.add(_clientSort.dir === 1 ? "sort-asc" : "sort-desc");
    filterClients();
  }

  function _returnStatusOrder(returnDate) {
    if (!returnDate) return 3;
    const today = new Date(); today.setHours(0,0,0,0);
    const rd = new Date(returnDate + "T00:00:00");
    const diff = Math.round((rd - today) / 86400000);
    if (diff < 0)  return 0; // overdue
    if (diff <= 30) return 1; // upcoming
    return 2; // ok
  }

  function renderClientsTable(clients) {
    const tbody = document.getElementById("clients-tbody");
    if (!tbody) return;
    if (!clients.length) {
      const emptyMsg = _clientsData.length === 0
        ? "<div class='clients-empty'><div class='clients-empty-icon'>&#128100;</div><div>Nenhum cliente cadastrado.<br>Clique em <strong>Novo Cliente</strong> para comecar.</div></div>"
        : "<div class='clients-empty'><div class='clients-empty-icon'>&#128269;</div><div>Nenhum cliente encontrado com os filtros atuais.</div></div>";
      tbody.innerHTML = '<tr><td colspan="10" class="empty-row">' + emptyMsg + '</td></tr>';
      return;
    }
    tbody.innerHTML = clients.map(c => {
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
      return '<tr data-client-id="' + c.id + '" class="tr-clickable" onclick="openClientDrawer(' + c.id + ')">'
        + '<td><span class="client-name">' + (c.first_name || "") + '</span></td>'
        + '<td>' + (c.last_name || '<span style="color:var(--muted)">—</span>') + '</td>'
        + '<td>' + phoneLink + '</td>'
        + '<td style="text-align:center">' + visitBadge + '</td>'
        + '<td>' + _fmtDate(c.last_appointment_date) + '</td>'
        + '<td>' + birthFmt + '</td>'
        + '<td>' + (c.return_date ? _fmtDate(c.return_date) : '<span style="color:var(--muted)">—</span>') + '</td>'
        + '<td><span class="return-badge ' + st.cls + '">' + st.label + '</span></td>'
        + '<td><span class="notes-cell" title="' + notesEsc + '">' + notesShort + '</span></td>'
        + '<td onclick="event.stopPropagation()"><div class="actions-cell">'
        + '<button class="action-btn edit-btn" onclick="openClientModal(' + c.id + ')"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Editar</button>'
        + '<button class="action-btn notify-btn"' + notifyDisabled + ' onclick="openNotifyModal(' + c.id + ')"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg> Notificar</button>'
        + '<button class="action-btn delete-btn" onclick="openClientDelModal(' + c.id + ',' + JSON.stringify((c.first_name||"")+" "+(c.last_name||"")).replace(/"/g,"&quot;") + ')"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/></svg> Excluir</button>'
        + '</div></td></tr>';
    }).join("");
  }

  /* Abre modal de add/edit */
  function openClientModal(id) {
    const m = document.getElementById("modal-client");
    const titleEl = document.getElementById("client-modal-title");
    const idEl = document.getElementById("client-edit-id");
    document.getElementById("form-client").reset();
    document.getElementById("return-parse-hint").style.display = "none";
    if (id) {
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
    } else {
      if (titleEl) titleEl.textContent = "Novo Cliente";
      idEl.value = "";
    }
    m.style.display = "block";
    if (!m._positioned) {
      m.style.left = Math.max(0,(window.innerWidth-m.offsetWidth)/2) + "px";
      m.style.top  = Math.max(0,(window.innerHeight-m.offsetHeight)/2) + "px";
      m._positioned = true;
    }
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }

  function closeClientModal() {
    document.getElementById("modal-client").style.display = "none";
    isPaused = false; secs = 30;
  }

  /* Salvar (POST ou PUT) */
  async function submitClient(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-client");
    btn.disabled = true; btn.textContent = "Salvando...";
    const editId = document.getElementById("client-edit-id").value;
    const body = {
      first_name:            document.getElementById("client-first-name").value.trim(),
      last_name:             document.getElementById("client-last-name").value.trim(),
      phone:                 document.getElementById("client-phone").value.trim(),
      last_appointment_date: document.getElementById("client-apt-date").value || null,
      birth_date:            document.getElementById("client-birth-date").value || null,
      notes:                 document.getElementById("client-notes").value.trim(),
      return_period_months:  document.getElementById("client-return-months").value || null,
      return_date:           document.getElementById("client-return-date").value || null,
    };
    try {
      const url    = editId ? "/admin/clients/" + editId : "/admin/clients";
      const method = editId ? "PUT" : "POST";
      const r = await fetch(url, {method, headers:authHeaders(), body:JSON.stringify(body)});
      if (r.ok) { closeClientModal(); await loadClients(); showToast(editId ? "Cliente atualizado!" : "Cliente cadastrado!"); }
      else { const d = await r.json().catch(()=>({})); showToast("Erro: " + (d.detail||"falha ao salvar"), false); }
    } catch(ex) { showToast("Erro: " + ex.message, false); }
    btn.disabled = false; btn.textContent = "Salvar";
  }

  /* Excluir */
  function openClientDelModal(id, name) {
    _deletingClientId = id;
    const msg = document.getElementById("client-del-msg");
    if (msg) msg.textContent = 'Deseja excluir o cliente "' + name.trim() + '"? Esta acao nao pode ser desfeita.';
    document.getElementById("modal-confirm-client-del").classList.add("open");
    isPaused = true; document.getElementById("cd").textContent = "Pausado";
  }
  function closeClientDelModal() {
    document.getElementById("modal-confirm-client-del").classList.remove("open");
    _deletingClientId = null; isPaused = false; secs = 30;
  }
  async function confirmDeleteClient() {
    if (!_deletingClientId) return;
    const id = _deletingClientId;
    closeClientDelModal();
    const r = await fetch("/admin/clients/" + id, {method:"DELETE",headers:authHeaders()});
    if (r.ok) { await loadClients(); showToast("Cliente excluido."); }
    else showToast("Erro ao excluir.", false);
  }

  /* Exportar CSV */
  function exportClientsCSV() {
    if (!_clientsData.length) { showToast("Nenhum cliente para exportar.", false); return; }
    const cols = ["ID","Nome","Sobrenome","Telefone","Visitas","Ultima Consulta","Nasc.","Data Retorno","Status Retorno","Observacoes"];
    const rows = _clientsData.map(c => {
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
    });
    const csv = [cols.join(","), ...rows].join("\\n");
    const blob = new Blob(["﻿" + csv], {type:"text/csv;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "clientes_lenzótica_" + new Date().toISOString().split("T")[0] + ".csv";
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
    showToast("CSV exportado com " + _clientsData.length + " clientes!");
  }

  /* Notificar retorno via WhatsApp */
  function openNotifyModal(id) {
    _notifyingClientId = id;
    const c = _clientsData.find(x => x.id === id);
    const name = c ? (c.first_name + " " + (c.last_name||"")).trim() : "este cliente";
    const msg = document.getElementById("client-notify-msg");
    if (msg) msg.textContent = 'Enviar lembrete de retorno via WhatsApp para ' + name + '?';
    document.getElementById("modal-confirm-client-notify").classList.add("open");
    isPaused = true; document.getElementById("cd").textContent = "Pausado";
  }
  function closeNotifyModal() {
    document.getElementById("modal-confirm-client-notify").classList.remove("open");
    _notifyingClientId = null; isPaused = false; secs = 30;
  }
  async function confirmNotifyClient() {
    if (!_notifyingClientId) return;
    const id = _notifyingClientId;
    const c = _clientsData.find(x => x.id === id);
    const name = c ? (c.first_name + " " + (c.last_name||"")).trim() : "este cliente";
    closeNotifyModal();
    const r = await fetch("/admin/clients/" + id + "/notify-return", {method:"POST",headers:authHeaders()});
    if (r.ok) showToast("Lembrete enviado para " + name + "!");
    else { const d = await r.json().catch(()=>({})); showToast("Erro: " + (d.detail||"falha ao enviar"), false); }
  }

  /* Atalho: filtrar clientes por chave (chamado pelos cards de metricas) */
  function setClientFilterByKey(key) {
    const btn = document.querySelector('#clients-filters .filter-chip[data-cf="' + key + '"]');
    if (btn) setClientFilter(btn);
  }

  /* Conta clientes com aniversario no mes atual */
  function _countBirthdaysThisMonth(clients) {
    const m = new Date().getMonth();
    return clients.filter(c => c.birth_date && new Date(c.birth_date + "T00:00:00").getMonth() === m).length;
  }

  /* Renderiza a barra de distribuicao de status de retorno */
  function renderDistBar(clients) {
    const wrap = document.getElementById("return-dist-wrap");
    if (!wrap) return;
    const total = clients.length;
    if (!total) { wrap.style.display = "none"; return; }
    let ov = 0, up = 0, ok = 0, no = 0;
    clients.forEach(c => {
      const st = clientReturnStatus(c.return_date);
      if (st.cls.includes("overdue"))       ov++;
      else if (st.cls.includes("upcoming")) up++;
      else if (st.cls.includes("ok"))       ok++;
      else                                  no++;
    });
    const setBar = (id, count) => {
      const el = document.getElementById(id);
      if (!el) return;
      const pct = Math.round(count / total * 100);
      el.style.width = pct + "%";
      const lbl = el.querySelector(".dist-seg-lbl");
      if (lbl) lbl.textContent = pct >= 9 ? count : "";
    };
    setBar("ds-overdue",  ov);
    setBar("ds-upcoming", up);
    setBar("ds-ok",       ok);
    setBar("ds-none",     no);
    [["overdue", ov], ["upcoming", up], ["ok", ok], ["none", no]].forEach(([k, n]) => {
      const el = document.getElementById("dl-" + k);
      if (el) el.textContent = n;
    });
    wrap.style.display = "block";
  }

  /* Renderiza o banner de aniversariantes dos proximos 7 dias */
  function renderBirthdayBanner(clients) {
    const banner = document.getElementById("birthday-banner");
    if (!banner) return;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const upcoming = [];
    clients.forEach(c => {
      if (!c.birth_date) return;
      const b = new Date(c.birth_date + "T00:00:00");
      const yr = today.getFullYear();
      let next = new Date(yr, b.getMonth(), b.getDate());
      if (next < today) next = new Date(yr + 1, b.getMonth(), b.getDate());
      const diff = Math.round((next - today) / 86400000);
      if (diff <= 7) upcoming.push({ name: ((c.first_name || "") + " " + (c.last_name || "")).trim(), diff });
    });
    upcoming.sort((a, b) => a.diff - b.diff);
    if (!upcoming.length) { banner.style.display = "none"; return; }
    const names = upcoming.slice(0, 3).map(c => {
      const when = c.diff === 0 ? "hoje" : c.diff === 1 ? "amanha" : "em " + c.diff + " dias";
      return "<strong>" + c.name + "</strong> (" + when + ")";
    });
    const extra = upcoming.length > 3 ? " e mais " + (upcoming.length - 3) : "";
    banner.innerHTML = '<span class="bday-icon">&#127874;</span>'
      + '<span class="bday-text">' + upcoming.length + ' cliente' + (upcoming.length > 1 ? "s fazem" : " faz")
      + ' aniversario esta semana: ' + names.join(", ") + extra + '</span>'
      + '<button class="bday-close" onclick="this.parentElement.style.display=\'none\'" title="Fechar">&times;</button>';
    banner.style.display = "flex";
  }

  /* ── VISTA EM CARDS ─────────────────────────────────────────────────────── */

  function _clientInitials(first, last) {
    return ((first || "").charAt(0) + (last || "").charAt(0)).toUpperCase() || "?";
  }

  function _clientAvatarColor(name) {
    const palette = ["#2563eb","#059669","#d97706","#dc2626","#7c3aed","#0891b2","#db2777","#65a30d","#9333ea","#c2410c"];
    return palette[(name.charCodeAt(0) || 0) % palette.length];
  }

  function renderClientsCards(clients) {
    const grid = document.getElementById("clients-cards");
    if (!grid) return;
    if (!clients.length) {
      const msg = _clientsData.length === 0
        ? "<div class='clients-empty'><div class='clients-empty-icon'>&#128100;</div><div>Nenhum cliente cadastrado.<br>Clique em <strong>Novo Cliente</strong> para comecar.</div></div>"
        : "<div class='clients-empty'><div class='clients-empty-icon'>&#128269;</div><div>Nenhum cliente encontrado com os filtros atuais.</div></div>";
      grid.innerHTML = msg;
      return;
    }
    grid.innerHTML = clients.map(c => {
      const st = clientReturnStatus(c.return_date);
      const phone = (c.phone || "").replace("@s.whatsapp.net","").replace("@lid","");
      const initials = _clientInitials(c.first_name, c.last_name);
      const color = _clientAvatarColor(c.first_name || "A");
      const visits = c.visit_count || 0;
      const fullName = ((c.first_name || "") + " " + (c.last_name || "")).trim() || "Sem nome";
      const nameEsc = JSON.stringify(fullName);
      const phoneHtml = phone
        ? '<a class="client-phone-link" href="https://wa.me/' + phone + '" target="_blank" onclick="event.stopPropagation()">' + phone + '</a>'
        : '<span style="color:var(--muted)">Sem telefone</span>';
      const notifyDisabled = !phone ? " disabled" : "";
      return '<div class="client-card" onclick="openClientDrawer(' + c.id + ')">'
        + '<div class="client-card-top">'
        + '<div class="client-avatar" style="background:' + color + '">' + initials + '</div>'
        + '<div class="client-card-info"><div class="client-card-name">' + fullName + '</div>'
        + '<div class="client-card-phone">' + phoneHtml + '</div></div>'
        + '<span class="return-badge ' + st.cls + '">' + st.label + '</span>'
        + '</div>'
        + '<div class="client-card-stats">'
        + '<div class="cc-stat"><span class="cc-stat-lbl">Visitas</span>'
        + '<span class="visit-badge' + (visits > 0 ? ' has-visits' : '') + '">' + visits + '</span></div>'
        + '<div class="cc-stat"><span class="cc-stat-lbl">Ultima Consulta</span>'
        + '<span class="cc-stat-val">' + (c.last_appointment_date ? _fmtDate(c.last_appointment_date) : "—") + '</span></div>'
        + '<div class="cc-stat"><span class="cc-stat-lbl">Retorno</span>'
        + '<span class="cc-stat-val">' + (c.return_date ? _fmtDate(c.return_date) : "—") + '</span></div>'
        + '</div>'
        + '<div class="client-card-actions">'
        + '<button class="action-btn edit-btn" onclick="event.stopPropagation();openClientModal(' + c.id + ')">Editar</button>'
        + '<button class="action-btn notify-btn"' + notifyDisabled + ' onclick="event.stopPropagation();openNotifyModal(' + c.id + ')">Notificar</button>'
        + '<button class="action-btn delete-btn" onclick="event.stopPropagation();openClientDelModal(' + c.id + ',' + nameEsc + ')">Excluir</button>'
        + '</div></div>';
    }).join("");
  }

  /* ── GAVETA DE DETALHES ──────────────────────────────────────────────────── */

  function openClientDrawer(id) {
    const c = _clientsData.find(x => x.id === id);
    if (!c) return;
    _drawerClientId = id;
    const content = document.getElementById("drawer-content");
    if (content) content.innerHTML = _buildDrawerHTML(c);
    document.getElementById("client-drawer")?.classList.add("open");
    document.getElementById("client-drawer-overlay")?.classList.add("open");
    isPaused = true;
    document.getElementById("cd").textContent = "Pausado";
  }

  function closeClientDrawer() {
    document.getElementById("client-drawer")?.classList.remove("open");
    document.getElementById("client-drawer-overlay")?.classList.remove("open");
    _drawerClientId = null;
    isPaused = false;
    secs = 30;
  }

  function _navToClientAgendamentos(phone) {
    closeClientDrawer();
    navTo("agendamentos");
    setTimeout(() => {
      const s = document.getElementById("search");
      if (s) { s.value = phone; applyFilter(); }
    }, 80);
  }

  function _buildDrawerHTML(c) {
    const st = clientReturnStatus(c.return_date);
    const phone = (c.phone || "").replace("@s.whatsapp.net","").replace("@lid","");
    const initials = _clientInitials(c.first_name, c.last_name);
    const color = _clientAvatarColor(c.first_name || "A");
    const fullName = ((c.first_name || "") + " " + (c.last_name || "")).trim() || "Sem nome";
    const nameEsc = JSON.stringify(fullName);
    const visits = c.visit_count || 0;
    const phoneHtml = phone
      ? '<a class="client-phone-link" href="https://wa.me/' + phone + '" target="_blank">' + phone + '</a>'
      : '<span style="color:var(--muted)">Sem telefone</span>';
    const notifyDis = !phone ? " disabled" : "";

    // Aniversario com alerta de proximidade
    let bdayHtml = c.birth_date ? _fmtDate(c.birth_date) : '<span style="color:var(--muted)">—</span>';
    if (c.birth_date) {
      const today = new Date(); today.setHours(0,0,0,0);
      const b = new Date(c.birth_date + "T00:00:00");
      const yr = today.getFullYear();
      let next = new Date(yr, b.getMonth(), b.getDate());
      if (next < today) next = new Date(yr + 1, b.getMonth(), b.getDate());
      const diff = Math.round((next - today) / 86400000);
      if (diff === 0)      bdayHtml += ' <span class="bday-soon">&#127874; Hoje!</span>';
      else if (diff <= 7)  bdayHtml += ' <span class="bday-soon">em ' + diff + 'd</span>';
    }

    const notesEsc = (c.notes || "").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    const notesSection = notesEsc
      ? '<div class="drawer-section"><div class="drawer-section-title">Observacoes</div>'
        + '<div class="drawer-notes">' + notesEsc + '</div></div>'
      : "";

    return '<div class="drawer-hdr">'
      + '<div class="drawer-avatar" style="background:' + color + '">' + initials + '</div>'
      + '<div class="drawer-identity">'
      + '<div class="drawer-name">' + fullName + '</div>'
      + '<div class="drawer-phone">' + phoneHtml + '</div>'
      + '</div>'
      + '<button class="drawer-close-btn" onclick="closeClientDrawer()" title="Fechar">&times;</button>'
      + '</div>'
      + '<div class="drawer-body">'
      + '<div class="drawer-section">'
      + '<div class="drawer-section-title">Contato</div>'
      + '<div class="drawer-row"><span class="drawer-lbl">Aniversario</span><span class="drawer-val">' + bdayHtml + '</span></div>'
      + '</div>'
      + '<div class="drawer-section">'
      + '<div class="drawer-section-title">Historico</div>'
      + '<div class="drawer-row"><span class="drawer-lbl">Visitas</span>'
      + '<span class="drawer-val"><span class="visit-badge' + (visits > 0 ? ' has-visits' : '') + '">' + visits + '</span></span></div>'
      + '<div class="drawer-row"><span class="drawer-lbl">Ultima Consulta</span>'
      + '<span class="drawer-val">' + (c.last_appointment_date ? _fmtDate(c.last_appointment_date) : '<span style="color:var(--muted)">—</span>') + '</span></div>'
      + '</div>'
      + '<div class="drawer-section">'
      + '<div class="drawer-section-title">Retorno</div>'
      + '<div class="drawer-row"><span class="drawer-lbl">Data</span>'
      + '<span class="drawer-val">' + (c.return_date ? _fmtDate(c.return_date) : '<span style="color:var(--muted)">Nao definido</span>') + '</span></div>'
      + '<div class="drawer-row"><span class="drawer-lbl">Status</span>'
      + '<span class="drawer-val"><span class="return-badge ' + st.cls + '">' + st.label + '</span></span></div>'
      + '</div>'
      + notesSection
      + '</div>'
      + '<div class="drawer-footer">'
      + '<button class="action-btn edit-btn" onclick="closeClientDrawer();openClientModal(' + c.id + ')">Editar</button>'
      + '<button class="action-btn notify-btn"' + notifyDis + ' onclick="closeClientDrawer();openNotifyModal(' + c.id + ')">Notificar</button>'
      + '<button class="action-btn agend-btn" onclick="_navToClientAgendamentos(' + JSON.stringify(phone) + ')">Agendamentos</button>'
      + '<button class="action-btn delete-btn" onclick="closeClientDrawer();openClientDelModal(' + c.id + ',' + nameEsc + ')">Excluir</button>'
      + '</div>';
  }

  /* Auto-calcular data de retorno a partir dos meses */
  function calcReturnDateFromMonths() {
    const months = parseInt(document.getElementById("client-return-months").value);
    if (!months || months < 1) return;
    const aptDate = document.getElementById("client-apt-date").value;
    const base = aptDate ? new Date(aptDate + "T00:00:00") : new Date();
    base.setMonth(base.getMonth() + months);
    document.getElementById("client-return-date").value = base.toISOString().split("T")[0];
  }

  function suggestReturnDate() {
    // Recalcula retorno se ja tiver meses preenchido
    const months = parseInt(document.getElementById("client-return-months").value);
    if (months && months > 0) calcReturnDateFromMonths();
  }

  /* Tenta parsear "retorno em X meses" nas observacoes */
  function parseReturnFromNotes() {
    const notes = document.getElementById("client-notes").value.toLowerCase();
    const hint  = document.getElementById("return-parse-hint");
    const match = notes.match(/retorno\\s+em\\s+(\\d+)\\s*mes/);
    if (match) {
      const months = parseInt(match[1]);
      const monthsEl = document.getElementById("client-return-months");
      if (!monthsEl.value) {
        monthsEl.value = months;
        calcReturnDateFromMonths();
      }
      if (hint) {
        hint.style.display = "block";
        hint.textContent = "✓ Detectado: retorno em " + months + " meses — data sugerida.";
      }
    } else {
      if (hint) hint.style.display = "none";
    }
  }

  /* Drag modal-client */
  (function(){
    const m = document.getElementById("modal-client");
    const h = document.getElementById("modal-client-handle");
    if (!m || !h) return;
    let drag=false, ox=0, oy=0;
    h.addEventListener("mousedown", e => {
      drag=true;
      const r=m.getBoundingClientRect(); ox=e.clientX-r.left; oy=e.clientY-r.top;
      document.body.style.userSelect="none";
    });
    document.addEventListener("mousemove", e => {
      if (!drag || m.style.display==="none") return;
      m.style.left = Math.max(0,Math.min(window.innerWidth-m.offsetWidth,  e.clientX-ox)) + "px";
      m.style.top  = Math.max(0,Math.min(window.innerHeight-m.offsetHeight, e.clientY-oy)) + "px";
    });
    document.addEventListener("mouseup", () => { if(drag){ drag=false; document.body.style.userSelect=""; } });
  })();

  /* Drag modal-doc, modal-faq e modal-custom-tpl */
  (function(){
    [["modal-doc","modal-doc-handle"],["modal-faq","modal-faq-handle"],["modal-custom-tpl","modal-custom-tpl-handle"]].forEach(([mid,hid])=>{
      const m=document.getElementById(mid),h=document.getElementById(hid);
      if(!m||!h)return;let drag=false,ox=0,oy=0;
      h.addEventListener("mousedown",e=>{drag=true;const r=m.getBoundingClientRect();ox=e.clientX-r.left;oy=e.clientY-r.top;document.body.style.userSelect="none";});
      document.addEventListener("mousemove",e=>{if(!drag||m.style.display==="none")return;m.style.left=Math.max(0,Math.min(window.innerWidth-m.offsetWidth,e.clientX-ox))+"px";m.style.top=Math.max(0,Math.min(window.innerHeight-m.offsetHeight,e.clientY-oy))+"px";});
      document.addEventListener("mouseup",()=>{if(drag){drag=false;document.body.style.userSelect="";}});
    });
  })();

  /* ── CHAT CLIENTE ──────────────────────────────────────────────────────────── */
  var _chatContacts = [];
  var _chatContactFilter = "all";
  var _currentChatPhone = null;
  var _chatPollTimer = null;
  var _chatLastMsgCount = 0;

  var _AVATAR_COLORS = ["#2563eb","#7c3aed","#db2777","#ea580c","#16a34a","#0891b2","#d97706","#dc2626","#0e7490","#4f46e5"];
  function _avatarColor(str) {
    var h = 0;
    for (var i = 0; i < str.length; i++) h = str.charCodeAt(i) + ((h << 5) - h);
    return _AVATAR_COLORS[Math.abs(h) % _AVATAR_COLORS.length];
  }
  function _avatarInitials(name) {
    var parts = (name||"?").trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length-1][0]).toUpperCase();
    return (parts[0].slice(0,2)||"?").toUpperCase();
  }
  function _chatRelTime(iso) {
    if (!iso) return "";
    var d = new Date(iso), now = new Date(), diff = now - d;
    if (diff < 60000) return "agora";
    if (diff < 3600000) return Math.floor(diff/60000) + " min";
    if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});
    var yd = new Date(now); yd.setDate(yd.getDate()-1);
    if (d.toDateString() === yd.toDateString()) return "ontem";
    return d.toLocaleDateString("pt-BR",{day:"2-digit",month:"2-digit"});
  }
  function _chatDateLabel(iso) {
    if (!iso) return "Sem data";
    var d = new Date(iso), now = new Date();
    if (d.toDateString() === now.toDateString()) return "Hoje";
    var yd = new Date(now); yd.setDate(yd.getDate()-1);
    if (d.toDateString() === yd.toDateString()) return "Ontem";
    return d.toLocaleDateString("pt-BR",{day:"2-digit",month:"2-digit",year:"numeric"});
  }
  function _chatMsgTime(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});
  }
  function _escHtml(s) {
    return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }

  async function loadChatContacts() {
    try {
      var r = await fetch("/admin/chat/contacts", {headers:authHeaders()});
      if (!r.ok) return;
      _chatContacts = await r.json();
      renderChatContacts();
      // Atualiza badge de nao lidas no sidebar
      var total = _chatContacts.reduce(function(s,c){ return s + (c.unread_count||0); }, 0);
      var badge = document.getElementById("chat-unread-badge");
      if (badge) { badge.textContent = total; badge.style.display = total > 0 ? "inline-block" : "none"; }
      if (typeof _updatePageTitle === "function") _updatePageTitle();
      // Se conversa aberta e ha novas mensagens, recarrega
      if (_currentChatPhone) {
        var contact = _chatContacts.find(function(c){ return c.phone === _currentChatPhone; });
        if (contact && contact.unread_count > 0) {
          await loadChatMessages(_currentChatPhone, false);
          await fetch("/admin/chat/read/" + encodeURIComponent(_currentChatPhone), {method:"POST",headers:authHeaders()});
          contact.unread_count = 0;
          renderChatContacts();
        }
      }
    } catch(e) { /* silent */ }
  }

  function renderChatContacts() {
    var q = ((document.getElementById("chat-search")||{}).value||"").toLowerCase();
    var cf = _chatContactFilter;
    var list = _chatContacts.filter(function(c) {
      if (cf === "unread" && !c.unread_count) return false;
      if (cf === "ia-off" && c.ia_enabled !== false) return false;
      if (q && !c.name.toLowerCase().includes(q) && !c.display_phone.includes(q)) return false;
      return true;
    });
    var el = document.getElementById("chat-contact-list");
    if (!el) return;
    _updateChatStats();
    if (!list.length) {
      el.innerHTML = '<div class="chat-empty-contacts">Nenhum contato encontrado.</div>';
      return;
    }
    el.innerHTML = list.map(function(c) {
      var color    = _avatarColor(c.name);
      var initials = _avatarInitials(c.name);
      var active   = c.phone === _currentChatPhone ? "active" : "";
      var preview  = _escHtml((c.last_message_role === "user" ? "" : "🤖 ") + (c.last_message||""));
      var unreadHtml = c.unread_count > 0 ? '<span class="chat-unread-badge">' + c.unread_count + '</span>' : "";
      var iaDot    = c.ia_enabled === false ? '<span title="IA pausada" style="color:#ef4444;font-size:.7rem">⏸</span>' : "";
      return '<div class="chat-contact-item ' + active + '" onclick="openChat(\'' + c.phone + '\')" data-phone="' + _escHtml(c.phone) + '">' +
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
    }).join("");
  }

  function filterChatContacts() { renderChatContacts(); }
  function setChatContactFilter(btn) {
    document.querySelectorAll(".chat-filter-btn").forEach(function(b){ b.classList.remove("active"); });
    btn.classList.add("active");
    _chatContactFilter = btn.dataset.cf;
    renderChatContacts();
  }

  async function openChat(phone) {
    _currentChatPhone = phone;
    _chatLastMsgCount = 0;
    closeConvSearch();
    clearQuote();
    document.querySelectorAll(".chat-contact-item").forEach(function(el){
      el.classList.toggle("active", el.dataset.phone === phone);
    });
    var emptyEl  = document.getElementById("chat-conv-empty");
    var activeEl = document.getElementById("chat-active-conv");
    if (emptyEl) emptyEl.style.display = "none";
    if (activeEl) { activeEl.style.display = "flex"; activeEl.style.flexDirection = "row"; }
    document.getElementById("chat-layout").classList.add("conv-open");
    var contact  = _chatContacts.find(function(c){ return c.phone === phone; });
    var name     = (contact && contact.name) || phone.replace("@s.whatsapp.net","").replace("@lid","");
    var color    = _avatarColor(name);
    var initials = _avatarInitials(name);
    var avatarEl = document.getElementById("conv-avatar");
    if (avatarEl) { avatarEl.textContent = initials; avatarEl.style.background = color; }
    var nameEl = document.getElementById("conv-name");
    var phoneEl = document.getElementById("conv-phone");
    if (nameEl)  nameEl.textContent  = name;
    if (phoneEl) phoneEl.textContent = (contact && contact.display_phone) || "";
    // Status chip
    _updateStatusChip(phone);
    // IA button
    var iaEnabled = contact ? contact.ia_enabled !== false : true;
    _updateContactIABtn(iaEnabled);
    // Info sidebar: recarrega se estava aberta
    if (document.getElementById("chat-info-sidebar").classList.contains("open")) {
      loadInfoSidebar(phone);
    }
    await loadChatMessages(phone, true);
    await fetch("/admin/chat/read/" + encodeURIComponent(phone), {method:"POST",headers:authHeaders()});
    if (contact) { contact.unread_count = 0; renderChatContacts(); }
    _initScrollToBottom();
    var inputEl = document.getElementById("chat-input");
    if (inputEl) { inputEl.focus(); _updateCharCounter(); }
    _updatePageTitle();
  }


  async function loadChatMessages(phone, scroll) {
    var area = document.getElementById("chat-messages-area");
    if (!area) return;
    var atBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 80;
    try {
      var r = await fetch("/admin/chat/messages/" + encodeURIComponent(phone), {headers:authHeaders()});
      if (!r.ok) return;
      var msgs = await r.json();
      var prevCount = _chatLastMsgCount;
      if (msgs.length === prevCount && !scroll) return;
      _chatLastMsgCount = msgs.length;
      _hideTypingIndicator();
      area.innerHTML = _renderMsgBubbles(msgs);
      _updateMsgCountLabel(msgs.length);
      if (scroll || atBottom) {
        area.scrollTop = area.scrollHeight;
      } else if (msgs.length > prevCount) {
        _notifyScrollBottomNewMsg(msgs.length - prevCount);
      }
    } catch(e) { /* silent */ }
  }

  function _renderMsgBubbles(msgs) {
    var html = "", lastDate = "";
    msgs.forEach(function(msg) {
      var dl = _chatDateLabel(msg.created_at);
      if (dl !== lastDate) {
        html += '<div class="chat-date-sep">' + _escHtml(dl) + '</div>';
        lastDate = dl;
      }
      var isUser = msg.role === "user";
      var isOp   = msg.sent_by_operator;
      var cls    = isUser ? "received" : (isOp ? "operator" : "sent");
      var time   = _chatMsgTime(msg.created_at);
      var fullTime = msg.created_at ? new Date(msg.created_at).toLocaleString("pt-BR") : "";
      var tick   = !isUser ? '<span class="chat-tick">&#10003;&#10003;</span>' : "";
      var subHtml = "";
      if (!isUser) {
        var subCls  = isOp ? "chat-sub-label op" : "chat-sub-label";
        var subText = isOp ? "&#9997; Operador" : "&#129302; Liza";
        subHtml = '<div class="' + subCls + '">' + subText + '</div>';
      }
      var safe = _escHtml(msg.content);
      var actHtml =
        '<div class="msg-actions">' +
        '<button class="msg-act-btn" onclick="copyMsg(' + JSON.stringify(msg.content) + ')" title="Copiar">&#128203;</button>' +
        '<button class="msg-act-btn" onclick="quoteMsg(' + JSON.stringify(msg.content) + ')" title="Citar">&#8617;</button>' +
        '</div>';
      html += subHtml +
        '<div class="chat-bubble-wrap ' + cls + '">' +
          actHtml +
          '<div class="chat-bubble ' + cls + '" data-msgid="' + (msg.id||"") + '" title="' + fullTime + '">' +
            safe +
            '<div class="chat-bubble-meta">' +
              '<span class="chat-bubble-time">' + time + '</span>' + tick +
            '</div>' +
          '</div>' +
        '</div>';
    });
    return html || '<div style="text-align:center;color:var(--muted);font-size:.82rem;padding:2rem">Nenhuma mensagem ainda.</div>';
  }

  async function sendChatMsg() {
    var input = document.getElementById("chat-input");
    var rawText = input ? input.value : "";
    // Prepend citação se houver
    var text = (_quotedText ? "> " + _quotedText + "\n\n" : "") + rawText.trim();
    if (!text.trim() || !_currentChatPhone) return;
    var btn = document.getElementById("chat-send-btn");
    if (btn) btn.disabled = true;
    input.value = "";
    chatInputResize(input);
    clearQuote();
    try {
      var r = await fetch("/admin/chat/send", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({phone: _currentChatPhone, text: text})
      });
      if (r.ok) {
        await loadChatMessages(_currentChatPhone, true);
        await loadChatContacts();
        if (_currentContactIA && _iaGlobalEnabled) _showTypingIndicator();
      } else {
        showToast("Erro ao enviar mensagem.", false);
        input.value = rawText;
        chatInputResize(input);
      }
    } catch(e) {
      showToast("Erro: " + e.message, false);
      input.value = rawText;
      chatInputResize(input);
    }
    if (btn) btn.disabled = false;
    if (input) input.focus();
  }


  function chatKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMsg(); }
  }
  function chatInputResize(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 130) + "px";
  }

  /* ── Chat SSE (tempo real) ─────────────────────────────────────────────── */
  var _chatSSE = null;
  var _chatSSERetryTimer = null;
  var _chatSSEActive = false;

  function startChatPoll() {
    // SSE tem prioridade; poll é fallback se SSE não suportado/falhou
    stopChatPoll();
    _chatSSEActive = true;
    _connectChatSSE();
  }

  function stopChatPoll() {
    _chatSSEActive = false;
    if (_chatPollTimer)  { clearInterval(_chatPollTimer); _chatPollTimer = null; }
    if (_chatSSERetryTimer) { clearTimeout(_chatSSERetryTimer); _chatSSERetryTimer = null; }
    if (_chatSSE) { _chatSSE.close(); _chatSSE = null; }
  }

  function _connectChatSSE() {
    if (!_chatSSEActive) return;
    if (_chatSSE) { _chatSSE.close(); _chatSSE = null; }
    try {
      _chatSSE = new EventSource("/admin/chat/stream?token=" + encodeURIComponent(ADMIN_TOKEN));

      _chatSSE.addEventListener("connected", function() {
        // SSE ativo — cancela fallback poll se houver
        if (_chatPollTimer) { clearInterval(_chatPollTimer); _chatPollTimer = null; }
        loadChatContacts();
      });

      _chatSSE.addEventListener("new_message", async function(e) {
        var data;
        try { data = JSON.parse(e.data); } catch(_) { return; }
        await loadChatContacts();
        if (_currentChatPhone && _currentChatPhone === data.phone) {
          await loadChatMessages(_currentChatPhone, false);
          await fetch("/admin/chat/read/" + encodeURIComponent(_currentChatPhone), {method:"POST",headers:authHeaders()});
          var contact = _chatContacts.find(function(c){ return c.phone === _currentChatPhone; });
          if (contact) { contact.unread_count = 0; renderChatContacts(); }
        } else if (data.role === "user") {
          // Notificação para mensagens de clientes quando não está vendo a conversa
          var src = _chatContacts.find(function(c){ return c.phone === data.phone; });
          var senderName = src ? src.name : (data.phone||"").replace("@s.whatsapp.net","").replace("@lid","");
          _sendDesktopNotif(senderName, data.content || "Nova mensagem");
          _playChatSound();
        }
        _updatePageTitle();
      });

      _chatSSE.onerror = function() {
        _chatSSE.close(); _chatSSE = null;
        if (!_chatSSEActive) return;
        // Fallback: poll a cada 5s enquanto SSE está reconectando
        if (!_chatPollTimer) _chatPollTimer = setInterval(loadChatContacts, 5000);
        // Tenta reconectar SSE em 6s
        _chatSSERetryTimer = setTimeout(_connectChatSSE, 6000);
      };
    } catch(_) {
      // Browser sem suporte a EventSource — poll permanente
      if (!_chatPollTimer) _chatPollTimer = setInterval(loadChatContacts, 4000);
    }
  }

  /* ── IA Global Toggle ───────────────────────────────────────────────────── */
  let _iaGlobalEnabled = true;

  async function loadGlobalIAStatus() {
    try {
      const r = await fetch("/admin/ia-global", {headers:{"X-Admin-Token":ADMIN_TOKEN}});
      if (!r.ok) return;
      const d = await r.json();
      _iaGlobalEnabled = d.ia_enabled !== false;
      _applyGlobalIAUI(_iaGlobalEnabled);
    } catch(e) { /* silencioso — nao bloqueia o chat */ }
  }

  function _applyGlobalIAUI(enabled) {
    const btn    = document.getElementById("global-ia-btn");
    const banner = document.getElementById("ia-global-banner");
    const txt    = document.getElementById("ia-global-banner-txt");
    if (btn) {
      btn.classList.toggle("ia-on",  enabled);
      btn.classList.toggle("ia-off", !enabled);
      btn.title = enabled
        ? "IA ativa — clique para pausar globalmente"
        : "IA pausada — clique para retomar";
    }
    if (banner) {
      banner.className = "ia-global-banner " + (enabled ? "ia-on" : "ia-off");
    }
    if (txt) {
      txt.innerHTML = enabled
        ? "IA ativa &mdash; respondendo automaticamente"
        : "&#9888;&#65039; IA pausada &mdash; nenhuma resposta automatica";
    }
  }

  async function toggleGlobalIA() {
    const novo = !_iaGlobalEnabled;
    // Feedback imediato
    _iaGlobalEnabled = novo;
    _applyGlobalIAUI(novo);
    try {
      const r = await fetch("/admin/ia-global", {
        method:  "POST",
        headers: authHeaders(),
        body:    JSON.stringify({ia_enabled: novo}),
      });
      if (r.ok) {
        showToast(
          novo
            ? "&#129302; IA retomada — respondendo automaticamente"
            : "&#9209;&#65039; IA pausada — sem respostas automaticas",
          novo
        );
      } else {
        // Reverte se falhar
        _iaGlobalEnabled = !novo;
        _applyGlobalIAUI(!novo);
        showToast("Erro ao alterar IA global.", false);
      }
    } catch(e) {
      _iaGlobalEnabled = !novo;
      _applyGlobalIAUI(!novo);
      showToast("Erro: " + e.message, false);
    }
  }

  /* ── Chat v2: Funções extras ──────────────────────────────────────────────── */

  /* ── IA por contato ─────────────────────────────────────────────── */
  var _currentContactIA = true;

  function _updateContactIABtn(enabled) {
    _currentContactIA = enabled;
    var btn = document.getElementById("conv-ia-btn");
    var lbl = document.getElementById("conv-ia-label");
    if (!btn) return;
    btn.className = "conv-hdr-btn " + (enabled ? "conv-ia-on" : "conv-ia-off");
    if (lbl) lbl.textContent = enabled ? "IA On" : "IA Off";
    btn.title = enabled ? "IA ativa — clique para pausar" : "IA pausada — clique para retomar";
  }

  async function toggleContactIA() {
    if (!_currentChatPhone) return;
    var novo = !_currentContactIA;
    _updateContactIABtn(novo);
    try {
      var r = await fetch("/admin/chat/ia-mode/" + encodeURIComponent(_currentChatPhone), {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify({ia_enabled: novo})
      });
      if (r.ok) {
        showToast(novo ? "IA retomada para este contato" : "IA pausada para este contato", novo);
        var c = _chatContacts.find(function(c){ return c.phone === _currentChatPhone; });
        if (c) { c.ia_enabled = novo; renderChatContacts(); }
      } else {
        _updateContactIABtn(!novo);
        showToast("Erro ao alterar IA.", false);
      }
    } catch(e) { _updateContactIABtn(!novo); }
  }

  /* ── Status do contato ──────────────────────────────────────────── */
  var _CHAT_STATUSES = [
    {key:"none",      label:"Sem status",      icon:"⚪", cls:""},
    {key:"active",    label:"Ativo",           icon:"🟢", cls:"status-active"},
    {key:"waiting",   label:"Aguardando",      icon:"🟡", cls:"status-waiting"},
    {key:"attending", label:"Em atendimento",  icon:"🔵", cls:"status-attending"},
    {key:"resolved",  label:"Resolvido",       icon:"✅", cls:"status-resolved"},
  ];

  function _getContactStatus(phone) {
    try { return JSON.parse(localStorage.getItem("chat_status_" + phone) || "{}"); } catch(_) { return {}; }
  }
  function _setContactStatus(phone, key) {
    localStorage.setItem("chat_status_" + phone, JSON.stringify({key:key}));
  }
  function _updateStatusChip(phone) {
    var chip = document.getElementById("conv-status-chip");
    if (!chip) return;
    var st = _getContactStatus(phone);
    var found = _CHAT_STATUSES.find(function(s){ return s.key === (st.key||"none"); }) || _CHAT_STATUSES[0];
    if (found.key === "none") { chip.textContent = ""; chip.className = "chat-conv-status-chip"; return; }
    chip.textContent = found.icon + " " + found.label;
    chip.className = "chat-conv-status-chip " + found.cls;
  }
  function openStatusPicker(evt) {
    if (evt) evt.stopPropagation();
    var picker = document.getElementById("chat-status-picker");
    if (!picker) return;
    var chip = document.getElementById("conv-status-chip");
    if (chip) {
      var rect = chip.getBoundingClientRect();
      picker.style.top  = (rect.bottom + 6) + "px";
      picker.style.left = rect.left + "px";
    }
    var list = document.getElementById("chat-status-picker-list");
    if (list) {
      list.innerHTML = _CHAT_STATUSES.map(function(s){
        return '<div class="chat-status-item" onclick="setContactStatus(\'' + s.key + '\')">' +
          s.icon + ' ' + _escHtml(s.label) + '</div>';
      }).join("");
    }
    picker.style.display = "block";
    setTimeout(function(){
      document.addEventListener("click", _closePickers, {once:true});
    }, 50);
  }
  function setContactStatus(key) {
    if (!_currentChatPhone) return;
    _setContactStatus(_currentChatPhone, key);
    _updateStatusChip(_currentChatPhone);
    document.getElementById("chat-status-picker").style.display = "none";
    renderChatContacts();
  }

  /* ── Agendamentos do cliente ────────────────────────────────────── */
  function navToClientAppt() {
    if (!_currentChatPhone) return;
    var phone = _currentChatPhone.replace("@s.whatsapp.net","").replace("@lid","");
    navTo("agendamentos");
    setTimeout(function(){
      var searchEl = document.getElementById("search");
      if (searchEl) { searchEl.value = phone; applyFilter(); }
    }, 200);
  }

  /* ── Busca na conversa ──────────────────────────────────────────── */
  var _convSearchResults = [];
  var _convSearchIdx = -1;

  function toggleConvSearch() {
    var bar = document.getElementById("conv-search-bar");
    var btn = document.getElementById("conv-search-btn");
    if (!bar) return;
    var open = bar.style.display !== "none";
    if (open) { closeConvSearch(); }
    else {
      bar.style.display = "flex";
      if (btn) btn.style.color = "#25D366";
      var inp = document.getElementById("conv-search-input");
      if (inp) { inp.value = ""; inp.focus(); }
    }
  }
  function closeConvSearch() {
    var bar = document.getElementById("conv-search-bar");
    var btn = document.getElementById("conv-search-btn");
    if (bar) bar.style.display = "none";
    if (btn) btn.style.color = "";
    _convSearchResults = []; _convSearchIdx = -1;
    var area = document.getElementById("chat-messages-area");
    if (area) {
      area.querySelectorAll("mark").forEach(function(m){
        var p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize();
      });
    }
    var cnt = document.getElementById("conv-search-count");
    if (cnt) cnt.textContent = "";
  }
  function searchConv() {
    var q = (document.getElementById("conv-search-input")||{}).value || "";
    var area = document.getElementById("chat-messages-area");
    var cnt  = document.getElementById("conv-search-count");
    if (!area) return;
    // Remove destaques anteriores
    area.querySelectorAll("mark").forEach(function(m){
      var p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize();
    });
    _convSearchResults = []; _convSearchIdx = -1;
    if (!q.trim()) { if (cnt) cnt.textContent = ""; return; }
    var bubbles = area.querySelectorAll(".chat-bubble");
    var re;
    try { re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&") + ")", "gi"); } catch(_){ return; }
    bubbles.forEach(function(bub){
      var walker = document.createTreeWalker(bub, NodeFilter.SHOW_TEXT);
      var nodes = []; var n;
      while((n = walker.nextNode())) nodes.push(n);
      nodes.forEach(function(node){
        if (!node.textContent.match(re)) return;
        var frag = document.createDocumentFragment();
        var parts = node.textContent.split(re);
        parts.forEach(function(part){
          if (part.match(re)) {
            var mk = document.createElement("mark");
            mk.textContent = part;
            _convSearchResults.push(mk);
            frag.appendChild(mk);
          } else {
            frag.appendChild(document.createTextNode(part));
          }
        });
        node.parentNode.replaceChild(frag, node);
      });
    });
    if (cnt) cnt.textContent = _convSearchResults.length ? "1/" + _convSearchResults.length : "0";
    if (_convSearchResults.length) { _convSearchIdx = 0; _scrollToMark(0); }
  }
  function _scrollToMark(idx) {
    _convSearchResults.forEach(function(m){ m.className = ""; });
    if (_convSearchResults[idx]) {
      _convSearchResults[idx].className = "current";
      _convSearchResults[idx].scrollIntoView({behavior:"smooth", block:"center"});
    }
    var cnt = document.getElementById("conv-search-count");
    if (cnt && _convSearchResults.length) cnt.textContent = (idx+1) + "/" + _convSearchResults.length;
  }
  function searchConvNav(dir) {
    if (!_convSearchResults.length) return;
    _convSearchIdx = (_convSearchIdx + dir + _convSearchResults.length) % _convSearchResults.length;
    _scrollToMark(_convSearchIdx);
  }
  function searchConvKeydown(e) {
    if (e.key === "Enter")  searchConvNav(e.shiftKey ? -1 : 1);
    if (e.key === "Escape") closeConvSearch();
  }

  /* ── Drag livre para painéis flutuantes ─────────────────────────── */
  function _makeDraggable(el, handleSel) {
    var handle = handleSel ? el.querySelector(handleSel) : el;
    if (!handle) return;
    var ox = 0, oy = 0, dragging = false;
    handle.addEventListener("mousedown", function(e) {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      dragging = true;
      var rect = el.getBoundingClientRect();
      ox = e.clientX - rect.left;
      oy = e.clientY - rect.top;
      document.body.style.userSelect = "none";
    });
    document.addEventListener("mousemove", function(e) {
      if (!dragging) return;
      var x = Math.max(0, Math.min(window.innerWidth  - el.offsetWidth,  e.clientX - ox));
      var y = Math.max(0, Math.min(window.innerHeight - el.offsetHeight, e.clientY - oy));
      el.style.left   = x + "px";
      el.style.top    = y + "px";
      el.style.bottom = "auto";
      el.style.right  = "auto";
    });
    document.addEventListener("mouseup", function() {
      if (dragging) { dragging = false; document.body.style.userSelect = ""; }
    });
  }

  /* ── Posicionar painel acima do botão trigger ────────────────────── */
  function _positionAboveBtn(el, triggerBtn, offsetX) {
    var btnRect = triggerBtn.getBoundingClientRect();
    el.style.bottom = "auto"; el.style.right = "auto";
    // Largura do painel
    var pw = el.offsetWidth || 300;
    var ph = el.offsetHeight || 260;
    // Posicionar acima do botão
    var top = btnRect.top - ph - 8;
    var left = btnRect.left + (offsetX || 0);
    // Corrige se sair pela direita
    if (left + pw > window.innerWidth - 8) left = window.innerWidth - pw - 8;
    // Corrige se sair pela esquerda
    if (left < 8) left = 8;
    // Se não couber acima, posiciona abaixo
    if (top < 8) top = btnRect.bottom + 8;
    el.style.top  = top  + "px";
    el.style.left = left + "px";
  }

  /* ── Emoji picker ────────────────────────────────────────────────── */
  var _EMOJIS = [
    ["Rostos",  ["😊","😄","😂","🤣","😍","🥰","😎","🤩","😅","😏","😒","😞","😢","😭","😡","😤","🙏","👍","👎","👋","🤝","💪","👏","✌️"]],
    ["Coração", ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","💕","💞","💓","💗","💖","💝","💘","💔","❣️","♥️"]],
    ["Símbolos",["✅","❌","⭐","🌟","✨","🔥","⚡","💡","📌","📋","📅","📞","💬","🔔","⚠️","ℹ️","🔍","🔒","🔓"]],
    ["Outros",  ["🎉","🎊","🎈","🎁","🚀","🛒","🏠","🕐","⏰","📍","✔️","💰","💳","📷","📱","💻","🌐","✏️","📝","📊"]],
  ];
  var _emojiPickerOpen = false;
  var _emojiPickerReady = false;

  function _buildEmojiPicker() {
    if (_emojiPickerReady) return;
    var picker = document.getElementById("chat-emoji-picker");
    if (!picker) return;
    var handle = '<div class="chat-picker-drag-handle">' +
      '<span>Emojis</span>' +
      '<div class="chat-picker-drag-dots"><span></span><span></span><span></span><span></span><span></span><span></span></div>' +
    '</div>';
    var grid = '<div class="chat-emoji-grid">';
    _EMOJIS.forEach(function(cat){
      grid += '<div class="chat-emoji-cat">' + _escHtml(cat[0]) + '</div>';
      cat[1].forEach(function(em){
        grid += '<button class="chat-emoji-btn" onclick="insertEmoji(\'' + em + '\')">' + em + '</button>';
      });
    });
    grid += '</div>';
    picker.innerHTML = handle + grid;
    _makeDraggable(picker, ".chat-picker-drag-handle");
    _emojiPickerReady = true;
  }

  function toggleEmojiPicker(evt) {
    if (evt) evt.stopPropagation();
    _buildEmojiPicker();
    var picker = document.getElementById("chat-emoji-picker");
    var btn    = document.getElementById("emoji-btn");
    if (!picker) return;
    _emojiPickerOpen = !_emojiPickerOpen;
    if (_emojiPickerOpen) {
      document.getElementById("chat-quick-replies").style.display = "none";
      _qrOpen = false;
      var qb = document.getElementById("qr-btn");
      if (qb) qb.classList.remove("active");
      picker.style.display = "block";
      _positionAboveBtn(picker, btn, 0);
      if (btn) btn.classList.add("active");
      setTimeout(function(){ document.addEventListener("click", _closePickers, {once:true}); }, 50);
    } else {
      picker.style.display = "none";
      if (btn) btn.classList.remove("active");
    }
  }

  function insertEmoji(em) {
    var inp = document.getElementById("chat-input");
    if (!inp) return;
    var s = inp.selectionStart, e2 = inp.selectionEnd;
    inp.value = inp.value.slice(0, s) + em + inp.value.slice(e2);
    inp.selectionStart = inp.selectionEnd = s + em.length;
    inp.focus();
    chatInputResize(inp);
  }

  /* ── Quick replies ────────────────────────────────────────────────── */
  var _QUICK_REPLIES = [
    {label:"Saudação",    text:"Olá! Seja bem-vindo(a) à LenzÓtica. Como posso ajudar você hoje?"},
    {label:"Confirmação", text:"Perfeito! Seu agendamento está confirmado. Estaremos aguardando sua visita!"},
    {label:"Aguardar",    text:"Peço um momento, vou verificar essa informação para você."},
    {label:"Horários",    text:"Nosso atendimento é de segunda a sexta das 8h às 18h, e aos sábados das 8h às 12h."},
    {label:"Localização", text:"Estamos aqui aguardando sua visita! Qualquer dúvida sobre como chegar, é só perguntar."},
    {label:"Exame grátis",text:"Lembrando que nosso exame de vista é completamente gratuito! Agende o seu."},
    {label:"Remarcar",    text:"Sem problemas! Podemos remarcar. Qual data e horário seria melhor para você?"},
    {label:"Encerrar",    text:"Obrigado pelo contato! Qualquer dúvida estamos à disposição. Até logo! 😊"},
  ];
  var _qrOpen = false;
  var _qrReady = false;

  function _buildQuickReplies() {
    if (_qrReady) return;
    var menu = document.getElementById("chat-quick-replies");
    if (!menu) return;
    var list = document.getElementById("chat-qr-list");
    if (list) {
      // Wrap list em div com scroll
      var wrap = document.createElement("div");
      wrap.className = "chat-qr-body";
      wrap.innerHTML = _QUICK_REPLIES.map(function(r){
        return '<div class="chat-qr-item" onclick="insertQuickReply(' + JSON.stringify(r.text) + ')">' +
          '<div class="chat-qr-label">' + _escHtml(r.label) + '</div>' +
          '<div class="chat-qr-preview">' + _escHtml(r.text) + '</div>' +
        '</div>';
      }).join("");
      list.parentNode.replaceChild(wrap, list);
    }
    // O drag usa o .chat-qr-hdr que já está no HTML
    _makeDraggable(menu, ".chat-qr-hdr");
    _qrReady = true;
  }

  function toggleQuickReplies(evt) {
    if (evt) evt.stopPropagation();
    _buildQuickReplies();
    var menu = document.getElementById("chat-quick-replies");
    var btn  = document.getElementById("qr-btn");
    if (!menu) return;
    _qrOpen = !_qrOpen;
    if (_qrOpen) {
      document.getElementById("chat-emoji-picker").style.display = "none";
      _emojiPickerOpen = false;
      var eb = document.getElementById("emoji-btn");
      if (eb) eb.classList.remove("active");
      menu.style.display = "block";
      _positionAboveBtn(menu, btn, 0);
      if (btn) btn.classList.add("active");
      setTimeout(function(){ document.addEventListener("click", _closePickers, {once:true}); }, 50);
    } else {
      menu.style.display = "none";
      if (btn) btn.classList.remove("active");
    }
  }

  function insertQuickReply(text) {
    var inp = document.getElementById("chat-input");
    if (inp) { inp.value = text; chatInputResize(inp); inp.focus(); }
    document.getElementById("chat-quick-replies").style.display = "none";
    _qrOpen = false;
    var btn = document.getElementById("qr-btn");
    if (btn) btn.classList.remove("active");
  }

  function _closePickers() {
    var ep = document.getElementById("chat-emoji-picker");
    var qr = document.getElementById("chat-quick-replies");
    var sp = document.getElementById("chat-status-picker");
    if (ep) { ep.style.display = "none"; _emojiPickerOpen = false; }
    if (qr) { qr.style.display = "none"; _qrOpen = false; }
    if (sp) sp.style.display = "none";
    var eb = document.getElementById("emoji-btn");
    var qb = document.getElementById("qr-btn");
    if (eb) eb.classList.remove("active");
    if (qb) qb.classList.remove("active");
  }

  /* ── Copiar e Citar mensagens ───────────────────────────────────── */
  var _quotedText = "";

  function copyMsg(text) {
    navigator.clipboard.writeText(text).then(function(){
      showToast("Mensagem copiada!", true);
    }).catch(function(){
      showToast("Erro ao copiar.", false);
    });
  }

  function quoteMsg(text) {
    _quotedText = text;
    var bar  = document.getElementById("chat-quote-bar");
    var disp = document.getElementById("chat-quote-text");
    if (bar)  bar.style.display = "flex";
    if (disp) disp.textContent = text.length > 90 ? text.slice(0, 90) + "…" : text;
    var inp = document.getElementById("chat-input");
    if (inp) inp.focus();
  }

  function clearQuote() {
    _quotedText = "";
    var bar = document.getElementById("chat-quote-bar");
    if (bar) bar.style.display = "none";
  }

  /* ── Info sidebar ────────────────────────────────────────────────── */
  var _infoSidebarOpen = false;

  function toggleInfoSidebar() {
    _infoSidebarOpen = !_infoSidebarOpen;
    var sb  = document.getElementById("chat-info-sidebar");
    var btn = document.getElementById("conv-info-btn");
    if (!sb) return;
    if (_infoSidebarOpen) {
      sb.classList.add("open");
      if (btn) btn.classList.add("info-open");
      if (_currentChatPhone) loadInfoSidebar(_currentChatPhone);
    } else {
      closeInfoSidebar();
    }
  }

  function closeInfoSidebar() {
    _infoSidebarOpen = false;
    var sb  = document.getElementById("chat-info-sidebar");
    var btn = document.getElementById("conv-info-btn");
    if (sb) sb.classList.remove("open");
    if (btn) btn.classList.remove("info-open");
  }

  async function loadInfoSidebar(phone) {
    var body = document.getElementById("chat-info-body");
    if (!body) return;
    body.innerHTML = '<div style="text-align:center;color:var(--muted);padding:2rem;font-size:.82rem">Carregando...</div>';
    try {
      var r = await fetch("/admin/chat/contact-info/" + encodeURIComponent(phone), {headers:authHeaders()});
      if (!r.ok) { body.innerHTML = '<div style="color:var(--muted);padding:1rem;font-size:.82rem">Erro ao carregar.</div>'; return; }
      var d = await r.json();
      var cl = d.client;
      var apts = d.appointments || [];
      var html = "";

      // Dados do cliente
      html += '<div class="chat-info-section">';
      html += '<div class="chat-info-section-title">Dados</div>';
      if (cl) {
        var fullName = ((cl.first_name||"") + " " + (cl.last_name||"")).trim() || "—";
        html += '<div class="chat-info-row"><span class="chat-info-key">Nome</span><span class="chat-info-val">' + _escHtml(fullName) + '</span></div>';
        html += '<div class="chat-info-row"><span class="chat-info-key">Visitas</span><span class="chat-info-val">' + (cl.visit_count||0) + '</span></div>';
        if (cl.last_appointment_date) {
          var ld = new Date(cl.last_appointment_date + "T00:00:00");
          html += '<div class="chat-info-row"><span class="chat-info-key">Última cons.</span><span class="chat-info-val">' + ld.toLocaleDateString("pt-BR") + '</span></div>';
        }
        if (cl.return_date) {
          var rd = new Date(cl.return_date + "T00:00:00");
          html += '<div class="chat-info-row"><span class="chat-info-key">Retorno</span><span class="chat-info-val">' + rd.toLocaleDateString("pt-BR") + '</span></div>';
        }
      } else {
        html += '<div style="font-size:.78rem;color:var(--muted);padding:.5rem 0">Nenhum cadastro encontrado.</div>';
      }
      html += '</div>';

      // Agendamentos
      if (apts.length) {
        html += '<div class="chat-info-section">';
        html += '<div class="chat-info-section-title">Agendamentos recentes</div>';
        var _STATUS_LABELS = {scheduled:"Aguardando",confirmed:"Confirmado",attended:"Compareceu",completed:"Concluído",cancelled:"Cancelado",no_show:"Não veio"};
        apts.slice(0,5).forEach(function(a){
          var dt = a.date ? new Date(a.date + "T00:00:00").toLocaleDateString("pt-BR") : "—";
          var stLbl = _STATUS_LABELS[a.status] || a.status;
          html += '<div class="chat-info-appt">';
          html += '<div class="chat-info-appt-date">' + dt + ' &bull; ' + (a.time||"") + '</div>';
          html += '<span class="badge ' + (a.status||"") + '">' + _escHtml(stLbl) + '</span>';
          html += '</div>';
        });
        html += '</div>';
      }

      // Nota interna
      var noteVal = (cl && cl.notes) ? cl.notes : "";
      html += '<div class="chat-info-section">';
      html += '<div class="chat-info-section-title">Nota interna</div>';
      html += '<textarea id="chat-info-note-ta" class="chat-info-note-ta" rows="4" placeholder="Adicione observacoes sobre este cliente...">' + _escHtml(noteVal) + '</textarea>';
      html += '<button class="chat-info-save-btn" onclick="saveInfoNote()">Salvar nota</button>';
      html += '</div>';

      body.innerHTML = html;
    } catch(e) {
      body.innerHTML = '<div style="color:var(--muted);padding:1rem;font-size:.82rem">Erro: ' + e.message + '</div>';
    }
  }

  async function saveInfoNote() {
    if (!_currentChatPhone) return;
    var ta = document.getElementById("chat-info-note-ta");
    if (!ta) return;
    var note = ta.value.trim();
    try {
      var r = await fetch("/admin/chat/note/" + encodeURIComponent(_currentChatPhone), {
        method:"POST", headers:authHeaders(), body:JSON.stringify({note:note})
      });
      showToast(r.ok ? "Nota salva!" : "Erro ao salvar.", r.ok);
    } catch(e) { showToast("Erro: " + e.message, false); }
  }

  /* ── Notificações de desktop ─────────────────────────────────────── */
  var _notifGranted = false;

  function requestChatNotifPermission() {
    if (!("Notification" in window)) { showToast("Seu browser nao suporta notificacoes.", false); return; }
    if (Notification.permission === "granted") {
      _notifGranted = true;
      var btn = document.getElementById("chat-notif-btn");
      if (btn) btn.classList.add("notif-on");
      showToast("Notificacoes ja estao ativas!", true);
      return;
    }
    Notification.requestPermission().then(function(perm) {
      _notifGranted = perm === "granted";
      var btn = document.getElementById("chat-notif-btn");
      if (btn) btn.classList.toggle("notif-on", _notifGranted);
      showToast(_notifGranted ? "Notificacoes ativas!" : "Permissao negada.", _notifGranted);
    });
  }

  function _sendDesktopNotif(name, text) {
    if (!_notifGranted || Notification.permission !== "granted") return;
    if (document.hasFocus()) return;
    try {
      var n = new Notification("Nova mensagem — " + name, {body: text.slice(0,100), icon:"/painel/logo"});
      n.onclick = function(){ window.focus(); navTo("chat"); n.close(); };
      setTimeout(function(){ n.close(); }, 6000);
    } catch(_) {}
  }

  /* ── Som de notificação ──────────────────────────────────────────── */
  function _playChatSound() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.type = "sine"; osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.3);
    } catch(_) {}
  }

  /* ── Título da aba com badge de não lidas ────────────────────────── */
  var _origTitle = document.title;
  function _updatePageTitle() {
    var total = _chatContacts.reduce(function(s,c){ return s + (c.unread_count||0); }, 0);
    document.title = total > 0 ? "(" + total + ") " + _origTitle : _origTitle;
  }

  /* ── Lightbox de imagem ──────────────────────────────────────────── */
  function openLightbox(src) {
    var lb = document.getElementById("chat-lightbox");
    var img = document.getElementById("chat-lightbox-img");
    if (!lb || !img) return;
    img.src = src;
    lb.style.display = "flex";
    document.body.style.overflow = "hidden";
  }
  function closeLightbox() {
    var lb = document.getElementById("chat-lightbox");
    if (lb) lb.style.display = "none";
    document.body.style.overflow = "";
  }

  /* ── Atalhos de teclado ──────────────────────────────────────────── */
  document.addEventListener("keydown", function(e) {
    // Ctrl+K — foca busca de contatos
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      var pageChat = document.getElementById("page-chat");
      if (pageChat && pageChat.classList.contains("active")) {
        e.preventDefault();
        var si = document.getElementById("chat-search");
        if (si) { si.focus(); si.select(); }
      }
    }
    // Ctrl+F — busca na conversa
    if ((e.ctrlKey || e.metaKey) && e.key === "f") {
      var pageChat = document.getElementById("page-chat");
      if (pageChat && pageChat.classList.contains("active") && _currentChatPhone) {
        e.preventDefault();
        var bar = document.getElementById("conv-search-bar");
        if (bar && bar.style.display === "none") toggleConvSearch();
        else {
          var inp = document.getElementById("conv-search-input");
          if (inp) inp.focus();
        }
      }
    }
    // Escape — fecha sobreposições
    if (e.key === "Escape") {
      _closePickers();
      closeConvSearch();
      closeLightbox();
      closeInfoSidebar();
    }
  });

  // Inicializa notificação se já concedida
  if (typeof Notification !== "undefined" && Notification.permission === "granted") {
    _notifGranted = true;
    setTimeout(function(){
      var btn = document.getElementById("chat-notif-btn");
      if (btn) btn.classList.add("notif-on");
    }, 500);
  }

  /* ── Chat v3 — estatísticas, scroll, typing, char counter ──────────────── */

  function _updateChatStats() {
    var total  = _chatContacts.length;
    var unread = _chatContacts.filter(function(c){ return (c.unread_count||0) > 0; }).length;
    var iaOff  = _chatContacts.filter(function(c){ return c.ia_enabled === false; }).length;
    var elT = document.getElementById("chat-stat-total");
    var elU = document.getElementById("chat-stat-unread");
    var elI = document.getElementById("chat-stat-ia-off");
    if (elT) elT.textContent = total + " contato" + (total !== 1 ? "s" : "");
    if (elU) {
      elU.textContent = unread + " nao lido" + (unread !== 1 ? "s" : "");
      elU.style.color = unread > 0 ? "#22c55e" : "";
      elU.style.fontWeight = unread > 0 ? "700" : "";
    }
    if (elI) {
      elI.textContent = iaOff > 0 ? iaOff + " IA pausada" : "";
      elI.style.color = iaOff > 0 ? "#ef4444" : "";
      elI.style.display = iaOff > 0 ? "" : "none";
      var dots = document.querySelectorAll(".chat-stats-dot");
      if (dots[1]) dots[1].style.display = iaOff > 0 ? "" : "none";
    }
  }

  function _updateMsgCountLabel(count) {
    var el = document.getElementById("chat-msg-count-label");
    if (!el) return;
    el.textContent = count > 0 ? count + " mensagen" + (count !== 1 ? "s" : "") : "";
  }

  /* scroll-to-bottom */
  var _scrollBottomNewMsgs = 0;

  function _initScrollToBottom() {
    var area = document.getElementById("chat-messages-area");
    var btn  = document.getElementById("chat-scroll-bottom");
    if (!area || !btn) return;
    area.onscroll = null;
    area.addEventListener("scroll", function() {
      var atBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 80;
      if (atBottom) {
        btn.style.display = "none";
        _scrollBottomNewMsgs = 0;
        var badge = document.getElementById("chat-scroll-bottom-badge");
        if (badge) badge.style.display = "none";
      } else {
        btn.style.display = "flex";
      }
    });
  }

  function scrollToBottom() {
    var area = document.getElementById("chat-messages-area");
    if (area) { area.scrollTop = area.scrollHeight; }
    _scrollBottomNewMsgs = 0;
    var btn   = document.getElementById("chat-scroll-bottom");
    var badge = document.getElementById("chat-scroll-bottom-badge");
    if (btn)   btn.style.display = "none";
    if (badge) badge.style.display = "none";
  }

  function _notifyScrollBottomNewMsg(qty) {
    var area = document.getElementById("chat-messages-area");
    if (!area) return;
    var atBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 80;
    if (atBottom) return;
    _scrollBottomNewMsgs += (qty || 1);
    var btn   = document.getElementById("chat-scroll-bottom");
    var badge = document.getElementById("chat-scroll-bottom-badge");
    if (btn) btn.style.display = "flex";
    if (badge) {
      badge.style.display = "inline-block";
      badge.textContent = _scrollBottomNewMsgs > 9 ? "9+" : _scrollBottomNewMsgs;
    }
  }

  /* typing indicator */
  function _showTypingIndicator() {
    var area = document.getElementById("chat-messages-area");
    if (!area || document.getElementById("chat-typing-indicator")) return;
    var div = document.createElement("div");
    div.className = "chat-typing";
    div.id = "chat-typing-indicator";
    div.innerHTML =
      '<div class="chat-sub-label" style="align-self:flex-start;margin-bottom:.05rem">&#129302; Liza</div>' +
      '<div class="chat-typing-bubble">' +
        '<span class="chat-typing-dot"></span>' +
        '<span class="chat-typing-dot"></span>' +
        '<span class="chat-typing-dot"></span>' +
      '</div>';
    area.appendChild(div);
    area.scrollTop = area.scrollHeight;
  }

  function _hideTypingIndicator() {
    var el = document.getElementById("chat-typing-indicator");
    if (el) el.remove();
  }

  /* char counter */
  function _updateCharCounter() {
    var input   = document.getElementById("chat-input");
    var counter = document.getElementById("chat-char-counter");
    if (!input || !counter) return;
    var len = input.value.length;
    counter.textContent = len > 0 ? len : "";
    if (len > 900) counter.className = "chat-char-counter over";
    else if (len > 600) counter.className = "chat-char-counter warn";
    else counter.className = "chat-char-counter";
  }

  /* fechar conversa — botão voltar no mobile */
  function closeChatConv() {
    document.getElementById("chat-layout").classList.remove("conv-open");
    _currentChatPhone = null;
    _chatLastMsgCount = 0;
    _scrollBottomNewMsgs = 0;
    _hideTypingIndicator();
    var emptyEl  = document.getElementById("chat-conv-empty");
    var activeEl = document.getElementById("chat-active-conv");
    if (emptyEl)  emptyEl.style.display = "";
    if (activeEl) activeEl.style.display = "none";
    document.querySelectorAll(".chat-contact-item").forEach(function(el){
      el.classList.remove("active");
    });
    closeInfoSidebar();
    closeConvSearch();
  }

  /* resolver conversa rapidamente */
  function quickResolve() {
    if (!_currentChatPhone) return;
    _setContactStatus(_currentChatPhone, "resolved");
    _updateStatusChip(_currentChatPhone);
    showToast("Conversa marcada como resolvida", true);
  }

  /* ── Dashboard v2 ─────────────────────────────────────────────────────────── */

  function navToTab(page, filter) {
    navTo(page);
    if (filter) setTimeout(() => setTabByFilter(filter), 100);
  }

  function setTabByFilter(f) {
    const tab = document.querySelector('.tab-nav .tab[data-f="' + f + '"]');
    if (tab) setTab(tab);
  }

  function renderDashboard() {
    renderAlerts();
    renderMetricSubs();
    renderChartV2(7);
    renderStatusBreakdown();
    renderUpcoming();
  }

  function renderAlerts() {
    const el = document.getElementById("dash-alerts");
    if (!el) return;
    const alerts = [];
    if (_PANEL_DATA.pendente > 0) {
      const n = _PANEL_DATA.pendente;
      const txt = "<strong>" + n + " pend\xeancia" + (n !== 1 ? "s" : "") + "</strong> aguardando"
        + (_PANEL_DATA.ai_errors_n > 0 ? " — inclui erros de IA" : "");
      alerts.push({type:"danger", icon:"🔴", txt, action:"navToTab('agendamentos','pending')", link:"Ver pend\xeancias"});
    }
    if (_PANEL_DATA.overdue_n > 0) {
      const n = _PANEL_DATA.overdue_n;
      alerts.push({type:"warn", icon:"⚠️",
        txt:"<strong>" + n + " cliente" + (n !== 1 ? "s" : "") + "</strong> com retorno atrasado",
        action:"navTo('clientes')", link:"Ver clientes"});
    }
    if (_PANEL_DATA.hoje_sem_lembrete > 0) {
      const n = _PANEL_DATA.hoje_sem_lembrete;
      alerts.push({type:"info", icon:"🔔",
        txt:"<strong>" + n + " agendamento" + (n !== 1 ? "s" : "") + "</strong> de hoje sem lembrete enviado",
        action:"navToTab('agendamentos','day')", link:"Enviar lembrete"});
    }
    el.innerHTML = alerts.map(a =>
      '<div class="dash-alert-item dash-alert-' + a.type + '" onclick="' + a.action + '">'
      + '<span class="dash-alert-icon">' + a.icon + '</span>'
      + '<span class="dash-alert-txt">' + a.txt + '</span>'
      + '<span class="dash-alert-link">' + a.link + ' →</span>'
      + '</div>'
    ).join("");
  }

  function renderMetricSubs() {
    const set = (id, html) => { const el = document.getElementById(id); if (el) el.innerHTML = html; };
    const trend = (n, goodDir) => {
      if (n === 0) return '<span class="metric-trend trend-neutral">= est\xe1vel</span>';
      const good = goodDir === "up" ? n > 0 : n < 0;
      const cls  = good ? "trend-up" : "trend-down";
      return '<span class="metric-trend ' + cls + '">' + (n > 0 ? "↑ +" : "↓ ") + n + " vs semana passada</span>";
    };
    const hc = _PANEL_DATA.hoje_confirmados, ha = _PANEL_DATA.hoje_aguardando;
    const parts = [];
    if (hc > 0) parts.push(hc + " confirmado" + (hc !== 1 ? "s" : ""));
    if (ha > 0) parts.push(ha + " aguardando");
    set("m-sub-hoje", parts.join(" \xb7 "));
    set("m-sub-confirmados", trend(_PANEL_DATA.trend_confirmados, "up"));
    set("m-sub-cancelados",  trend(_PANEL_DATA.trend_cancelados,  "down"));
    set("m-sub-concluidos",  "este m\xeas");
    if (_PANEL_DATA.pendente > 0) {
      set("m-sub-pendente", _PANEL_DATA.ai_errors_n > 0
        ? '<span style="color:#b45309;font-size:.7rem">Inclui erros de IA</span>'
        : '<span style="color:#b45309;font-size:.7rem">A\xe7\xe3o necess\xe1ria</span>');
    }
  }

  function setChartRange(btn) {
    document.querySelectorAll(".chart-range-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderChartV2(parseInt(btn.dataset.days));
  }

  function renderChartV2(days) {
    const allCounts = _PANEL_DATA.chart30 || [];
    const allDates  = _PANEL_DATA.chart30d || [];
    const data  = allCounts.slice(-days);
    const dates = allDates.slice(-days);
    if (!data.length) return;
    const total = data.reduce((a, b) => a + b, 0);
    const avg   = total / data.length;
    const max   = Math.max(...data, 1);
    const avgPct = (avg / max) * 100;
    const avgLine  = document.getElementById("chart-avg-line");
    const avgLabel = document.getElementById("chart-avg-label");
    if (avgLine)  avgLine.style.bottom  = "calc(" + avgPct + "% + 20px)";
    if (avgLabel) avgLabel.textContent  = "m\xe9dia " + avg.toFixed(1);
    const el = document.getElementById("bar-chart-v2");
    if (!el) return;
    const DAY_NAMES = ["Dom","Seg","Ter","Qua","Qui","Sex","S\xe1b"];
    el.innerHTML = data.map((cnt, i) => {
      const dateStr = dates[i] || "";
      const isToday = dateStr === TODAY_STR;
      const dp = dateStr ? dateStr.split("-") : [];
      let lbl;
      if (days <= 7) {
        lbl = DAY_NAMES[new Date(dateStr + "T12:00").getDay()] || dateStr;
      } else {
        lbl = dp.length === 3 ? dp[2] + "/" + dp[1] : dateStr;
      }
      const pct      = Math.max((cnt / max) * 100, cnt > 0 ? 6 : 4);
      const colorCls = cnt === 0 ? "chart-bar-zero" : (cnt >= avg ? "chart-bar-above" : "chart-bar-below");
      const todayCls = isToday ? " chart-bar-today" : "";
      return '<div class="chart-col-v2">'
        + '<div class="chart-val-v2">' + (cnt || "") + '</div>'
        + '<div class="chart-col-inner">'
        + '<div class="chart-bar-v2 ' + colorCls + todayCls + '" style="height:' + pct + '%">'
        + '<div class="chart-tooltip-v2">' + lbl + (isToday ? " (hoje)" : "") + " — " + cnt + " agendamento" + (cnt !== 1 ? "s" : "") + '</div>'
        + '</div></div>'
        + '<span class="chart-lbl-v2">' + (isToday ? "<strong>" + lbl + "</strong>" : lbl) + '</span>'
        + '</div>';
    }).join("");
  }

  /* ── AGENDAMENTOS v2 ─────────────────────────────────────────────────── */

  let _agendWidgetsInited = false;
  let _nextApptTimer = null;

  function initAgendWidgets() {
    renderDonutChart();
    updateNextApptBanner();
    updateAgendKPIs();
    _agendWidgetsInited = true;
  }

  /* KPI cards */
  function updateAgendKPIs() {
    const allRows = Array.from(document.querySelectorAll("#tbody tr[data-status]"));
    const today = TODAY_STR;
    const hojeCount = allRows.filter(r => r.dataset.date === today && !["cancelled","no_show","completed"].includes(r.dataset.status)).length;
    const confCount = allRows.filter(r => ["confirmed","attended"].includes(r.dataset.status)).length;
    const pendCount = (window.PENDING_ITEMS||[]).length;

    // Next appointment today
    const now = new Date();
    const nowStr = now.getHours().toString().padStart(2,"0") + ":" + now.getMinutes().toString().padStart(2,"0");
    const todayRows = allRows
      .filter(r => r.dataset.date === today && !["cancelled","no_show","completed"].includes(r.dataset.status) && r.dataset.time >= nowStr)
      .sort((a,b) => a.dataset.time.localeCompare(b.dataset.time));

    const elHoje = document.getElementById("akpi-hoje");
    const elConf = document.getElementById("akpi-conf");
    const elPend = document.getElementById("akpi-pend");
    if (elHoje) { _animateCount(elHoje, hojeCount); }
    if (elConf) { _animateCount(elConf, confCount); }
    if (elPend) { _animateCount(elPend, pendCount); }

    const hojeSubEl = document.getElementById("akpi-hoje-sub");
    const confSubEl = document.getElementById("akpi-conf-sub");
    const pendSubEl = document.getElementById("akpi-pend-sub");
    if (hojeSubEl) {
      const conf = allRows.filter(r => r.dataset.date === today && r.dataset.status === "confirmed").length;
      hojeSubEl.textContent = conf + " confirmado" + (conf !== 1 ? "s" : "");
    }
    if (confSubEl) {
      const total = allRows.filter(r => !["cancelled","no_show","completed"].includes(r.dataset.status)).length;
      const taxa = total > 0 ? Math.round(confCount / total * 100) : 0;
      confSubEl.textContent = taxa + "% da taxa ativa";
    }
    if (pendSubEl) { pendSubEl.textContent = pendCount > 0 ? "requer atencao" : "nenhuma pendencia"; }

    const nextTimeEl = document.getElementById("akpi-next-time");
    const nextNameEl = document.getElementById("akpi-next-name");
    if (nextTimeEl && todayRows.length > 0) {
      nextTimeEl.textContent = todayRows[0].dataset.time;
      const name = todayRows[0].dataset.name || "";
      if (nextNameEl) nextNameEl.textContent = name.split(" ")[0];
    } else if (nextTimeEl) {
      nextTimeEl.textContent = "—";
      if (nextNameEl) nextNameEl.textContent = "nenhum pendente";
    }
  }

  function _animateCount(el, target) {
    const cur = parseInt(el.textContent) || 0;
    if (cur === target) return;
    const step = target > cur ? 1 : -1;
    const diff = Math.abs(target - cur);
    const delay = diff > 20 ? 10 : diff > 5 ? 30 : 60;
    let v = cur;
    const iv = setInterval(() => {
      v += step;
      el.textContent = v;
      if (v === target) clearInterval(iv);
    }, delay);
  }

  /* Next appointment banner */
  function updateNextApptBanner() {
    const banner = document.getElementById("next-appt-banner");
    if (!banner) return;
    if (_nextApptTimer) { clearInterval(_nextApptTimer); _nextApptTimer = null; }

    const allRows = Array.from(document.querySelectorAll("#tbody tr[data-status]"));
    const now = new Date();
    const nowStr = now.getHours().toString().padStart(2,"0") + ":" + now.getMinutes().toString().padStart(2,"0");
    const todayRows = allRows
      .filter(r => r.dataset.date === TODAY_STR && !["cancelled","no_show","completed"].includes(r.dataset.status) && r.dataset.time >= nowStr)
      .sort((a,b) => a.dataset.time.localeCompare(b.dataset.time));

    if (!todayRows.length) { banner.classList.remove("visible","urgent"); return; }

    const next = todayRows[0];
    const [h,m] = next.dataset.time.split(":").map(Number);
    const apptDt = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0);
    const diffMs = apptDt - now;
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin > 60) { banner.classList.remove("visible","urgent"); return; }

    const nameEl = document.getElementById("next-appt-name");
    const cdEl = document.getElementById("next-appt-countdown");
    if (nameEl) nameEl.textContent = next.dataset.name || "Proximo";
    banner.classList.add("visible");
    if (diffMin < 10) banner.classList.add("urgent"); else banner.classList.remove("urgent");

    function tick() {
      const now2 = new Date();
      const diff2 = Math.floor((apptDt - now2) / 60000);
      if (diff2 < 0) { banner.classList.remove("visible","urgent"); if (_nextApptTimer) { clearInterval(_nextApptTimer); _nextApptTimer=null; } return; }
      const h2 = Math.floor(diff2 / 60), m2 = diff2 % 60;
      const txt = h2 > 0 ? ("em " + h2 + "h " + m2 + "min") : ("em " + diff2 + " min");
      if (cdEl) cdEl.textContent = "— " + next.dataset.time + " — " + txt;
      if (diff2 < 10) banner.classList.add("urgent"); else banner.classList.remove("urgent");
    }
    tick();
    _nextApptTimer = setInterval(tick, 30000);
  }

  /* Timeline */
  function renderTimeline() {
    const body = document.getElementById("timeline-body");
    const dateEl = document.getElementById("timeline-date-lbl");
    if (!body) return;
    const today = TODAY_STR;
    const dp = today.split("-");
    if (dateEl && dp.length === 3) dateEl.textContent = dp[2] + "/" + dp[1] + "/" + dp[0];

    const apts = (window._PANEL_DATA && window._PANEL_DATA.today_apts) || [];
    if (!apts.length) {
      body.innerHTML = '<div class="timeline-empty">Nenhum agendamento hoje</div>';
      return;
    }

    const SC = {scheduled:"#d97706",day_reminder_sent:"#2563eb",reminder_sent:"#7c3aed",response_received:"#7c3aed",confirmed:"#059669",attended:"#0f766e"};
    const SL = {scheduled:"Aguardando",day_reminder_sent:"Lembrete 1d",reminder_sent:"Lembrete 1h",response_received:"Respondeu",confirmed:"Confirmado",attended:"Compareceu"};
    const SBG = {scheduled:"#fef9c3",day_reminder_sent:"#dbeafe",reminder_sent:"#e0e7ff",response_received:"#ede9fe",confirmed:"#d1fae5",attended:"#ccfbf1"};

    const now = new Date();
    const nowStr = now.getHours().toString().padStart(2,"0") + ":" + now.getMinutes().toString().padStart(2,"0");

    body.innerHTML = apts.map(a => {
      const color = SC[a.status] || "#64748b";
      const stLbl = SL[a.status] || a.status;
      const stBg = SBG[a.status] || "#f1f5f9";
      const isPast = a.time < nowStr;
      const isNext = !isPast && apts.find(x => x.time >= nowStr) === a;
      return '<div class="timeline-item" onclick="navToTab(\'agendamentos\',\'day\')" style="' + (isPast ? "opacity:.5" : "") + '">'
        + '<span class="timeline-time" style="' + (isNext ? "color:var(--primary);font-weight:800" : "") + '">' + a.time + '</span>'
        + '<span class="timeline-dot" style="background:' + color + (isNext ? ';box-shadow:0 0 0 3px ' + color + '33' : '') + '"></span>'
        + '<div class="timeline-info">'
        + '<div class="timeline-name">' + a.name + '</div>'
        + '<span class="timeline-badge-mini" style="background:' + stBg + ';color:' + color + '">' + stLbl + '</span>'
        + '</div>'
        + '</div>';
    }).join("");
  }

  /* Donut chart */
  function renderDonutChart() {
    const canvas = document.getElementById("donut-canvas");
    const legendEl = document.getElementById("donut-legend");
    if (!canvas || !legendEl) return;

    const sc = (window._PANEL_DATA && window._PANEL_DATA.status_counts) || {};
    const ITEMS = [
      {key:"confirmed",   label:"Confirmado", color:"#059669"},
      {key:"attended",    label:"Compareceu", color:"#0f766e"},
      {key:"scheduled",   label:"Aguardando", color:"#d97706"},
      {key:"day_reminder_sent", label:"Lembrete 1d", color:"#2563eb"},
      {key:"reminder_sent",     label:"Lembrete 1h", color:"#7c3aed"},
      {key:"completed",   label:"Concluido",  color:"#0891b2"},
      {key:"cancelled",   label:"Cancelado",  color:"#dc2626"},
      {key:"no_show",     label:"Nao veio",   color:"#ea580c"},
    ];
    const filtered = ITEMS.filter(it => sc[it.key] > 0);
    const total = filtered.reduce((s, it) => s + (sc[it.key]||0), 0);
    if (!total) { legendEl.innerHTML = '<div style="font-size:.75rem;color:var(--muted)">Sem dados</div>'; return; }

    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const cx = W/2, cy = H/2, R = W/2 - 5, r = R * 0.55;
    ctx.clearRect(0, 0, W, H);

    let angle = -Math.PI / 2;
    filtered.forEach(it => {
      const frac = (sc[it.key]||0) / total;
      const end = angle + frac * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, angle, end);
      ctx.closePath();
      ctx.fillStyle = it.color;
      ctx.fill();
      angle = end;
    });
    // Hole
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    ctx.fillStyle = isDark ? "#1e293b" : "#ffffff";
    ctx.fill();
    // Center count
    ctx.fillStyle = isDark ? "#f1f5f9" : "#0f172a";
    ctx.font = "bold " + Math.round(R*0.42) + "px Inter,system-ui,sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(total, cx, cy);

    legendEl.innerHTML = filtered.slice(0,5).map(it =>
      '<div class="donut-legend-item">'
      + '<span class="donut-legend-dot" style="background:' + it.color + '"></span>'
      + '<span class="donut-legend-lbl">' + it.label + '</span>'
      + '<span class="donut-legend-val">' + (sc[it.key]||0) + '</span>'
      + '</div>'
    ).join("");
  }

  /* Mobile cards */
  function renderMobileCards(start, end) {
    const container = document.getElementById("appt-card-list");
    if (!container) return;
    if (window.innerWidth > 768) { container.innerHTML = ""; return; }

    const rows = _pgVisible.slice(start, end);
    if (!rows.length) {
      container.innerHTML = '<div style="text-align:center;padding:1.5rem;color:var(--muted);font-size:.84rem">Nenhum registro encontrado.</div>';
      return;
    }

    const SL = {scheduled:"Aguardando",day_reminder_sent:"Lembrete 1 dia",reminder_sent:"Lembrete 1h",response_received:"Respondeu",confirmed:"Confirmado",attended:"Compareceu",no_show:"Nao veio",completed:"Concluido",cancelled:"Cancelado"};
    const SC = {scheduled:"#854d0e",day_reminder_sent:"#1e40af",reminder_sent:"#3730a3",response_received:"#5b21b6",confirmed:"#065f46",attended:"#0f766e",no_show:"#9a3412",completed:"#0369a1",cancelled:"#991b1b"};
    const SBG= {scheduled:"#fef9c3",day_reminder_sent:"#dbeafe",reminder_sent:"#e0e7ff",response_received:"#ede9fe",confirmed:"#d1fae5",attended:"#ccfbf1",no_show:"#ffedd5",completed:"#e0f2fe",cancelled:"#fee2e2"};

    container.innerHTML = rows.map((row, i) => {
      const st = row.dataset.status || "";
      const name = row.dataset.name || "";
      const phone = row.querySelector(".phone-num")?.textContent || "";
      const date = row.dataset.date || "";
      const time = row.dataset.time || "";
      const dp = date.split("-");
      const dateStr = dp.length === 3 ? dp[2]+"/"+dp[1]+"/"+dp[0] : date;
      const isToday = date === TODAY_STR;
      const faltamEl = row.querySelector(".faltam");
      const faltam = faltamEl ? faltamEl.textContent : "";
      const faltamCls = faltamEl ? (faltamEl.className.includes("time-soon") ? "time-soon" : faltamEl.className.includes("time-past") ? "time-past" : "time-ok") : "";
      const rowIdx = start + i;

      let primaryBtn = "";
      if (st === "confirmed")
        primaryBtn = '<button class="action-btn confirm-btn" onclick="mCardAction(' + rowIdx + ',\'markAttended\')">Compareceu</button>';
      else if (st === "attended")
        primaryBtn = '<button class="action-btn confirm-btn" onclick="mCardAction(' + rowIdx + ',\'complete\')">Concluir</button>';
      else if (st === "scheduled" || st === "day_reminder_sent")
        primaryBtn = '<button class="action-btn remind-btn" onclick="mCardAction(' + rowIdx + ',\'remind\')">Lembrete</button>';
      else if (st === "cancelled")
        primaryBtn = '<button class="action-btn recover-btn" onclick="mCardAction(' + rowIdx + ',\'recover\')">Recuperar</button>';
      else if (st === "no_show")
        primaryBtn = '<button class="action-btn recover-btn" onclick="mCardAction(' + rowIdx + ',\'reschedule\')">Remarcar</button>';

      const stColor = SC[st] || "#64748b";
      const stBg = SBG[st] || "#f1f5f9";

      return '<div class="appt-card" data-status="' + st + '" data-row-idx="' + rowIdx + '">'
        + '<div class="appt-card-top">'
        + '<span class="appt-card-name">' + name + '</span>'
        + '<span style="display:inline-flex;padding:.15rem .5rem;border-radius:999px;font-size:.65rem;font-weight:600;background:' + stBg + ';color:' + stColor + '">' + (SL[st]||st) + '</span>'
        + '</div>'
        + '<div class="appt-card-meta">'
        + '<span>&#128222; ' + phone + '</span>'
        + '<span>&#128197; ' + dateStr + (isToday ? ' <span class="hoje-tag">HOJE</span>' : '') + '</span>'
        + '<span>&#128336; ' + time + '</span>'
        + (faltam && faltam !== "—" ? '<span class="faltam ' + faltamCls + '">' + faltam + '</span>' : '')
        + '</div>'
        + '<div class="appt-card-actions">'
        + primaryBtn
        + (!["cancelled","no_show","completed"].includes(st) ? '<button class="action-btn edit-btn" onclick="mCardAction(' + rowIdx + ',\'edit\')">Editar</button>' : '')
        + (!["cancelled","no_show","completed"].includes(st) ? '<button class="action-btn cancel-btn" onclick="mCardAction(' + rowIdx + ',\'cancel\')">Cancelar</button>' : '')
        + '</div>'
        + '</div>';
    }).join("");
  }

  function mCardAction(rowIdx, action) {
    const row = _pgVisible[rowIdx];
    if (!row) return;
    const sel = {markAttended:".confirm-btn", complete:".confirm-btn", remind:".remind-btn", recover:".recover-btn", reschedule:".recover-btn", edit:".edit-btn", cancel:".cancel-btn"};
    const btn = row.querySelector(sel[action]);
    if (btn) btn.click();
  }

  /* Period chips */
  function applyPeriodChip(chip) {
    document.querySelectorAll(".period-chip").forEach(c => c.classList.remove("pc-active"));
    chip.classList.add("pc-active");
    const period = chip.dataset.period;
    const from = document.getElementById("filter-date-from");
    const to = document.getElementById("filter-date-to");
    const clearBtn = document.getElementById("btn-clear-dates");
    if (period === "all") {
      if (from) from.value = "";
      if (to) to.value = "";
      if (clearBtn) clearBtn.classList.remove("visible");
    } else {
      const today = new Date();
      const fmt = d => d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" + String(d.getDate()).padStart(2,"0");
      let f, t;
      if (period === "today") { f = t = fmt(today); }
      else if (period === "tomorrow") { const tm = new Date(today); tm.setDate(tm.getDate()+1); f = t = fmt(tm); }
      else if (period === "week") { const we = new Date(today); we.setDate(we.getDate()+6); f = fmt(today); t = fmt(we); }
      if (from) from.value = f || "";
      if (to) to.value = t || "";
      if (clearBtn) clearBtn.classList.add("visible");
    }
    applyFilter();
  }

  /* Sort */
  let _apptSortKey = "";
  function applyApptSort() {
    const sel = document.getElementById("appt-sort");
    _apptSortKey = sel ? sel.value : "";
    applyFilter();
  }
  function _applyApptSortInternal() {
    if (!_apptSortKey) return;
    _pgVisible.sort((a, b) => {
      if (_apptSortKey === "date-asc") return (a.dataset.date+a.dataset.time).localeCompare(b.dataset.date+b.dataset.time);
      if (_apptSortKey === "date-desc") return (b.dataset.date+b.dataset.time).localeCompare(a.dataset.date+a.dataset.time);
      if (_apptSortKey === "name-asc") return (a.dataset.name||"").localeCompare(b.dataset.name||"", "pt-BR");
      if (_apptSortKey === "name-desc") return (b.dataset.name||"").localeCompare(a.dataset.name||"", "pt-BR");
      if (_apptSortKey === "status") return (a.dataset.status||"").localeCompare(b.dataset.status||"");
      return 0;
    });
  }

  /* Export CSV */
  function exportApptCSV() {
    const rows = Array.from(document.querySelectorAll("#tbody tr[data-status]"))
      .filter(r => r.style.display !== "none" || _pgVisible.includes(r));
    if (!rows.length) { showToast("Nenhum dado para exportar.", false); return; }
    const lines = ["Nome,Telefone,Data,Hora,Status"];
    _pgVisible.forEach(row => {
      const name = (row.dataset.name||"").replace(/,/g,";");
      const phone = (row.querySelector(".phone-num")?.textContent||"").replace(/,/g,";");
      const date = row.dataset.date||"";
      const time = row.dataset.time||"";
      const st = row.dataset.status||"";
      lines.push([name,phone,date,time,st].join(","));
    });
    const blob = new Blob(["﻿"+lines.join("\n")], {type:"text/csv;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "agendamentos.csv"; a.click();
    URL.revokeObjectURL(url);
    showToast("CSV exportado com " + _pgVisible.length + " registros.");
  }

  /* Resize: refresh donut when theme changes */
  document.getElementById("theme-btn")?.addEventListener("click", () => {
    setTimeout(renderDonutChart, 150);
  });

  /* Init */
  (function(){
    const lp=localStorage.getItem("lastPage")||"dashboard";navTo(lp);
    if(localStorage.getItem("sbCollapsed")==="1" && window.innerWidth > 768)document.getElementById("sidebar").classList.add("collapsed");
    renderDashboard();
  })();
