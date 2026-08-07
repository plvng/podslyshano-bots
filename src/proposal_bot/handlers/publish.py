from __future__ import annotations

import logging

import redis.asyncio as redis
from aiogram import Bot, F, Router
from aiogram.types import Message

from common.config import get_block_message, get_settings
from common.db.repository import Database
from common.greetings import make_hello
from common.keyboards import BTN_PUBLISH, BTN_SUPPORT, proposal_keyboard
from proposal_bot.handlers.start import check_rate_limit
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


@router.message(F.text, ~F.text.in_({BTN_PUBLISH, BTN_SUPPORT}))
async def publish_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> None:
    user = message.from_user
    if not user:
        return

    if await db.is_blocked(user.id):
        await message.answer(get_block_message(), reply_markup=proposal_keyboard())
        return

    if await db.get_mode(user.id) != "publish":
        return

    if not await check_rate_limit(redis_client, user.id):
        await message.reply(f"{make_hello()} Подожди немного перед следующим сообщением :)")
        return

    settings = get_settings()
    copied = await bot.copy_message(settings.tgk, message.chat.id, message.message_id)
    await db.create_proposal_post(user.id, copied.message_id, message)
    await set_good_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, f"{make_hello()} Твое сообщение опубликовано :)", mood="good")


@router.message(~F.text)
async def publish_media_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> None:
    user = message.from_user
    if not user:
        return

    if await db.is_blocked(user.id):
        await message.answer(get_block_message(), reply_markup=proposal_keyboard())
        return

    if await db.get_mode(user.id) != "publish":
        return

    if not await check_rate_limit(redis_client, user.id):
        await message.reply(f"{make_hello()} Подожди немного перед следующим сообщением :)")
        return

    settings = get_settings()
    copied = await bot.copy_message(settings.tgk, message.chat.id, message.message_id)
    await db.create_proposal_post(user.id, copied.message_id, message)
    await set_good_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, f"{make_hello()} Твое сообщение опубликовано :)", mood="good")
