"""Telegram assistant bot for employees.

Runs as its own process (`python -m backend.app.telegram.bot`, the `telegram-bot`
compose service) and talks to the platform over its HTTP API, so conversation
memory, provider routing (Ollama / OmniRoute) and future features live in one place.
"""
import asyncio
import base64
import contextlib
import logging
import time

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from backend.app.core.config import settings
from backend.app.core.logging_config import configure_logging

logger = logging.getLogger("ai_agent_platform.telegram_bot")

TELEGRAM_MESSAGE_LIMIT = 4000
# Telegram bots can download files up to 20 MB.
MAX_FILE_BYTES = 20 * 1024 * 1024

START_TEXT = (
    "Assalomu alaykum! Men AI yordamchiman. Savolingiz yoki vazifangizni yozing.\n\n"
    "Hujjat (PDF, Word, TXT) yuborsangiz — o'qib olaman va u haqida savollarga javob beraman. "
    "Jadval (Excel .xlsx, CSV) yuborsangiz — tahlil qilaman. Hujjatlaringizni faqat siz ishlatasiz.\n\n"
    "Buyruqlar:\n"
    "/clear — yangi mavzu boshlash (AI oldingi suhbatni hisobga olmaydi)\n"
    "/users — (faqat administrator) foydalanuvchilar va ruxsatlar\n"
    "/havola Ism — (faqat administrator) shaxsiy veb-chat havolasi yaratish\n\n"
    "⚠️ Diqqat: suhbatlaringiz ish maqsadida saqlanadi va ularni administrator ko'rishi mumkin. "
    "Shaxsiy yoki maxfiy ma'lumotlarni keraksiz yubormang."
)

CLOUD_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("☁️ Kuchliroq AI'dan so'rash", callback_data="cloud:preview")]]
)
HIDDEN_LABELS = {
    "TEL": "telefon", "PASPORT": "pasport", "JSHSHIR": "JSHSHIR", "STIR": "STIR",
    "KARTA": "karta", "HISOB": "hisob raqam", "EMAIL": "email", "SUMMA": "summa",
    "MANZIL": "manzil", "ISM": "ism",
}

ACCESS_CACHE_SECONDS = 30
_access_cache: dict[int, tuple[bool, float]] = {}
_last_denied_reply: dict[int, float] = {}

# One lock per chat: a user's messages are answered in order; different users run in parallel.
_chat_locks: dict[int, asyncio.Lock] = {}


def _admin_ids() -> set[int]:
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
            json={
                "message": message,
                "session_id": session_id,
                "user_name": user_name,
                "use_documents": True,
            },
            headers=_headers(),
        )
        response.raise_for_status()
        return response.json()["response"]


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    # Telegram's "typing…" indicator lasts ~5s, so refresh it while the model works.
    while True:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(4)


async def _send_long(update: Update, text: str, reply_markup=None) -> None:
    text = text or "(bo'sh javob)"
    message = update.effective_message
    chunk = ""
    for part in text.split("\n\n"):
        if chunk and len(chunk) + len(part) + 2 > TELEGRAM_MESSAGE_LIMIT:
            await message.reply_text(chunk)
            chunk = part
        else:
            chunk = f"{chunk}\n\n{part}" if chunk else part
        while len(chunk) > TELEGRAM_MESSAGE_LIMIT:
            await message.reply_text(chunk[:TELEGRAM_MESSAGE_LIMIT])
            chunk = chunk[TELEGRAM_MESSAGE_LIMIT:]
    if chunk:
        # Buttons go on the last part only.
        await message.reply_text(chunk, reply_markup=reply_markup)


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
    await _send_long(update, reply, reply_markup=CLOUD_BUTTON)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    filename = doc.file_name or "fayl"
    if doc.file_size and doc.file_size > MAX_FILE_BYTES:
        await update.message.reply_text("Fayl juda katta (20 MB dan oshmasin).")
        return

    chat_id = update.effective_chat.id
    lock = _chat_locks.setdefault(chat_id, asyncio.Lock())
    async with lock:
        typing = asyncio.create_task(_keep_typing(context, chat_id))
        try:
            tg_file = await context.bot.get_file(doc.file_id)
            data = bytes(await tg_file.download_as_bytearray())
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"{settings.PLATFORM_URL}/api/v1/files/ingest",
                    json={
                        "filename": filename,
                        "content_base64": base64.b64encode(data).decode(),
                        "session_id": _session_id(update),
                        "user_name": _user_name(update),
                    },
                    headers=_headers(),
                )
            if response.status_code == 415:
                reply = "Bu format qo'llab-quvvatlanmaydi. PDF, Word (.docx), TXT, CSV yoki Excel (.xlsx) yuboring."
            elif response.status_code == 422:
                reply = f"Faylni o'qib bo'lmadi: {response.json().get('detail', '')}"
            else:
                response.raise_for_status()
                result = response.json()
                if result["kind"] == "document":
                    reply = (
                        f"'{filename}' o'qildi ({result['chunks']} bo'lak). "
                        "Endi bu hujjat haqida savol berishingiz mumkin."
                    )
                else:
                    reply = f"'{filename}' jadvali tahlil qilindi. Endi u haqida savol bering."
        except Exception:
            logger.exception("file ingest failed for %s", _session_id(update))
            reply = "Kechirasiz, faylni qayta ishlab bo'lmadi. Birozdan keyin qayta urinib ko'ring."
        finally:
            typing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await typing
    await update.message.reply_text(reply)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Rasm tahlili hozircha mavjud emas. Matn yozing yoki hujjat (PDF, Word, Excel) yuboring."
    )


