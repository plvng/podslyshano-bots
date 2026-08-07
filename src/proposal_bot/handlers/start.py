from __future__ import annotations

import logging

import redis.asyncio as redis
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from common.config import get_block_message, get_config_value, get_settings, get_start_message
from common.db.repository import Database
from common.greetings import make_hello
from common.keyboards import BTN_PUBLISH, BTN_SUPPORT, proposal_keyboard
from common.subscription_cache import check_channel_subscription
from proposal_bot.services.reactions import reply_with_effect, set_good_reaction

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def start_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> None:
    user = message.from_user
    if not user:
        return

    settings = get_settings()
    full_name = user.full_name
    is_new = await db.upsert_user(user.id, user.username, full_name)

    subscribed = await check_channel_subscription(bot, settings.tgk, user.id, redis_client)
    if not subscribed and user.id not in settings.admins:
        await message.answer(f"🍭Подпишись на {settings.tgk}, чтобы пользоваться ботом🍭")
        return

    if is_new:
        logger.info("New user registered: %s", user.id)

    blocked = await db.is_blocked(user.id)
    if blocked:
        await message.answer(f"{make_hello()} {get_block_message()}", reply_markup=proposal_keyboard())
        return

    await db.set_mode(user.id, "publish")
    text = f"{make_hello()} {get_start_message()}"
    await reply_with_effect(message, text, mood="good", reply=False)
    await message.answer("Режим: публикация в канал.", reply_markup=proposal_keyboard("publish"))
    await set_good_reaction(bot, message.chat.id, message.message_id)
