from __future__ import annotations

import logging

import redis.asyncio as redis
from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from common.config import get_block_message, get_settings
from common.db.repository import Database
from common.greetings import make_hello
from common.keyboards import BTN_PUBLISH, BTN_SUPPORT, proposal_keyboard
from proposal_bot.services.reactions import reply_with_effect, set_good_reaction

logger = logging.getLogger(__name__)
router = Router(name="publish")


async def check_rate_limit(redis_client: redis.Redis, user_id: int) -> bool:
    from common.config import get_rate_limit_seconds

    key = f"proposal:rate:{user_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, get_rate_limit_seconds())
    return count <= 1


async def _publish_to_channel(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    user = message.from_user
    if not user:
        return UNHANDLED

    if message.text and message.text.startswith("/"):
        return UNHANDLED

    if await db.is_blocked(user.id):
        await message.answer(get_block_message(), reply_markup=proposal_keyboard())
        return None

    if await db.get_mode(user.id) != "publish":
        return UNHANDLED

    if not await check_rate_limit(redis_client, user.id):
        await message.reply(f"{make_hello()} Подожди немного перед следующим сообщением :)")
        return None

    settings = get_settings()
    try:
        copied = await bot.copy_message(settings.tgk, message.chat.id, message.message_id)
    except TelegramAPIError as exc:
        logger.exception("Failed to publish message from %s to %s", user.id, settings.tgk)
        await message.answer(
            f"Не удалось опубликовать в {settings.tgk}. "
            f"Проверь, что бот — админ канала. Ошибка: {exc.message}"
        )
        return None

    await db.create_proposal_post(user.id, copied.message_id, message)
    await set_good_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, f"{make_hello()} Твое сообщение опубликовано :)", mood="good")
    return None


@router.message(F.text, ~F.text.in_({BTN_PUBLISH, BTN_SUPPORT}))
async def publish_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    return await _publish_to_channel(message, bot, db, redis_client)


@router.message(~F.text)
async def publish_media_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    return await _publish_to_channel(message, bot, db, redis_client)
