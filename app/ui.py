"""HTML for the Meta-OS web UI — served at GET / by app/main.py."""

CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Meta-OS</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d1117;--surface:#161b22;--surface2:#1c2128;
  --border:#30363d;--text:#e6edf3;--muted:#8b949e;
  --accent:#58a6ff;--green:#3fb950;--yellow:#e3b341;--red:#f85149;--purple:#bc8cff;
  --user-bg:#1f6feb;--bot-bg:#21262d;--r:12px;
}
html,body{height:100%;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  font-size:15px;-webkit-font-smoothing:antialiased;overscroll-behavior:none}

/* ── App shell ── */
#app{display:flex;flex-direction:column;height:100dvh;max-width:860px;margin:0 auto}

/* ── Header ── */
header{display:flex;align-items:center;gap:.5rem;padding:.7rem 1rem;
  background:var(--surface);border-bottom:1px solid var(--border);flex-shrink:0}
header h1{font-size:.95rem;font-weight:700;color:var(--accent);letter-spacing:.03em;margin-right:auto}
#status-dot{width:9px;height:9px;border-radius:50%;background:var(--muted);flex-shrink:0;transition:background .3s}
#status-dot.connected{background:var(--green)}
#status-dot.connecting{background:var(--yellow);animation:pulse 1s infinite}
#status-dot.error{background:var(--red)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
#status-label{font-size:.7rem;color:var(--muted)}
.hdr-btn{background:none;border:1px solid var(--border);color:var(--muted);border-radius:6px;
  padding:.25rem .6rem;font-size:.7rem;cursor:pointer;transition:color .2s,border-color .2s;white-space:nowrap}
.hdr-btn:hover{color:var(--accent);border-color:var(--accent)}

/* ── Tab bar ── */
#tab-bar{display:flex;background:var(--surface);border-bottom:1px solid var(--border);flex-shrink:0}
.tab{flex:1;padding:.65rem .5rem;background:none;border:none;color:var(--muted);
  font-size:.8rem;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:.35rem;
  border-bottom:2px solid transparent;transition:color .2s,border-color .2s;font-family:inherit}
.tab svg{width:15px;height:15px;flex-shrink:0}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab:hover:not(.active){color:var(--text)}

/* ── Panels ── */
.panel{flex:1;overflow:hidden;display:none;flex-direction:column}
.panel.active{display:flex}

/* ════════════════════════════════ CHAT ════════════════════════════════ */
#messages{flex:1;overflow-y:auto;padding:1rem;display:flex;flex-direction:column;
  gap:.55rem;scroll-behavior:smooth;overscroll-behavior:contain}
#messages::-webkit-scrollbar{width:3px}
#messages::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}

