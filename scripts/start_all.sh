#!/usr/bin/env bash
# Meta-OS v3.2 — start all services
# Usage: bash scripts/start_all.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$REPO_DIR/data/logs"
mkdir -p "$LOG_DIR" "$REPO_DIR/data/chroma"

# Activate venv if present
if [[ -f "$REPO_DIR/.venv/bin/activate" ]]; then
    source "$REPO_DIR/.venv/bin/activate"
fi

cd "$REPO_DIR"

# --------------------------------------------------------------------------- #
stop_all() {
    echo "Stopping Meta-OS..."
    kill "${PIDS[@]}" 2>/dev/null || true
    exit 0
}
trap stop_all INT TERM
PIDS=()
# --------------------------------------------------------------------------- #

echo "=== Starting Meta-OS v3.2 ==="

# 1. Go observer (:8081)
if [[ -f "$REPO_DIR/observer/observer_bin" ]]; then
    LOG_DIR="$LOG_DIR" "$REPO_DIR/observer/observer_bin" \
        >> "$LOG_DIR/observer.log" 2>&1 &
    PIDS+=($!)
    echo "[observer] PID=${PIDS[-1]}  :8081"
else
    echo "[observer] binary not found — run setup.sh first"
fi

# 2. FastAPI gateway (:8000)
uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --log-level info \
    >> "$LOG_DIR/api.log" 2>&1 &
PIDS+=($!)
echo "[api]      PID=${PIDS[-1]}  :8000"

# 3. n8n (:5678) — if installed
if command -v n8n &>/dev/null; then
    n8n start >> "$LOG_DIR/n8n.log" 2>&1 &
    PIDS+=($!)
    echo "[n8n]      PID=${PIDS[-1]}  :5678"
else
    echo "[n8n]      not installed — skipping"
fi

# 4. Telegram bot
python bot.py >> "$LOG_DIR/bot.log" 2>&1 &
PIDS+=($!)
echo "[bot]      PID=${PIDS[-1]}"

echo ""
echo "All services started. Logs → $LOG_DIR"
echo "Dashboard → http://0.0.0.0:8000/dashboard"
echo "Press Ctrl+C to stop all."
echo ""

wait "${PIDS[@]}"
