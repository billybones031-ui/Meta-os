"""
HTML for the Meta-OS web UI.
Served at GET / by app/main.py.

Design goals:
  - Mobile-first, works on phone and laptop
  - Dark theme, readable at a glance
  - WebSocket chat with auto-reconnect
  - Loads full history on connect (shared across devices)
  - Shows which backend handled each message
  - Swipe-friendly, big tap targets on mobile
"""

CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Meta-OS</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #0d1117;
    --surface:  #161b22;
    --border:   #30363d;
    --text:     #e6edf3;
    --muted:    #8b949e;
    --accent:   #58a6ff;
    --green:    #3fb950;
    --yellow:   #e3b341;
    --red:      #f85149;
    --user-bg:  #1f6feb;
    --bot-bg:   #21262d;
    --radius:   12px;
  }

  html, body {
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    font-size: 15px;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Layout ── */
  #app {
    display: flex;
    flex-direction: column;
    height: 100dvh;        /* dynamic viewport — accounts for mobile browser chrome */
    max-width: 800px;
    margin: 0 auto;
  }

  /* ── Header ── */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: .75rem 1rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    gap: .5rem;
  }
  header h1 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: .02em;
  }
  #status-dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    background: var(--muted);
    flex-shrink: 0;
    transition: background .3s;
  }
  #status-dot.connected  { background: var(--green); }
  #status-dot.connecting { background: var(--yellow); }
  #status-dot.error      { background: var(--red); }

  #status-label {
    font-size: .75rem;
    color: var(--muted);
    margin-right: auto;
    margin-left: .35rem;
  }

  #clear-btn {
    background: none;
    border: 1px solid var(--border);
    color: var(--muted);
    border-radius: 6px;
    padding: .3rem .65rem;
    font-size: .75rem;
    cursor: pointer;
    transition: border-color .2s, color .2s;
  }
  #clear-btn:hover { border-color: var(--red); color: var(--red); }

  #dashboard-link {
    font-size: .75rem;
    color: var(--muted);
    text-decoration: none;
    padding: .3rem .5rem;
    border: 1px solid var(--border);
    border-radius: 6px;
    transition: color .2s, border-color .2s;
  }
  #dashboard-link:hover { color: var(--accent); border-color: var(--accent); }

  /* ── Messages ── */
  #messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: .6rem;
    scroll-behavior: smooth;
    overscroll-behavior: contain;
  }

  /* ── Individual message ── */
  .msg {
    display: flex;
    flex-direction: column;
    max-width: 82%;
    gap: .2rem;
    animation: fadeIn .15s ease;
  }
  @keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:none; } }

  .msg.user     { align-self: flex-end; align-items: flex-end; }
  .msg.assistant,
  .msg.system,
  .msg.confirm  { align-self: flex-start; align-items: flex-start; }

  .bubble {
    padding: .6rem .9rem;
    border-radius: var(--radius);
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .msg.user     .bubble { background: var(--user-bg); color: #fff; border-bottom-right-radius: 3px; }
  .msg.assistant .bubble { background: var(--bot-bg); border: 1px solid var(--border); border-bottom-left-radius: 3px; }
  .msg.system   .bubble { background: transparent; color: var(--muted); font-size: .8rem; border: none; padding: .2rem .4rem; }
  .msg.confirm  .bubble { background: #2d1f00; border: 1px solid var(--yellow); color: var(--yellow); border-bottom-left-radius: 3px; }

  .meta-row {
    display: flex;
    gap: .4rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .ts { font-size: .68rem; color: var(--muted); }
  .backend-tag {
    font-size: .65rem;
    padding: .1rem .4rem;
    border-radius: 4px;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--muted);
    font-family: monospace;
    text-transform: uppercase;
    letter-spacing: .04em;
  }
  .backend-tag.n8n    { border-color: #58a6ff44; color: var(--accent); }
  .backend-tag.ollama { border-color: #3fb95044; color: var(--green); }
  .backend-tag.crewai { border-color: #e3b34144; color: var(--yellow); }
  .backend-tag.hitl   { border-color: #f8514944; color: var(--red); }

  /* ── Typing indicator ── */
  #typing {
    display: none;
    align-self: flex-start;
    padding: .5rem .9rem;
    background: var(--bot-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    border-bottom-left-radius: 3px;
    gap: .3rem;
  }
  #typing.show { display: flex; }
  #typing span {
    width: 7px; height: 7px;
    background: var(--muted);
    border-radius: 50%;
    animation: bounce .9s ease-in-out infinite;
  }
  #typing span:nth-child(2) { animation-delay: .15s; }
  #typing span:nth-child(3) { animation-delay: .3s; }
  @keyframes bounce { 0%,60%,100% { transform:translateY(0); } 30% { transform:translateY(-5px); } }

  /* ── Input bar ── */
  #input-bar {
    display: flex;
    gap: .5rem;
    padding: .75rem 1rem;
    background: var(--surface);
    border-top: 1px solid var(--border);
    flex-shrink: 0;
  }

  #input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 1rem;
    padding: .6rem .85rem;
    resize: none;
    max-height: 130px;
    line-height: 1.4;
    outline: none;
    transition: border-color .2s;
    font-family: inherit;
  }
  #input:focus { border-color: var(--accent); }
  #input::placeholder { color: var(--muted); }

  #send-btn {
    background: var(--accent);
    border: none;
    border-radius: var(--radius);
    color: #000;
    font-size: 1.2rem;
    width: 44px;
    min-width: 44px;
    cursor: pointer;
    transition: opacity .2s;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  #send-btn:disabled { opacity: .4; cursor: default; }
  #send-btn:not(:disabled):hover { opacity: .85; }

  /* ── Empty state ── */
  #empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    gap: .5rem;
    pointer-events: none;
    user-select: none;
  }
  #empty svg { opacity: .25; }
  #empty p { font-size: .9rem; }

  /* ── Responsive: desktop gets a bit more padding ── */
  @media (min-width: 600px) {
    #messages { padding: 1.25rem 1.5rem; }
    #input-bar { padding: 1rem 1.5rem; }
    header { padding: .85rem 1.5rem; }
    header h1 { font-size: 1.05rem; }
  }

  /* ── Scrollbar (webkit) ── */
  #messages::-webkit-scrollbar { width: 4px; }
  #messages::-webkit-scrollbar-track { background: transparent; }
  #messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
</head>
<body>
<div id="app">

  <header>
    <div id="status-dot" class="connecting"></div>
    <span id="status-label">connecting…</span>
    <h1>Meta-OS</h1>
    <a href="/dashboard" id="dashboard-link" target="_blank">logs</a>
    <button id="clear-btn" title="Clear history">clear</button>
  </header>

  <div id="messages">
    <div id="empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      <p>Send a task to get started.</p>
    </div>
    <div id="typing"><span></span><span></span><span></span></div>
  </div>

  <div id="input-bar">
    <textarea id="input" rows="1" placeholder="Send a task…" autocomplete="off" spellcheck="true"></textarea>
    <button id="send-btn" disabled>&#10148;</button>
  </div>

</div>

<script>
(function () {
  const messagesEl = document.getElementById('messages');
  const inputEl    = document.getElementById('input');
  const sendBtn    = document.getElementById('send-btn');
  const statusDot  = document.getElementById('status-dot');
  const statusLbl  = document.getElementById('status-label');
  const typingEl   = document.getElementById('typing');
  const emptyEl    = document.getElementById('empty');
  const clearBtn   = document.getElementById('clear-btn');

  let ws = null;
  let reconnectDelay = 1000;

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function fmtTs(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function hideEmpty() { emptyEl.style.display = 'none'; }

  function appendMsg(role, content, meta, ts) {
    hideEmpty();
    // Move typing indicator to end always
    typingEl.parentNode.appendChild(typingEl);

    const div = document.createElement('div');
    div.className = `msg ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = content;
    div.appendChild(bubble);

    const metaRow = document.createElement('div');
    metaRow.className = 'meta-row';

    const tsSpan = document.createElement('span');
    tsSpan.className = 'ts';
    tsSpan.textContent = fmtTs(ts || new Date().toISOString());
    metaRow.appendChild(tsSpan);

    if (meta && meta.backend) {
      const tag = document.createElement('span');
      tag.className = `backend-tag ${meta.backend}`;
      tag.textContent = meta.backend;
      metaRow.appendChild(tag);
    }

    div.appendChild(metaRow);
    messagesEl.insertBefore(div, typingEl);
    scrollToBottom();
    return div;
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setStatus(state, label) {
    statusDot.className = state;
    statusLbl.textContent = label;
  }

  function showTyping() { typingEl.classList.add('show'); scrollToBottom(); }
  function hideTyping() { typingEl.classList.remove('show'); }

  // ── Load history ────────────────────────────────────────────────────────────

  function renderHistory(messages) {
    // Remove all existing message divs (keep empty + typing)
    Array.from(messagesEl.children).forEach(el => {
      if (el !== emptyEl && el !== typingEl) el.remove();
    });
    if (messages.length === 0) {
      emptyEl.style.display = '';
      return;
    }
    hideEmpty();
    messages.forEach(m => appendMsg(m.role, m.content, m.meta, m.ts));
  }

  // ── WebSocket ────────────────────────────────────────────────────────────────

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url   = `${proto}://${location.host}/ws`;
    setStatus('connecting', 'connecting…');

    ws = new WebSocket(url);

    ws.onopen = () => {
      setStatus('connected', 'connected');
      sendBtn.disabled = false;
      reconnectDelay = 1000;
    };

    ws.onclose = () => {
      setStatus('error', 'reconnecting…');
      sendBtn.disabled = true;
      hideTyping();
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 16000);
    };

    ws.onerror = () => ws.close();

    ws.onmessage = (e) => {
      let data;
      try { data = JSON.parse(e.data); } catch { return; }

      hideTyping();

      if (data.type === 'history') {
        renderHistory(data.messages);
        return;
      }
      if (data.type === 'assistant') {
        appendMsg('assistant', data.content, data.meta);
        return;
      }
      if (data.type === 'confirm') {
        appendMsg('confirm', data.content, null);
        return;
      }
      if (data.type === 'system') {
        appendMsg('system', data.content, null);
        return;
      }
    };
  }

  // ── Send ─────────────────────────────────────────────────────────────────────

  function send() {
    const text = inputEl.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    appendMsg('user', text);
    ws.send(JSON.stringify({ text }));

    inputEl.value = '';
    inputEl.style.height = 'auto';
    showTyping();
  }

  sendBtn.addEventListener('click', send);

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  // Auto-grow textarea
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 130) + 'px';
    sendBtn.disabled = !inputEl.value.trim();
  });

  // ── Clear history ─────────────────────────────────────────────────────────

  clearBtn.addEventListener('click', async () => {
    if (!confirm('Clear all conversation history?')) return;
    await fetch('/history', { method: 'DELETE' });
    renderHistory([]);
  });

  // ── Boot ─────────────────────────────────────────────────────────────────────

  connect();
})();
</script>
</body>
</html>"""


# ── Log dashboard (existing) ─────────────────────────────────────────────────

LOG_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Meta-OS — Logs</title>
  <style>
    body { background:#0d1117; color:#c9d1d9; font-family:monospace; padding:1rem; }
    h1   { color:#58a6ff; margin-bottom:.5rem; font-size:1rem; }
    a    { color:#8b949e; font-size:.8rem; text-decoration:none; }
    a:hover { color:#58a6ff; }
    #log { height:90vh; overflow-y:auto; border:1px solid #30363d;
           padding:.5rem; border-radius:4px; font-size:.78rem; }
    .info  { color:#c9d1d9; }
    .warn  { color:#e3b341; }
    .error { color:#f85149; }
  </style>
</head>
<body>
<h1>Meta-OS — Live Logs &nbsp;<a href="/">← chat</a></h1>
<div id="log"></div>
<script>
  const box = document.getElementById('log');
  const es  = new EventSource('/stream');
  es.onmessage = e => {
    try {
      const o = JSON.parse(e.data);
      const d = document.createElement('div');
      d.className = o.level || 'info';
      d.textContent = `[${(o.ts||'').slice(11,19)}] [${o.source||'-'}] ${o.message}`;
      box.appendChild(d);
      box.scrollTop = box.scrollHeight;
    } catch (_) {}
  };
</script>
</body>
</html>"""
