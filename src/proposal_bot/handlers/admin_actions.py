from __future__ import annotations

import logging

import redis.asyncio as redis
from aiogram import Bot, Router
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import Message

from common.db.repository import Database
from common.keyboards import BTN_PUBLISH, BTN_SUPPORT
from proposal_bot.handlers.panel import IsAdminFilter, reply_key

logger = logging.getLogger(__name__)
router = Router(name="admin_actions")


class _TextMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.caption = None
        self.content_type = "text"


@router.message(IsAdminFilter())
async def admin_support_reply_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    """Deliver admin reply when Redis reply-mode is active; otherwise pass through."""
    user = message.from_user
    if not user:
        return UNHANDLED

    if message.text and (message.text.startswith("/") or message.text in {BTN_PUBLISH, BTN_SUPPORT}):
        return UNHANDLED

    thread_raw = await redis_client.get(reply_key(user.id))
    if not thread_raw:
        return UNHANDLED

    thread_id = int(thread_raw)
    threads = await db.list_support_threads()
    thread = next((item for item in threads if int(item["id"]) == thread_id), None)
    if not thread:
        await redis_client.delete(reply_key(user.id))
        await message.answer("Обращение не найдено, режим ответа сброшен.")
        return None

    if thread.get("status") != "open":
        await redis_client.delete(reply_key(user.id))
        await message.answer(f"Обращение #{thread_id} уже закрыто.")
        return None

    target_user_id = int(thread["user_id"])
    try:
        sent = await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except Exception as exc:
        logger.warning("Failed to deliver admin reply to %s: %s", target_user_id, exc)
        await message.answer(f"Не удалось отправить пользователю {target_user_id}.")
        return None

    payload: object = message if (message.text or message.caption) else _TextMessage("[media]")
    await db.add_support_message(thread_id, user.id, "admin", payload, sent.message_id)
    await redis_client.delete(reply_key(user.id))
    await message.answer(f"Ответ отправлен в обращение #{thread_id}.")
    return None
