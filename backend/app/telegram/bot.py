"""Telegram assistant bot for employees.

Runs as its own process (`python -m backend.app.telegram.bot`, the `telegram-bot`
compose service) and talks to the platform over its HTTP API, so conversation
memory, provider routing (Ollama / OmniRoute) and future features live in one place.
"""
import asyncio
import contextlib
import logging

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from backend.app.core.config import settings
from backend.app.core.logging_config import configure_logging

logger = logging.getLogger("ai_agent_platform.telegram_bot")

TELEGRAM_MESSAGE_LIMIT = 4000

START_TEXT = (
    "Assalomu alaykum! Men AI yordamchiman. Savolingiz yoki vazifangizni yozing.\n\n"
    "Buyruqlar:\n"
    "/clear — yangi mavzu boshlash (AI oldingi suhbatni hisobga olmaydi)\n\n"
    "⚠️ Diqqat: suhbatlaringiz ish maqsadida saqlanadi va ularni administrator ko'rishi mumkin. "
    "Shaxsiy yoki maxfiy ma'lumotlarni keraksiz yubormang."
)

# One lock per chat: a user's messages are answered in order; different users run in parallel.
_chat_locks: dict[int, asyncio.Lock] = {}


def _allowed_user_ids() -> set[int]:
    return {int(x) for x in settings.TELEGRAM_ALLOWED_USER_IDS.split(",") if x.strip().isdigit()}


def _session_id(update: Update) -> str:
    return f"tg:{update.effective_user.id}"


def _user_name(update: Update) -> str:
    user = update.effective_user
    full_name = " ".join(filter(None, [user.first_name, user.last_name]))
    return f"@{user.username} ({full_name})" if user.username else full_name or str(user.id)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.PLATFORM_API_KEY}"} if settings.PLATFORM_API_KEY else {}


async def _ask_platform(session_id: str, message: str, user_name: str) -> str:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{settings.PLATFORM_URL}/api/v1/chat",
            json={"message": message, "session_id": session_id, "user_name": user_name},
            headers=_headers(),
        )
        response.raise_for_status()
        return response.json()["response"]


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    # Telegram's "typing…" indicator lasts ~5s, so refresh it while the model works.
    while True:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(4)


async def _send_long(update: Update, text: str) -> None:
    text = text or "(bo'sh javob)"
    chunk = ""
    for part in text.split("\n\n"):
        if chunk and len(chunk) + len(part) + 2 > TELEGRAM_MESSAGE_LIMIT:
            await update.message.reply_text(chunk)
            chunk = part
        else:
            chunk = f"{chunk}\n\n{part}" if chunk else part
        while len(chunk) > TELEGRAM_MESSAGE_LIMIT:
            await update.message.reply_text(chunk[:TELEGRAM_MESSAGE_LIMIT])
            chunk = chunk[TELEGRAM_MESSAGE_LIMIT:]
    if chunk:
        await update.message.reply_text(chunk)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(START_TEXT)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{settings.PLATFORM_URL}/api/v1/chat/{_session_id(update)}/history", headers=_headers()
        )
        response.raise_for_status()
    await update.message.reply_text("Yangi mavzu boshlandi. Oldingi suhbat AI uchun hisobga olinmaydi.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    lock = _chat_locks.setdefault(chat_id, asyncio.Lock())
    async with lock:
        typing = asyncio.create_task(_keep_typing(context, chat_id))
        try:
            reply = await _ask_platform(_session_id(update), update.message.text, _user_name(update))
        except Exception:
            logger.exception("platform request failed for %s", _session_id(update))
            reply = "Kechirasiz, AI hozir javob bera olmadi. Birozdan keyin qayta urinib ko'ring."
        finally:
            typing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await typing
    await _send_long(update, reply)


async def handle_unauthorized(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        logger.warning("unauthorized user id=%s", update.effective_user.id if update.effective_user else "?")
        await update.message.reply_text("Kechirasiz, sizda bu botdan foydalanish huquqi yo'q.")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("unhandled telegram error", exc_info=context.error)


def main() -> None:
    configure_logging()
    logging.getLogger("telegram").setLevel(logging.INFO)

    if not settings.TELEGRAM_BOT_TOKEN:
        # Exit cleanly (code 0) so `restart: on-failure` doesn't loop when the bot isn't configured.
        logger.warning("TELEGRAM_BOT_TOKEN is not set -- Telegram bot not started.")
        return

    allowed_ids = _allowed_user_ids()
    if not allowed_ids:
        logger.warning("TELEGRAM_ALLOWED_USER_IDS is empty -- nobody will be able to use the bot.")
    allowed = filters.User(user_id=list(allowed_ids)) if allowed_ids else filters.User(user_id=[-1])

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", cmd_start, filters=allowed))
    app.add_handler(CommandHandler("clear", cmd_clear, filters=allowed))
    app.add_handler(MessageHandler(allowed & filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(~allowed, handle_unauthorized), group=1)
    app.add_error_handler(on_error)

    logger.info("Telegram bot starting (long polling), %d allowed users", len(allowed_ids))
    app.run_polling()


if __name__ == "__main__":
    main()