async def _post(path: str, payload: dict, timeout: float = 30.0) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.post(f"{settings.PLATFORM_URL}{path}", json=payload, headers=_headers())


async def handle_cloud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline buttons: preview the masked question, then send or cancel it."""
    query = update.callback_query
    await query.answer()
    session_id = _session_id(update)
    action, _, request_id = query.data.removeprefix("cloud:").partition(":")

    if action == "preview":
        response = await _post("/api/v1/cloud/preview", {"session_id": session_id})
        if response.status_code != 200:
            await query.message.reply_text("Bulutga yuboriladigan savol topilmadi.")
            return
        data = response.json()
        if not data["enabled"]:
            await query.message.reply_text(
                "Kuchliroq (bulut) AI hali sozlanmagan. Administrator bilan bog'laning."
            )
            return
        hidden = ", ".join(f"{HIDDEN_LABELS.get(k, k)}: {n}" for k, n in data["hidden"].items()) or "hech narsa"
        text = (
            "Bulut AI'ga quyidagi ko'rinishda yuboriladi:\n\n"
            f"{data['masked_question'][:3000]}\n\n"
            f"Yashirildi — {hidden} (oldingi {data['context_messages'] - 1} ta xabar ham shunday yashiriladi).\n\n"
            "⚠️ Tekshiring: yashirilmagan maxfiy ma'lumot qolgan bo'lsa, yubormang. "
            "Yashirilgan raqamlar bilan AI hisob-kitob qila olmaydi."
        )
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Yuborish", callback_data=f"cloud:send:{data['request_id']}"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cloud:cancel:{data['request_id']}"),
        ]])
        await query.message.reply_text(text, reply_markup=buttons)
        return

    if not request_id.isdigit():
        return
    payload = {"request_id": int(request_id), "session_id": session_id}
    await query.edit_message_reply_markup(reply_markup=None)  # one decision per preview
    if action == "cancel":
        await _post("/api/v1/cloud/cancel", payload)
        await query.message.reply_text("Bekor qilindi. Hech narsa yuborilmadi.")
        return
    if action == "send":
        chat_id = update.effective_chat.id
        lock = _chat_locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            typing = asyncio.create_task(_keep_typing(context, chat_id))
            try:
                response = await _post("/api/v1/cloud/send", payload, timeout=300.0)
                if response.status_code == 200:
                    reply = "☁️ " + response.json()["response"]
                else:
                    reply = response.json().get("detail", "Bulut AI javob bermadi.")
            except Exception:
                logger.exception("cloud send failed for %s", session_id)
                reply = "Kechirasiz, bulut AI hozir javob bera olmadi."
            finally:
                typing.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await typing
        await _send_long(update, reply)


async def _check_access(update: Update) -> dict:
    user = update.effective_user
    response = await _post("/api/v1/telegram/access", {"user_id": user.id, "name": _user_name(update)}, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def gatekeeper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs before every handler: lets allowed users through, turns strangers into access requests."""
    user = update.effective_user
    if user is None:
        raise ApplicationHandlerStop
    if update.callback_query and (update.callback_query.data or "").startswith(("acc:", "inv:")):
        return  # admin approval buttons check admin rights themselves
    cached = _access_cache.get(user.id)
    if cached and time.monotonic() - cached[1] < ACCESS_CACHE_SECONDS:
        allowed = cached[0]
    else:
        try:
            result = await _check_access(update)
        except Exception:
            logger.exception("access check failed for %s", user.id)
            raise ApplicationHandlerStop
        allowed = result["allowed"]
        _access_cache[user.id] = (allowed, time.monotonic())
        if result.get("new_request"):
            await _notify_admins(context, user.id, _user_name(update))
    if allowed:
        return
    if update.callback_query:
        await update.callback_query.answer("Huquqingiz yo'q.", show_alert=True)
    elif update.effective_message and time.monotonic() - _last_denied_reply.get(user.id, 0) > 60:
        _last_denied_reply[user.id] = time.monotonic()
        await update.effective_message.reply_text(
            "Sizda hali bu botdan foydalanish huquqi yo'q. So'rovingiz administratorga yuborildi — "
            "ruxsat berilgach sizga xabar keladi."
        )
    raise ApplicationHandlerStop


def _decision_buttons(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ruxsat berish", callback_data=f"acc:allowed:{user_id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"acc:blocked:{user_id}"),
    ]])