.msg{display:flex;flex-direction:column;max-width:84%;gap:.15rem;animation:fadeIn .15s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.msg.user{align-self:flex-end;align-items:flex-end}
.msg.assistant,.msg.system,.msg.confirm{align-self:flex-start;align-items:flex-start}
.bubble{padding:.55rem .85rem;border-radius:var(--r);line-height:1.5;white-space:pre-wrap;word-break:break-word}
.msg.user .bubble{background:var(--user-bg);color:#fff;border-bottom-right-radius:3px}
.msg.assistant .bubble{background:var(--bot-bg);border:1px solid var(--border);border-bottom-left-radius:3px}
.msg.system .bubble{background:transparent;color:var(--muted);font-size:.75rem;padding:.15rem .4rem;border:none}
.msg.confirm .bubble{background:#2d1f00;border:1px solid var(--yellow);color:var(--yellow);border-bottom-left-radius:3px}

.meta-row{display:flex;gap:.35rem;align-items:center;flex-wrap:wrap}
.ts{font-size:.65rem;color:var(--muted)}
.btag{font-size:.6rem;padding:.1rem .35rem;border-radius:4px;background:var(--surface);
  border:1px solid var(--border);color:var(--muted);font-family:monospace;text-transform:uppercase;letter-spacing:.04em}
.btag.n8n{border-color:#58a6ff44;color:var(--accent)}
.btag.ollama{border-color:#3fb95044;color:var(--green)}
.btag.crewai{border-color:#e3b34144;color:var(--yellow)}
.btag.hitl{border-color:#f8514944;color:var(--red)}

#typing{display:none;align-self:flex-start;padding:.5rem .85rem;background:var(--bot-bg);
  border:1px solid var(--border);border-radius:var(--r);border-bottom-left-radius:3px;gap:.3rem}
#typing.show{display:flex}
#typing span{width:6px;height:6px;background:var(--muted);border-radius:50%;animation:bounce .9s ease-in-out infinite}
#typing span:nth-child(2){animation-delay:.15s}
#typing span:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}

#empty{display:flex;flex-direction:column;align-items:center;justify-content:center;
  flex:1;color:var(--muted);gap:.5rem;pointer-events:none;user-select:none}
#empty svg{opacity:.2}
#empty p{font-size:.85rem}

#input-bar{display:flex;gap:.5rem;padding:.7rem 1rem;background:var(--surface);
  border-top:1px solid var(--border);flex-shrink:0}
#input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:var(--r);
  color:var(--text);font-size:1rem;padding:.55rem .8rem;resize:none;max-height:120px;
  line-height:1.4;outline:none;transition:border-color .2s;font-family:inherit}
#input:focus{border-color:var(--accent)}
#input::placeholder{color:var(--muted)}
#send-btn{background:var(--accent);border:none;border-radius:var(--r);color:#000;
  font-size:1.15rem;width:44px;min-width:44px;cursor:pointer;transition:opacity .2s;
  display:flex;align-items:center;justify-content:center}
#send-btn:disabled{opacity:.35;cursor:default}

/* ════════════════════════════════ STATS ════════════════════════════════ */
#stats-panel{overflow-y:auto;padding:1rem;gap:1rem}
#stats-panel::-webkit-scrollbar{width:3px}
#stats-panel::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}

.stat-cards{display:grid;grid-template-columns:repeat(2,1fr);gap:.65rem}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:.85rem 1rem;display:flex;flex-direction:column;gap:.25rem;position:relative;overflow:hidden}
.card::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,transparent 60%,rgba(255,255,255,.02));pointer-events:none}
.card-label{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.card-value{font-size:1.8rem;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}
.card-sub{font-size:.7rem;color:var(--muted)}
.card.blue .card-value{color:var(--accent)}
.card.green .card-value{color:var(--green)}
.card.yellow .card-value{color:var(--yellow)}
.card.purple .card-value{color:var(--purple)}

.chart-block{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:.9rem 1rem}
.chart-block h3{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:.75rem}
.chart-wrap{position:relative;height:140px}
.chart-wrap.tall{height:200px}

/* live pulse bar */
#pulse-bar{height:3px;background:var(--border);border-radius:2px;overflow:hidden;margin-top:.5rem}
#pulse-fill{height:100%;width:0%;background:var(--green);transition:width .4s ease;border-radius:2px}

/* ════════════════════════════════ TASKS ════════════════════════════════ */
#tasks-panel{overflow-y:auto;padding:1rem;gap:.75rem}
#tasks-panel::-webkit-scrollbar{width:3px}
#tasks-panel::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}

#task-add{display:flex;gap:.5rem}
#task-input{flex:1;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  color:var(--text);font-size:.9rem;padding:.55rem .85rem;outline:none;transition:border-color .2s;font-family:inherit}
#task-input:focus{border-color:var(--accent)}
#task-input::placeholder{color:var(--muted)}
#task-add-btn{background:var(--accent);border:none;border-radius:var(--r);color:#000;
  font-size:1.2rem;width:42px;min-width:42px;cursor:pointer;transition:opacity .2s;
  display:flex;align-items:center;justify-content:center}
#task-add-btn:hover{opacity:.85}

.progress-row{display:flex;align-items:center;gap:.75rem}
.progress-wrap{flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden}
#progress-fill{height:100%;width:0%;background:var(--green);transition:width .5s ease;border-radius:3px}
#progress-label{font-size:.72rem;color:var(--muted);white-space:nowrap;min-width:50px;text-align:right}

#task-list{display:flex;flex-direction:column;gap:.45rem}

.todo-item{display:flex;align-items:flex-start;gap:.65rem;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--r);padding:.7rem .85rem;
  transition:opacity .2s,border-color .2s;animation:fadeIn .15s ease}
