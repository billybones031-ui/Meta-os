"""
Meta-OS FastAPI gateway — port 8000

Endpoints:
  POST /run         — classify, route, execute
  GET  /health      — liveness probe
  GET  /stream      — SSE stream of observer logs
  GET  /dashboard   — minimal HTML dashboard (SSE consumer)
"""

from __future__ import annotations

import asyncio
import httpx
import os
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from orchestrator.router import route_and_execute
from orchestrator import memory as mem

app = FastAPI(title="Meta-OS", version="3.2.0")

OBSERVER_URL = os.getenv("OBSERVER_URL", "http://localhost:8081")


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #

class TaskRequest(BaseModel):
    task: str
    user_id: str = "default"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

async def _log(message: str, level: str = "info", source: str = "api") -> None:
    """Fire-and-forget: post a log entry to the Go observer."""
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            await client.post(
                f"{OBSERVER_URL}/log",
                json={"level": level, "source": source, "message": message},
            )
    except Exception:
        pass  # observer unavailable — don't crash the request


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.2.0"}


@app.post("/run")
async def run(request: TaskRequest):
    task = request.task.strip()
    user_id = request.user_id

    await _log(f"[{user_id}] task='{task[:80]}'", source="api")

    # Inject relevant memory as context prefix
    memory_ctx = mem.context_block(user_id, task)
    enriched_task = f"{memory_ctx}\n{task}" if memory_ctx else task

    result = await route_and_execute(enriched_task)

    # Persist non-destructive tasks to memory
    if result.get("status") == "done":
        mem.add(user_id, task)

    await _log(
        f"[{user_id}] status={result['status']} backend={result.get('backend','?')}",
        source="api",
    )
    return result


@app.get("/memory/{user_id}")
async def get_memory(user_id: str, q: str = ""):
    memories = mem.search(user_id, q or "recent") if q else mem.search(user_id, "")
    return {"user_id": user_id, "memories": memories}


# --------------------------------------------------------------------------- #
# SSE log stream
# --------------------------------------------------------------------------- #

async def _sse_log_stream() -> AsyncIterator[str]:
    """
    Poll the observer's /logs endpoint and push new lines as SSE events.
    Tracks offset to avoid re-sending old lines.
    """
    seen: int = 0
    while True:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{OBSERVER_URL}/logs?n=200")
            lines = [l for l in r.text.splitlines() if l.strip()]
            new_lines = lines[seen:]
            for line in new_lines:
                yield f"data: {line}\n\n"
            seen = len(lines)
        except Exception:
            yield "data: {\"message\":\"observer unavailable\"}\n\n"
        await asyncio.sleep(1)


@app.get("/stream")
async def stream_logs(request: Request):
    return StreamingResponse(
        _sse_log_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- #
# HTML dashboard
# --------------------------------------------------------------------------- #

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Meta-OS Dashboard</title>
  <style>
    body { background:#0d1117; color:#c9d1d9; font-family:monospace; padding:1rem; }
    h1   { color:#58a6ff; margin-bottom:.5rem; }
    #log { height:85vh; overflow-y:auto; border:1px solid #30363d;
           padding:.5rem; border-radius:4px; font-size:.8rem; }
    .info  { color:#c9d1d9; }
    .warn  { color:#e3b341; }
    .error { color:#f85149; }
  </style>
</head>
<body>
<h1>Meta-OS v3.2 — Live Logs</h1>
<div id="log"></div>
<script>
  const box = document.getElementById('log');
  const es  = new EventSource('/stream');
  es.onmessage = e => {
    try {
      const obj = JSON.parse(e.data);
      const div = document.createElement('div');
      div.className = obj.level || 'info';
      div.textContent = `[${obj.ts || ''}] [${obj.source || '-'}] ${obj.message}`;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
    } catch (_) {}
  };
</script>
</body>
</html>"""


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(_DASHBOARD_HTML)
