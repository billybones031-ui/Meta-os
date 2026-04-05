#!/usr/bin/env bash
# Meta-OS v3.2 — quick dev launcher (no Go observer)
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

[[ -f .venv/bin/activate ]] && source .venv/bin/activate

PIDS=()
stop_all() { kill "${PIDS[@]}" 2>/dev/null || true; exit 0; }
trap stop_all INT TERM

uvicorn app.main:app --host 127.0.0.1 --port 8000 &
PIDS+=($!)
echo "[api] PID=${PIDS[-1]}"

python bot.py &
PIDS+=($!)
echo "[bot] PID=${PIDS[-1]}"

echo "Meta-OS running — Ctrl+C to stop."
wait "${PIDS[@]}"