async def _notify_admins(context: ContextTypes.DEFAULT_TYPE, user_id: int, name: str) -> None:
    for admin_id in _admin_ids():
        try:
            await context.bot.send_message(
                admin_id,
                f"🔔 Yangi so'rov: {name}\nTelegram ID: {user_id}\n\nBotdan foydalanishga ruxsat berasizmi?",
                reply_markup=_decision_buttons(user_id),
            )
        except Exception:
            logger.exception("could not notify admin %s", admin_id)


async def handle_access_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin pressed Allow / Block (from a request notification or the /users list)."""
    query = update.callback_query
    if update.effective_user.id not in _admin_ids():
        await query.answer("Bu faqat administrator uchun.", show_alert=True)
        return
    _, status, user_id = query.data.split(":")
    response = await _post(f"/api/v1/telegram/access/{user_id}", {"status": status}, timeout=10.0)
    if response.status_code != 200:
        await query.answer("Xatolik.", show_alert=True)
        return
    _access_cache.pop(int(user_id), None)
    await query.answer("Saqlandi.")
    label = "✅ Ruxsat berildi" if status == "allowed" else "🚫 Bloklandi"
    await query.edit_message_text(f"{query.message.text}\n\n{label}")
    if status == "allowed":
        with contextlib.suppress(Exception):
            await context.bot.send_message(
                int(user_id), "✅ Sizga botdan foydalanishga ruxsat berildi! Savolingizni yozishingiz mumkin. /start"
            )


async def cmd_havola(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: /havola Ism Familiya -> personal web chat link for that person."""
    if update.effective_user.id not in _admin_ids():
        return
    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text("Ismni ham yozing, masalan: /havola Aliyev Vali")
        return
    response = await _post("/api/v1/invites", {"name": name}, timeout=10.0)
    if response.status_code != 200:
        await update.message.reply_text("Havola yaratib bo'lmadi.")
        return
    invite = response.json()
    links = "\n".join(invite["links"])
    await update.message.reply_text(
        f"🔗 {invite['name']} uchun shaxsiy veb-chat havolasi:\n\n{links}\n\n"
        "Shu odamga yuboring. Havola faqat u uchun — boshqaga bermasin.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "🚫 Havolani bekor qilish", callback_data=f"inv:revoke:{invite['id']}")]]),
        disable_web_page_preview=True,
    )


async def handle_invite_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if update.effective_user.id not in _admin_ids():
        await query.answer("Bu faqat administrator uchun.", show_alert=True)
        return
    invite_id = query.data.rsplit(":", 1)[1]
    response = await _post(f"/api/v1/invites/{invite_id}/revoke", {}, timeout=10.0)
    await query.answer("Bekor qilindi." if response.status_code == 200 else "Allaqachon bekor qilingan.")
    await query.edit_message_text(f"{query.message.text}\n\n🚫 Havola bekor qilindi.", disable_web_page_preview=True)


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: list everyone who asked for access, with buttons to change their status."""
    if update.effective_user.id not in _admin_ids():
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{settings.PLATFORM_URL}/api/v1/telegram/access", headers=_headers())
    users = response.json() if response.status_code == 200 else []
    if not users:
        await update.message.reply_text("Hali hech kim so'rov yubormagan. Odamlar botga yozsa, bu yerda ko'rinadi.")
        return
    icons = {"pending": "⏳", "allowed": "✅", "blocked": "🚫"}
    for u in users[:30]:
        if u["status"] == "allowed":
            buttons = [[InlineKeyboardButton("🚫 Bloklash", callback_data=f"acc:blocked:{u['user_id']}")]]
        elif u["status"] == "blocked":
            buttons = [[InlineKeyboardButton("✅ Ruxsat berish", callback_data=f"acc:allowed:{u['user_id']}")]]
        else:
            buttons = _decision_buttons(u["user_id"]).inline_keyboard
        await update.message.reply_text(
            f"{icons.get(u['status'], '')} {u['name'] or u['user_id']}\nID: {u['user_id']}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("unhandled telegram error", exc_info=context.error)


def main() -> None:
    configure_logging()
    logging.getLogger("telegram").setLevel(logging.INFO)

    if not settings.TELEGRAM_BOT_TOKEN:
        # Exit cleanly (code 0) so `restart: on-failure` doesn't loop when the bot isn't configured.
        logger.warning("TELEGRAM_BOT_TOKEN is not set -- Telegram bot not started.")
        return

    if not _admin_ids():
        logger.warning("TELEGRAM_ALLOWED_USER_IDS is empty -- no admin will receive access requests.")

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(TypeHandler(Update, gatekeeper), group=-1)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("havola", cmd_havola))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_cloud, pattern=r"^cloud:"))
    app.add_handler(CallbackQueryHandler(handle_access_decision, pattern=r"^acc:"))
    app.add_handler(CallbackQueryHandler(handle_invite_revoke, pattern=r"^inv:"))
    app.add_error_handler(on_error)

    logger.info("Telegram bot starting (long polling), %d admin(s)", len(_admin_ids()))
    app.run_polling()


if __name__ == "__main__":
    main()