.todo-item.done{opacity:.45}
.todo-item.done .todo-text{text-decoration:line-through;color:var(--muted)}
.todo-cb{width:18px;height:18px;min-width:18px;border-radius:5px;border:2px solid var(--border);
  background:none;cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:background .15s,border-color .15s;margin-top:1px;flex-shrink:0}
.todo-item.done .todo-cb{background:var(--green);border-color:var(--green)}
.todo-cb svg{display:none;width:10px;height:10px}
.todo-item.done .todo-cb svg{display:block}
.todo-text{flex:1;font-size:.88rem;line-height:1.4;word-break:break-word}
.todo-ts{font-size:.65rem;color:var(--muted);white-space:nowrap;margin-top:2px}
.todo-del{background:none;border:none;color:var(--border);cursor:pointer;font-size:1rem;
  padding:.1rem .3rem;transition:color .2s;flex-shrink:0;align-self:center}
.todo-del:hover{color:var(--red)}

#tasks-empty{display:flex;flex-direction:column;align-items:center;padding:2rem 1rem;
  color:var(--muted);gap:.5rem;font-size:.85rem}
#tasks-empty svg{opacity:.2}

/* ── Responsive ── */
@media(min-width:600px){
  #messages,#stats-panel,#tasks-panel,#input-bar,header,#tab-bar{padding-left:1.5rem;padding-right:1.5rem}
  .stat-cards{grid-template-columns:repeat(4,1fr)}
}
</style>
</head>
<body>
<div id="app">

  <!-- Header -->
  <header>
    <div id="status-dot" class="connecting"></div>
    <span id="status-label">connecting</span>
    <h1>Meta-OS</h1>
    <a href="/dashboard" class="hdr-btn" target="_blank" style="text-decoration:none">logs</a>
    <button class="hdr-btn" id="clear-btn">clear</button>
  </header>

  <!-- Tab bar -->
  <div id="tab-bar">
    <button class="tab active" data-tab="chat">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      Chat
    </button>
    <button class="tab" data-tab="stats">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      Stats
    </button>
    <button class="tab" data-tab="tasks">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      Tasks
    </button>
  </div>

  <!-- ── Chat panel ── -->
  <div class="panel active" id="chat-panel">
    <div id="messages">
      <div id="empty">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <p>Send a task to get started.</p>
      </div>
      <div id="typing"><span></span><span></span><span></span></div>
    </div>
    <div id="input-bar">
      <textarea id="input" rows="1" placeholder="Send a task…" autocomplete="off" spellcheck="true"></textarea>
      <button id="send-btn" disabled>&#10148;</button>
    </div>
  </div>

  <!-- ── Stats panel ── -->
  <div class="panel" id="stats-panel">
    <div class="stat-cards">
      <div class="card blue"><span class="card-label">Total Tasks</span><span class="card-value" id="s-total">—</span><span class="card-sub">all time</span></div>
      <div class="card green"><span class="card-label">Today</span><span class="card-value" id="s-today">—</span><span class="card-sub">messages</span></div>
      <div class="card yellow"><span class="card-label">Tasks Done</span><span class="card-value" id="s-done">—</span><span class="card-sub">of <span id="s-todos-total">0</span></span></div>
      <div class="card purple"><span class="card-label">Backends</span><span class="card-value" id="s-backends">—</span><span class="card-sub">active</span></div>
    </div>

    <div class="chart-block">
      <h3>Activity — last 24 h</h3>
      <div class="chart-wrap tall"><canvas id="hourly-chart"></canvas></div>
      <div id="pulse-bar"><div id="pulse-fill"></div></div>
    </div>

    <div class="chart-block">
      <h3>Backend distribution</h3>
      <div class="chart-wrap" style="height:160px;display:flex;align-items:center;justify-content:center">
        <canvas id="backend-chart" style="max-height:160px;max-width:260px"></canvas>
      </div>
    </div>
  </div>

  <!-- ── Tasks panel ── -->
  <div class="panel" id="tasks-panel">
    <div id="task-add">
      <input id="task-input" type="text" placeholder="Add a task…" autocomplete="off">
      <button id="task-add-btn">+</button>
    </div>
    <div class="progress-row">
      <div class="progress-wrap"><div id="progress-fill"></div></div>
      <span id="progress-label">0 / 0</span>
    </div>
    <div id="task-list">
      <div id="tasks-empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        <p>No tasks yet.</p>
      </div>
    </div>
  </div>

