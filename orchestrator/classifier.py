"""
OpenClaw-style task classifier.
Returns one of: destructive | complex | local | simple
"""

from __future__ import annotations

DESTRUCTIVE_KEYWORDS = {
    "delete", "erase", "remove", "shutdown", "drop", "wipe",
    "terminate", "kill", "destroy", "purge", "format",
}

LOCAL_PHRASES = ("local only", "offline", "private", "no cloud", "on device")


def classify(task: str) -> str:
    lower = task.lower()
    words = set(lower.split())

    if words & DESTRUCTIVE_KEYWORDS:
        return "destructive"

    if any(phrase in lower for phrase in LOCAL_PHRASES):
        return "local"

    if len(task.split()) > 40:
        return "complex"

    return "simple"
