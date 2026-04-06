"""
Persistent SQLite store for conversation history, todos, and stats.

Tables:
  messages      — every user/assistant turn, with metadata
  pending_tasks — confirmation state per WebSocket session
  todos         — persistent task list

The DB lives at data/meta_os.db so it survives restarts and is shared
by every client (phone, laptop) that hits the same server.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path("data/meta_os.db")


# --------------------------------------------------------------------------- #
# Init
# --------------------------------------------------------------------------- #

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                ts      TEXT    NOT NULL,
                role    TEXT    NOT NULL,   -- 'user' | 'assistant' | 'system'
                content TEXT    NOT NULL,
                meta    TEXT    DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS pending_tasks (
                session_id  TEXT PRIMARY KEY,
                task        TEXT NOT NULL,
                ts          TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS todos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                content     TEXT    NOT NULL,
                done        INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL,
                done_at     TEXT
            );
        """)


_local = __import__("threading").local()


def _conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return _local.conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #

def save_message(role: str, content: str, meta: Optional[dict] = None) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO messages (ts, role, content, meta) VALUES (?, ?, ?, ?)",
            (_now(), role, content, json.dumps(meta or {})),
        )
        return cur.lastrowid


def get_history(limit: int = 120) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, role, content, meta FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "ts":      r["ts"],
            "role":    r["role"],
            "content": r["content"],
            "meta":    json.loads(r["meta"]),
        }
        for r in reversed(rows)
    ]


def clear_history() -> None:
    with _conn() as c:
        c.execute("DELETE FROM messages")


# --------------------------------------------------------------------------- #
# Pending confirmations (per WebSocket session)
# --------------------------------------------------------------------------- #

def set_pending(session_id: str, task: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO pending_tasks (session_id, task, ts) VALUES (?, ?, ?)",
            (session_id, task, _now()),
        )


def get_pending(session_id: str) -> Optional[str]:
    with _conn() as c:
        row = c.execute(
            "SELECT task FROM pending_tasks WHERE session_id = ?", (session_id,)
        ).fetchone()
    return row["task"] if row else None


def clear_pending(session_id: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM pending_tasks WHERE session_id = ?", (session_id,))


# --------------------------------------------------------------------------- #
# Todos
# --------------------------------------------------------------------------- #

def todo_add(content: str) -> dict:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO todos (content, created_at) VALUES (?, ?)",
            (content.strip(), _now()),
        )
        return todo_get(cur.lastrowid)


def todo_get(todo_id: int) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return dict(row) if row else None


def todo_list() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM todos ORDER BY done ASC, id DESC").fetchall()
    return [dict(r) for r in rows]


def todo_toggle(todo_id: int) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT done FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if not row:
            return None
        new_done = 0 if row["done"] else 1
        done_at  = _now() if new_done else None
        c.execute(
            "UPDATE todos SET done = ?, done_at = ? WHERE id = ?",
            (new_done, done_at, todo_id),
        )
    return todo_get(todo_id)


def todo_delete(todo_id: int) -> bool:
    with _conn() as c:
        c.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    return True


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #

def get_stats() -> dict:
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM messages WHERE role='user'").fetchone()[0]

        today = c.execute(
            "SELECT COUNT(*) FROM messages WHERE role='user' AND ts >= date('now')"
        ).fetchone()[0]

        # Backend distribution from assistant message meta
        backend_rows = c.execute(
            "SELECT meta FROM messages WHERE role='assistant'"
        ).fetchall()
        backends: dict[str, int] = {}
        for row in backend_rows:
            try:
                b = json.loads(row["meta"]).get("backend")
                if b:
                    backends[b] = backends.get(b, 0) + 1
            except Exception:
                pass

        # Messages per hour for the last 24h (24 buckets)
        hourly_rows = c.execute("""
            SELECT strftime('%H', ts) AS hr, COUNT(*) AS cnt
            FROM messages
            WHERE role = 'user'
              AND ts >= datetime('now', '-24 hours')
            GROUP BY hr
            ORDER BY hr
        """).fetchall()
        hourly = {r["hr"]: r["cnt"] for r in hourly_rows}

        # Todos progress
        todos_total = c.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
        todos_done  = c.execute("SELECT COUNT(*) FROM todos WHERE done=1").fetchone()[0]

    return {
        "total_messages":  total,
        "today_messages":  today,
        "backends":        backends,
        "hourly":          hourly,
        "todos_total":     todos_total,
        "todos_done":      todos_done,
    }