</div><!-- #app -->

<script>
(function(){
'use strict';

/* ── Utils ─────────────────────────────────────────────────────────────── */
const $  = id => document.getElementById(id);
const fmtTs = iso => iso ? new Date(iso).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}) : '';
const fmtDate = iso => iso ? new Date(iso).toLocaleDateString([],{month:'short',day:'numeric'}) : '';

/* ── Tab switching ─────────────────────────────────────────────────────── */
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $(`${btn.dataset.tab}-panel`).classList.add('active');
    if(btn.dataset.tab === 'stats') refreshStats();
    if(btn.dataset.tab === 'tasks') loadTodos();
  });
});

/* ════════════════════════ CHAT ════════════════════════════════════════ */
const messagesEl = $('messages'), inputEl = $('input'), sendBtn = $('send-btn');
const statusDot = $('status-dot'), statusLbl = $('status-label');
const typingEl = $('typing'), emptyEl = $('empty');

let ws = null, reconnectDelay = 1000;

function setStatus(s, l){ statusDot.className = s; statusLbl.textContent = l; }

function hideEmpty(){ emptyEl.style.display = 'none'; }

function appendMsg(role, content, meta, ts){
  hideEmpty();
  messagesEl.insertBefore(buildMsg(role,content,meta,ts), typingEl);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function buildMsg(role, content, meta, ts){
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = content;
  div.appendChild(bubble);
  const row = document.createElement('div');
  row.className = 'meta-row';
  const tspan = document.createElement('span');
  tspan.className = 'ts';
  tspan.textContent = fmtTs(ts || new Date().toISOString());
  row.appendChild(tspan);
  if(meta && meta.backend){
    const tag = document.createElement('span');
    tag.className = `btag ${meta.backend}`;
    tag.textContent = meta.backend;
    row.appendChild(tag);
  }
  div.appendChild(row);
  return div;
}

function renderHistory(msgs){
  Array.from(messagesEl.children).forEach(el => {
    if(el !== emptyEl && el !== typingEl) el.remove();
  });
  if(!msgs.length){ emptyEl.style.display=''; return; }
  hideEmpty();
  msgs.forEach(m => messagesEl.insertBefore(buildMsg(m.role, m.content, m.meta, m.ts), typingEl));
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showTyping(){ typingEl.classList.add('show'); messagesEl.scrollTop = messagesEl.scrollHeight; }
function hideTyping(){ typingEl.classList.remove('show'); }

function connect(){
  const proto = location.protocol==='https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  setStatus('connecting','connecting…');

  ws.onopen = () => { setStatus('connected','connected'); sendBtn.disabled=false; reconnectDelay=1000; };
  ws.onclose = () => {
    setStatus('error','reconnecting…'); sendBtn.disabled=true; hideTyping();
    setTimeout(connect, reconnectDelay); reconnectDelay=Math.min(reconnectDelay*2,16000);
  };
  ws.onerror = () => ws.close();
  ws.onmessage = e => {
    let d; try{ d=JSON.parse(e.data); }catch{ return; }
    hideTyping();
    if(d.type==='history'){ renderHistory(d.messages); return; }
    if(d.type==='assistant'){ appendMsg('assistant',d.content,d.meta); return; }
    if(d.type==='confirm'){  appendMsg('confirm',d.content,null); return; }
    if(d.type==='system'){   appendMsg('system',d.content,null); return; }
  };
}

function send(){
  const text = inputEl.value.trim();
  if(!text || !ws || ws.readyState!==WebSocket.OPEN) return;
  appendMsg('user', text);
  ws.send(JSON.stringify({text}));
  inputEl.value=''; inputEl.style.height='auto'; showTyping();
}

sendBtn.addEventListener('click', send);
inputEl.addEventListener('keydown', e => { if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); } });
inputEl.addEventListener('input', () => {
  inputEl.style.height='auto';
  inputEl.style.height=Math.min(inputEl.scrollHeight,120)+'px';
  sendBtn.disabled=!inputEl.value.trim();
});

