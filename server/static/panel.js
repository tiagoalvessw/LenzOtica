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
    isPaused = false;
    secs = 30;
    if (page === "config") loadConfigPage();
    if (page === "clientes") loadClients();
    if (page === "chat") { loadChatContacts(); loadGlobalIAStatus(); startChatPoll(); } else { stopChatPoll(); }
    // Ajusta overflow do main para o chat (layout fixo)
    const mainEl = document.querySelector("main");
    if (mainEl) mainEl.style.overflow = page === "chat" ? "hidden" : "";
  }
  function toggleSidebar() {
    const sb = document.getElementById("sidebar");
    sb.classList.toggle("collapsed");
    localStorage.setItem("sbCollapsed", sb.classList.contains("collapsed") ? "1" : "0");
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
    const rows = Array.from(document.querySelectorAll("#tbody tr[data-status]"))
      .filter(r => !["cancelled","no_show","completed"].includes(r.dataset.status))
      .sort((a,b) => (a.dataset.date+a.dataset.time).localeCompare(b.dataset.date+b.dataset.time))
      .slice(0,6);
    const el = document.getElementById("upcoming-list");
    if (!el) return;
    if (!rows.length) {
      el.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--muted);font-size:.84rem;">Nenhum agendamento pendente.</div>';
      return;
    }
    el.innerHTML = rows.map(r => {
      const color = SC[r.dataset.status]||"#94a3b8";
      const name  = r.querySelector(".client-name")?.textContent||"—";
      const phone = r.querySelector(".phone-num")?.textContent||"—";
      const badge = r.querySelector(".badge")?.textContent||"";
      const dp = r.dataset.date?r.dataset.date.split("-"):[];
      const ds = dp.length===3?dp[2]+"/"+dp[1]+"/"+dp[0]:r.dataset.date;
      return '<div class="activity-item"><div class="act-dot" style="background:'+color+'"></div><div class="act-info"><div class="act-name">'+name+'</div><div class="act-detail">'+phone+' &middot; '+badge+'</div></div><div class="act-time">'+ds+' '+r.dataset.time+'</div></div>';
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
    goPage(1);
  }

  function goPage(p){
    const total=_pgVisible.length;
    const pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
    _pgCur=Math.min(Math.max(p,1),pages);
    const start=(_pgCur-1)*PAGE_SIZE;
    const end=start+PAGE_SIZE;
    _pgVisible.forEach((row,i)=>{ row.style.display=(i>=start&&i<end)?"":"none"; });
    _renderPagination(total,pages);
  }

  function _renderPagination(total,pages){
    const info=document.getElementById("pg-info");
    const btns=document.getElementById("pg-btns");
    if(total===0){ info.textContent="Nenhum registro encontrado"; btns.innerHTML=""; return; }
    const start=(_pgCur-1)*PAGE_SIZE+1;
    const end=Math.min(_pgCur*PAGE_SIZE,total);
    info.textContent=`Exibindo ${start}–${end} de ${total} registro${total!==1?"s":""}`;
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

  async function loadClients() {
    try {
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
        // Atualiza badge da sidebar
        const badge = document.querySelector('.nav-item[data-page="clientes"] .nav-badge');
        if (badge) badge.textContent = s.total ?? 0;
      }
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
        const st = clientReturnStatus(c.return_date);
        if (_clientFilter === "overdue"  && !st.cls.includes("overdue"))  return false;
        if (_clientFilter === "upcoming" && !st.cls.includes("upcoming")) return false;
        if (_clientFilter === "ok"       && !st.cls.includes("ok"))       return false;
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
    renderClientsTable(filtered);
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
    // Marca contato como ativo na lista
    document.querySelectorAll(".chat-contact-item").forEach(function(el){
      el.classList.toggle("active", el.dataset.phone === phone);
    });
    // Exibe painel de conversa
    var emptyEl  = document.getElementById("chat-conv-empty");
    var activeEl = document.getElementById("chat-active-conv");
    if (emptyEl)  emptyEl.style.display  = "none";
    if (activeEl) activeEl.style.display = "flex";
    document.getElementById("chat-layout").classList.add("conv-open");
    // Preenche header
    var contact  = _chatContacts.find(function(c){ return c.phone === phone; });
    var name     = (contact && contact.name) || phone.replace("@s.whatsapp.net","").replace("@lid","");
    var color    = _avatarColor(name);
    var initials = _avatarInitials(name);
    var avatarEl = document.getElementById("conv-avatar");
    if (avatarEl) { avatarEl.textContent = initials; avatarEl.style.background = color; }
    var nameEl   = document.getElementById("conv-name");
    var phoneEl  = document.getElementById("conv-phone");
    if (nameEl)  nameEl.textContent  = name;
    if (phoneEl) phoneEl.textContent = (contact && contact.display_phone) || "";
    // Carrega mensagens
    await loadChatMessages(phone, true);
    // Marca como lida
    await fetch("/admin/chat/read/" + encodeURIComponent(phone), {method:"POST",headers:authHeaders()});
    if (contact) { contact.unread_count = 0; renderChatContacts(); }
    var inputEl = document.getElementById("chat-input");
    if (inputEl) inputEl.focus();
  }


  async function loadChatMessages(phone, scroll) {
    var area = document.getElementById("chat-messages-area");
    if (!area) return;
    var atBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 80;
    try {
      var r = await fetch("/admin/chat/messages/" + encodeURIComponent(phone), {headers:authHeaders()});
      if (!r.ok) return;
      var msgs = await r.json();
      if (msgs.length === _chatLastMsgCount && !scroll) return;
      _chatLastMsgCount = msgs.length;
      area.innerHTML = _renderMsgBubbles(msgs);
      if (scroll || atBottom) area.scrollTop = area.scrollHeight;
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
      var tick   = !isUser ? '<span class="chat-tick">&#10003;&#10003;</span>' : "";
      if (!isUser) {
        var subCls  = isOp ? "chat-sub-label op" : "chat-sub-label";
        var subText = isOp ? "&#9997; Operador" : "&#129302; Liza";
        html += '<div class="' + subCls + '">' + subText + '</div>';
      }
      html += '<div class="chat-bubble ' + cls + '">' +
        _escHtml(msg.content) +
        '<div class="chat-bubble-meta">' +
          '<span class="chat-bubble-time">' + time + '</span>' + tick +
        '</div>' +
      '</div>';
    });
    return html || '<div style="text-align:center;color:var(--muted);font-size:.82rem;padding:2rem">Nenhuma mensagem ainda.</div>';
  }

  async function sendChatMsg() {
    var input = document.getElementById("chat-input");
    var text  = (input ? input.value : "").trim();
    if (!text || !_currentChatPhone) return;
    var btn   = document.getElementById("chat-send-btn");
    if (btn) btn.disabled = true;
    input.value = "";
    chatInputResize(input);
    try {
      var r = await fetch("/admin/chat/send", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({phone: _currentChatPhone, text: text})
      });
      if (r.ok) {
        await loadChatMessages(_currentChatPhone, true);
        await loadChatContacts();
      } else {
        showToast("Erro ao enviar mensagem.", false);
        input.value = text;
        chatInputResize(input);
      }
    } catch(e) {
      showToast("Erro: " + e.message, false);
      input.value = text;
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
        // Atualiza lista de contatos (inclui badge de nao lidas)
        await loadChatContacts();
        // Se a conversa aberta é do remetente, carrega mensagens novas
        if (_currentChatPhone && _currentChatPhone === data.phone) {
          await loadChatMessages(_currentChatPhone, false);
          // Marca como lida automaticamente
          await fetch("/admin/chat/read/" + encodeURIComponent(_currentChatPhone), {method:"POST",headers:authHeaders()});
          var contact = _chatContacts.find(function(c){ return c.phone === _currentChatPhone; });
          if (contact) { contact.unread_count = 0; renderChatContacts(); }
        }
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

  /* Init */
  (function(){
    const lp=localStorage.getItem("lastPage")||"dashboard";navTo(lp);
    if(localStorage.getItem("sbCollapsed")==="1")document.getElementById("sidebar").classList.add("collapsed");
    renderStatusBreakdown();renderUpcoming();
  })();
