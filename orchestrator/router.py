"""
Bernstein-style YAML router + executor.

Routes tasks to:
  - n8n       (simple / deterministic — webhook)
  - crewai    (complex reasoning — spawns ephemeral agents)
  - ollama    (local / private — direct LLM call)
  - hitl      (destructive — human-in-the-loop confirmation gate)

Falls back to a stub response when a backend is unreachable.
"""

from __future__ import annotations

import os
import asyncio
import httpx
import yaml
from pathlib import Path

from orchestrator.classifier import classify

ROUTES_FILE = Path(__file__).parent.parent / "config" / "routes.yaml"

N8N_WEBHOOK   = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/meta-os")
OLLAMA_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


_routes_cache: list[dict] | None = None
_routes_mtime: float = 0.0


def _load_routes() -> list[dict]:
    global _routes_cache, _routes_mtime
    if not ROUTES_FILE.exists():
        return []
    mtime = ROUTES_FILE.stat().st_mtime
    if _routes_cache is None or mtime != _routes_mtime:
        _routes_cache = yaml.safe_load(ROUTES_FILE.read_text()) or []
        _routes_mtime = mtime
    return _routes_cache


def _bernstein_match(task: str) -> str | None:
    """Return backend override from routes.yaml if a keyword matches."""
    lower = task.lower()
    for rule in _load_routes():
        for kw in rule.get("match", []):
            if kw.lower() in lower:
                return rule.get("action")
    return None


# --------------------------------------------------------------------------- #
# Backend callers
# --------------------------------------------------------------------------- #

async def _call_n8n(task: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(N8N_WEBHOOK, json={"task": task})
        r.raise_for_status()
        data = r.json()
        return data.get("result") or str(data)


async def _call_ollama(task: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": task,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        r.raise_for_status()
        return r.json().get("response", "").strip()


async def _call_crewai(task: str) -> str:
    """
    Spawn an ephemeral CrewAI run.
    Requires crewai installed: pip install crewai
    Runs in a thread to avoid blocking the event loop.
    """
    def _run() -> str:
        try:
            from crewai import Agent, Task, Crew  # type: ignore
            analyst = Agent(
                role="Analyst",
                goal="Complete the task accurately",
                backstory="You are a capable AI assistant.",
                verbose=False,
                allow_delegation=False,
            )
            t = Task(description=task, agent=analyst, expected_output="A clear result.")
            crew = Crew(agents=[analyst], tasks=[t], verbose=False)
            result = crew.kickoff()
            return str(result)
        except ImportError:
            return f"[crewai not installed] Task received: {task}"
        except Exception as exc:
            return f"[crewai error] {exc}"

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

async def route_and_execute(task: str) -> dict:
    """
    Classify → optionally override via Bernstein rules → execute.

    Returns:
        {
            "status": "done" | "confirm_required",
            "backend": str,
            "result": str,
            "task": str,
        }
    """
    classification = classify(task)
    backend = _bernstein_match(task) or _default_backend(classification)

    if classification == "destructive":
        return {"status": "confirm_required", "backend": "hitl", "task": task}

    result = await _dispatch(backend, task)
    return {"status": "done", "backend": backend, "result": result, "task": task}


def _default_backend(classification: str) -> str:
    return {
        "simple":      "n8n",
        "complex":     "crewai",
        "local":       "ollama",
        "destructive": "hitl",
    }.get(classification, "ollama")


async def _dispatch(backend: str, task: str) -> str:
    try:
        if backend == "n8n":
            return await _call_n8n(task)
        if backend == "ollama":
            return await _call_ollama(task)
        if backend == "crewai":
            return await _call_crewai(task)
    except Exception as exc:
        # Graceful degradation: fall back to stub
        return f"[{backend} unavailable — {exc}] Task received: {task}"
    return f"Task received: {task}"
