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

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("META_OS_API", "http://127.0.0.1:8000")

# Maps chat_id -> pending task awaiting confirmation
pending: dict[int, str] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Meta-OS online")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # Handle YES confirmation
    if text.upper() == "YES" and chat_id in pending:
        task = pending.pop(chat_id)
        await dispatch(update, task)
        return

    # Remove stale pending if user sends something other than YES
    pending.pop(chat_id, None)

    await dispatch(update, text)


async def dispatch(update: Update, task: str) -> None:
    chat_id = update.effective_chat.id
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/run",
                json={"task": task},
                timeout=10.0,
            )
        data = response.json()
    except Exception as exc:
        await update.message.reply_text(f"Error contacting API: {exc}")
        return

    if data.get("status") == "confirm_required":
        pending[chat_id] = data["task"]
        await update.message.reply_text(
            f"⚠️ Destructive task detected:\n\"{data['task']}\"\n\nConfirm? Reply YES"
        )
    elif data.get("status") == "done":
        await update.message.reply_text(data["result"])
    else:
        await update.message.reply_text(str(data))


def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
