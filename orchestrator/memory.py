"""
Mem0 long-term memory integration.

Provides:
  add(user_id, content)    — store a memory
  search(user_id, query)   — retrieve relevant memories
  context_block(...)       — format memories as prompt prefix
"""

from __future__ import annotations

import os
from typing import Optional

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")


def _mem0_config() -> dict:
    return {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": OLLAMA_MODEL,
                "ollama_base_url": OLLAMA_BASE,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": EMBED_MODEL,
                "ollama_base_url": OLLAMA_BASE,
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "meta_os_memory",
                "path": CHROMA_PATH,
            },
        },
    }


def _get_client():
    try:
        from mem0 import Memory  # type: ignore
        return Memory.from_config(_mem0_config())
    except ImportError:
        return None


def add(user_id: str, content: str) -> bool:
    """Store a memory. Returns True on success."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.add(content, user_id=user_id)
        return True
    except Exception:
        return False


def search(user_id: str, query: str, limit: int = 5) -> list[str]:
    """Return relevant memory strings for the given query."""
    client = _get_client()
    if client is None:
        return []
    try:
        results = client.search(query, user_id=user_id, limit=limit)
        return [r["memory"] for r in results if "memory" in r]
    except Exception:
        return []


def context_block(user_id: str, query: str) -> Optional[str]:
    """
    Return a formatted string of relevant memories to prepend to prompts,
    or None if nothing found.
    """
    memories = search(user_id, query)
    if not memories:
        return None
    lines = "\n".join(f"- {m}" for m in memories)
    return f"[Relevant memory]\n{lines}\n"