$('clear-btn').addEventListener('click', async () => {
  if(!confirm('Clear all conversation history?')) return;
  await fetch('/history',{method:'DELETE'});
  renderHistory([]);
});

connect();

/* ════════════════════════ STATS ═══════════════════════════════════════ */
let hourlyChart = null, backendChart = null;
const BACKEND_COLORS = {
  n8n:    '#58a6ff',
  ollama: '#3fb950',
  crewai: '#e3b341',
  hitl:   '#f85149',
  other:  '#8b949e',
};

function animateCounter(el, target){
  const start = parseInt(el.textContent) || 0;
  if(start === target){ el.textContent = target; return; }
  const duration = 600, startTime = performance.now();
  function step(now){
    const t = Math.min((now-startTime)/duration, 1);
    el.textContent = Math.round(start + (target-start)*t);
    if(t<1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function buildHourlyChart(hourly){
  const labels = Array.from({length:24},(_,i)=>String(i).padStart(2,'0')+':00');
  const data   = labels.map((_,i)=> hourly[String(i).padStart(2,'0')] || 0);
  const ctx    = $('hourly-chart').getContext('2d');
  if(hourlyChart){ hourlyChart.data.datasets[0].data=data; hourlyChart.update('none'); return; }
  hourlyChart = new Chart(ctx,{
    type:'bar',
    data:{
      labels,
      datasets:[{
        data,
        backgroundColor:'rgba(88,166,255,.35)',
        borderColor:'rgba(88,166,255,.9)',
        borderWidth:1,
        borderRadius:3,
        hoverBackgroundColor:'rgba(88,166,255,.6)',
      }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:{duration:600,easing:'easeOutQuart'},
      plugins:{legend:{display:false},tooltip:{
        callbacks:{label:c=>`${c.raw} task${c.raw!==1?'s':''}`}
      }},
      scales:{
        x:{ticks:{color:'#8b949e',font:{size:9},maxRotation:0,
             callback(v,i){ return i%4===0?this.getLabelForValue(i):''; }},
          grid:{color:'rgba(48,54,61,.6)'}},
        y:{ticks:{color:'#8b949e',font:{size:10},stepSize:1},
          grid:{color:'rgba(48,54,61,.6)'},beginAtZero:true},
      }
    }
  });
}

function buildBackendChart(backends){
  const keys = Object.keys(backends).length ? Object.keys(backends) : ['none'];
  const vals = keys.map(k => backends[k]||0);
  const colors = keys.map(k => BACKEND_COLORS[k]||BACKEND_COLORS.other);
  const ctx = $('backend-chart').getContext('2d');
  if(backendChart){
    backendChart.data.labels=keys;
    backendChart.data.datasets[0].data=vals;
    backendChart.data.datasets[0].backgroundColor=colors;
    backendChart.update(); return;
  }
  backendChart = new Chart(ctx,{
    type:'doughnut',
    data:{labels:keys, datasets:[{data:vals, backgroundColor:colors, borderColor:'#0d1117', borderWidth:3, hoverOffset:8}]},
    options:{
      responsive:true, maintainAspectRatio:false,
      animation:{animateRotate:true,duration:800},
      plugins:{
        legend:{position:'bottom',labels:{color:'#c9d1d9',font:{size:11},padding:12,boxWidth:12}},
        tooltip:{callbacks:{label:c=>`${c.label}: ${c.raw}`}}
      },
      cutout:'62%',
    }
  });
}

function updatePulse(today){
  const max = Math.max(today, 10);
  const pct = Math.min((today/max)*100, 100);
  $('pulse-fill').style.width = pct + '%';
  $('pulse-fill').style.background = today > 20 ? '#f85149' : today > 10 ? '#e3b341' : '#3fb950';
}

async function refreshStats(){
  try{
    const r = await fetch('/stats');
    const s = await r.json();
    animateCounter($('s-total'), s.total_messages || 0);
    animateCounter($('s-today'), s.today_messages || 0);
    animateCounter($('s-done'),  s.todos_done || 0);
    $('s-todos-total').textContent = s.todos_total || 0;
    animateCounter($('s-backends'), Object.keys(s.backends||{}).length);
    buildHourlyChart(s.hourly || {});
    buildBackendChart(s.backends || {});
    updatePulse(s.today_messages || 0);
  }catch(e){ console.warn('stats error',e); }
}

// Auto-refresh stats every 8s when tab is active
setInterval(()=>{
  const active = document.querySelector('.tab.active');
  if(active && active.dataset.tab === 'stats') refreshStats();
}, 8000);

/* ════════════════════════ TASKS ═══════════════════════════════════════ */
async function loadTodos(){
  const todos = await fetch('/todos').then(r=>r.json()).catch(()=>[]);
  renderTodos(todos);
}

function renderTodos(todos){
  const list = $('task-list');
  Array.from(list.children).forEach(el=>{ if(el.id!=='tasks-empty') el.remove(); });
  const empty = $('tasks-empty');

  if(!todos.length){ empty.style.display=''; updateProgress(0,0); return; }
  empty.style.display='none';
  const done = todos.filter(t=>t.done).length;
  updateProgress(done, todos.length);

  todos.forEach(t => list.insertBefore(buildTodoEl(t), empty));
}

function updateProgress(done, total){
  const pct = total ? Math.round((done/total)*100) : 0;
  $('progress-fill').style.width = pct + '%';
  $('progress-fill').style.background = pct===100 ? '#3fb950' : pct > 60 ? '#58a6ff' : '#8b949e';
  $('progress-label').textContent = `${done} / ${total}`;
}

function buildTodoEl(t){
  const el = document.createElement('div');
  el.className = `todo-item${t.done?' done':''}`;
  el.dataset.id = t.id;

  el.innerHTML = `
    <button class="todo-cb" title="Toggle done">
      <svg viewBox="0 0 12 12" fill="none" stroke="#fff" stroke-width="2.5"><polyline points="1.5 6 4.5 9 10.5 3"/></svg>
    </button>
    <div style="flex:1;min-width:0">
      <div class="todo-text">${escHtml(t.content)}</div>
      <div class="todo-ts">${fmtDate(t.created_at)}${t.done_at?' · done '+fmtDate(t.done_at):''}</div>
    </div>
    <button class="todo-del" title="Delete">×</button>`;

  el.querySelector('.todo-cb').addEventListener('click', async ()=>{
    await fetch(`/todos/${t.id}`,{method:'PATCH'});
    loadTodos();
  });
  el.querySelector('.todo-del').addEventListener('click', async ()=>{
    el.style.opacity='0'; el.style.transform='translateX(20px)'; el.style.transition='all .2s';
    await new Promise(r=>setTimeout(r,180));
    await fetch(`/todos/${t.id}`,{method:'DELETE'});
    loadTodos();
  });
  return el;
}

function escHtml(s){
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function addTodo(){
  const inp = $('task-input');
  const text = inp.value.trim();
  if(!text) return;
  inp.value='';
  await fetch('/todos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:text})});
  loadTodos();
}

$('task-add-btn').addEventListener('click', addTodo);
$('task-input').addEventListener('keydown', e=>{ if(e.key==='Enter') addTodo(); });

loadTodos();

})();
</script>
</body>
</html>"""


LOG_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Meta-OS — Logs</title>
  <style>
    body{background:#0d1117;color:#c9d1d9;font-family:monospace;padding:1rem}
    h1{color:#58a6ff;margin-bottom:.5rem;font-size:.95rem}
    a{color:#8b949e;font-size:.8rem;text-decoration:none}
    a:hover{color:#58a6ff}
    #log{height:90vh;overflow-y:auto;border:1px solid #30363d;padding:.5rem;border-radius:4px;font-size:.75rem}
    .info{color:#c9d1d9}.warn{color:#e3b341}.error{color:#f85149}
  </style>
</head>
<body>
<h1>Meta-OS — Live Logs &nbsp;<a href="/">← chat</a></h1>
<div id="log"></div>
<script>
  const box=document.getElementById('log');
  const es=new EventSource('/stream');
  es.onmessage=e=>{
    try{const o=JSON.parse(e.data);const d=document.createElement('div');
    d.className=o.level||'info';d.textContent=`[${(o.ts||'').slice(11,19)}] [${o.source||'-'}] ${o.message}`;
    box.appendChild(d);box.scrollTop=box.scrollHeight;}catch(_){}
  };
</script>
</body>
</html>"""
