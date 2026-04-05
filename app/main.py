"""
Meta-OS FastAPI gateway — port 8000

HTTP endpoints:
  GET    /              — chat UI (mobile + desktop)
  GET    /health        — liveness probe
  GET    /history       — last N messages (JSON)
  DELETE /history       — clear all history
  POST   /run           — classify, route, execute (REST)
  GET    /memory/{id}   — recall stored memories
  GET    /stats         — live stats (messages, backends, hourly)
  GET    /todos         — list all todos
  POST   /todos         — create todo
  PATCH  /todos/{id}    — toggle done
  DELETE /todos/{id}    — delete todo
  GET    /stream        — SSE observer log stream
  GET    /dashboard     — live log dashboard

WebSocket:
  WS     /ws            — real-time chat (preferred by UI)
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from orchestrator.router import route_and_execute
from orchestrator import memory as mem
from app.db import (
    init_db, save_message, get_history, clear_history,
    set_pending, get_pending, clear_pending,
    todo_add, todo_list, todo_toggle, todo_delete,
    get_stats,
)
from app.ui import CHAT_HTML

app = FastAPI(title="Meta-OS", version="3.2.0")

OBSERVER_URL = os.getenv("OBSERVER_URL", "http://localhost:8081")
DEFAULT_USER = os.getenv("META_OS_USER_ID", "bones")


@app.on_event("startup")
async def startup():
    init_db()


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #

class TaskRequest(BaseModel):
    task: str
    user_id: str = DEFAULT_USER


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

async def _log(message: str, level: str = "info", source: str = "api") -> None:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            await client.post(
                f"{OBSERVER_URL}/log",
                json={"level": level, "source": source, "message": message},
            )
    except Exception:
        pass


async def _execute(task: str, user_id: str, session_id: str) -> dict:
    """Core: memory inject → route → execute → persist."""
    memory_ctx = mem.context_block(user_id, task)
    enriched = f"{memory_ctx}\n{task}" if memory_ctx else task

    result = await route_and_execute(enriched)

    if result.get("status") == "done":
        mem.add(user_id, task)

    await _log(
        f"[{user_id}] status={result['status']} backend={result.get('backend','?')}",
        source="api",
    )
    return result


# --------------------------------------------------------------------------- #
# REST endpoints
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.2.0"}


@app.get("/history")
async def history(limit: int = 120):
    return {"messages": get_history(limit)}


@app.delete("/history")
async def delete_history():
    clear_history()
    return {"status": "cleared"}


@app.post("/run")
async def run(request: TaskRequest):
    task = request.task.strip()
    save_message("user", task)
    await _log(f"[{request.user_id}] task='{task[:80]}'", source="api")
    result = await _execute(task, request.user_id, "rest")
    save_message("assistant", result.get("result", str(result)), {"backend": result.get("backend"), "status": result.get("status")})
    return result


@app.get("/memory/{user_id}")
async def get_memory(user_id: str, q: str = ""):
    memories = mem.search(user_id, q or "recent")
    return {"user_id": user_id, "memories": memories}


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #

@app.get("/stats")
async def stats():
    return get_stats()


# --------------------------------------------------------------------------- #
# Todos
# --------------------------------------------------------------------------- #

class TodoCreate(BaseModel):
    content: str


@app.get("/todos")
async def list_todos():
    return todo_list()


@app.post("/todos", status_code=201)
async def create_todo(body: TodoCreate):
    return todo_add(body.content)


@app.patch("/todos/{todo_id}")
async def toggle_todo(todo_id: int):
    item = todo_toggle(todo_id)
    if item is None:
        from fastapi import HTTPException
        raise HTTPException(404, "not found")
    return item


@app.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: int):
    todo_delete(todo_id)


# --------------------------------------------------------------------------- #
# WebSocket chat
# --------------------------------------------------------------------------- #

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())
    user_id = DEFAULT_USER

    # Send history on connect so any device picks up right where it left off
    history = get_history(120)
    await ws.send_text(json.dumps({"type": "history", "messages": history}))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"text": raw}

            text = data.get("text", "").strip()
            if not text:
                continue

            # YES confirmation
            if text.upper() == "YES":
                pending = get_pending(session_id)
                if pending:
                    clear_pending(session_id)
                    await ws.send_text(json.dumps({"type": "system", "content": "Executing confirmed task..."}))
                    result = await _execute(f"[CONFIRMED] {pending}", user_id, session_id)
                    reply = result.get("result", str(result))
                    meta = {"backend": result.get("backend"), "status": result.get("status")}
                    save_message("assistant", reply, meta)
                    await ws.send_text(json.dumps({"type": "assistant", "content": reply, "meta": meta}))
                    continue
                # No pending — fall through and treat as normal message

            # Clear stale pending if user sends something other than YES
            if get_pending(session_id):
                clear_pending(session_id)
                await ws.send_text(json.dumps({"type": "system", "content": "Confirmation cancelled."}))

            save_message("user", text)
            await _log(f"[ws/{user_id}] '{text[:80]}'", source="ws")

            result = await _execute(text, user_id, session_id)

            if result.get("status") == "confirm_required":
                set_pending(session_id, result["task"])
                msg = f"⚠️ Destructive task detected:\n\"{result['task']}\"\n\nType YES to confirm, or send anything else to cancel."
                save_message("assistant", msg, {"status": "confirm_required"})
                await ws.send_text(json.dumps({"type": "confirm", "content": msg, "task": result["task"]}))
            else:
                reply = result.get("result", str(result))
                meta = {"backend": result.get("backend"), "status": result.get("status")}
                save_message("assistant", reply, meta)
                await ws.send_text(json.dumps({"type": "assistant", "content": reply, "meta": meta}))

    except WebSocketDisconnect:
        clear_pending(session_id)


# --------------------------------------------------------------------------- #
# SSE observer log stream
# --------------------------------------------------------------------------- #

async def _sse_log_stream() -> AsyncIterator[str]:
    seen = 0
    while True:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{OBSERVER_URL}/logs?n=200")
            lines = [l for l in r.text.splitlines() if l.strip()]
            for line in lines[seen:]:
                yield f"data: {line}\n\n"
            seen = len(lines)
        except Exception:
            yield 'data: {"message":"observer unavailable"}\n\n'
        await asyncio.sleep(1)


@app.get("/stream")
async def stream_logs():
    return StreamingResponse(
        _sse_log_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

@app.get("/", response_class=HTMLResponse)
async def chat_ui():
    return HTMLResponse(CHAT_HTML)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    from app.ui import LOG_HTML
    return HTMLResponse(LOG_HTML)
