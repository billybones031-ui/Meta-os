"""
Meta-OS Telegram bot — v3.2

Commands:
  /start    — greeting
  /status   — health-check all services
  /memory   — recall recent memories for this user
  /clear    — clear pending confirmation
  <text>    — route through Meta-OS API

Confirmation flow:
  destructive task → ask "⚠️ Confirm? Reply YES"
  YES              → re-execute with force flag
"""

from __future__ import annotations

import os
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("META_OS_API", "http://127.0.0.1:8000")
OBSERVER_URL = os.getenv("OBSERVER_URL", "http://localhost:8081")

# chat_id → pending task
pending: dict[int, str] = {}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _user_id(update: Update) -> str:
    return f"tg_{update.effective_user.id}"


async def _api_run(task: str, user_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{API_URL}/run",
            json={"task": task, "user_id": user_id},
        )
        r.raise_for_status()
        return r.json()


async def _api_health() -> dict[str, str]:
    results: dict[str, str] = {}
    checks = {
        "api":      f"{API_URL}/health",
        "observer": f"{OBSERVER_URL}/health",
    }
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in checks.items():
            try:
                r = await client.get(url)
                results[name] = "ok" if r.status_code == 200 else f"HTTP {r.status_code}"
            except Exception as exc:
                results[name] = f"down ({exc})"
    return results


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Meta-OS v3.2 online\n\n"
        "/status — service health\n"
        "/memory — recall your stored memories\n"
        "/clear  — cancel pending confirmation\n"
        "Or just send any task."
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    health = await _api_health()
    lines = [f"{svc}: {st}" for svc, st in health.items()]
    await update.message.reply_text("Service status:\n" + "\n".join(lines))


async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _user_id(update)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{API_URL}/memory/{user_id}")
            data = r.json()
        memories = data.get("memories", [])
        if not memories:
            await update.message.reply_text("No memories stored yet.")
        else:
            text = "\n".join(f"• {m}" for m in memories)
            await update.message.reply_text(f"Your memories:\n{text}")
    except Exception as exc:
        await update.message.reply_text(f"Could not fetch memories: {exc}")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in pending:
        pending.pop(chat_id)
        await update.message.reply_text("Pending confirmation cleared.")
    else:
        await update.message.reply_text("Nothing pending.")


# --------------------------------------------------------------------------- #
# Message handler
# --------------------------------------------------------------------------- #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id  = update.effective_chat.id
    user_id  = _user_id(update)
    text     = update.message.text.strip()

    # YES confirmation
    if text.upper() == "YES" and chat_id in pending:
        task = pending.pop(chat_id)
        await update.message.reply_text("Executing confirmed task...")
        await _dispatch(update, task, user_id, confirmed=True)
        return

    # Non-YES while pending → cancel
    if chat_id in pending:
        pending.pop(chat_id)
        await update.message.reply_text("Confirmation cancelled. Processing as new task...")

    await _dispatch(update, text, user_id)


async def _dispatch(
    update: Update,
    task: str,
    user_id: str,
    confirmed: bool = False,
) -> None:
    chat_id = update.effective_chat.id

    # If confirmed, prefix so classifier sees it as non-destructive
    effective_task = f"[CONFIRMED] {task}" if confirmed else task

    try:
        data = await _api_run(effective_task, user_id)
    except Exception as exc:
        await update.message.reply_text(f"API error: {exc}")
        return

    status = data.get("status")

    if status == "confirm_required":
        pending[chat_id] = task
        await update.message.reply_text(
            f"⚠️ Destructive task detected:\n\"{task}\"\n\n"
            "This action cannot be undone.\n"
            "Reply YES to confirm, or send anything else to cancel."
        )

    elif status == "done":
        backend = data.get("backend", "?")
        result  = data.get("result", "")
        await update.message.reply_text(f"[{backend}] {result}")

    else:
        await update.message.reply_text(str(data))


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    if not TOKEN or TOKEN == "REPLACE_ME":
        raise SystemExit("TELEGRAM_BOT_TOKEN not set in .env")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("clear",  cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Meta-OS bot polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
