#!/usr/bin/env bash
set -e

# Start FastAPI in background
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

# Start Telegram bot in background
python bot.py &
BOT_PID=$!

echo "Meta-OS started — FastAPI PID=$FASTAPI_PID, Bot PID=$BOT_PID"
echo "Press Ctrl+C to stop."

# Wait for either process to exit; kill both on exit
trap "kill $FASTAPI_PID $BOT_PID 2>/dev/null; exit" INT TERM
wait $FASTAPI_PID $BOT_PID
