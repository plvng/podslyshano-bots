from __future__ import annotations

import logging

import redis.asyncio as redis
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from common.config import get_block_message, get_rate_limit_seconds, get_settings, get_start_message
from common.db.repository import Database
from common.greetings import make_hello
from common.subscription import check_channel_subscription
from proposal_bot.services.admin_notify import notify_admins
from proposal_bot.services.reactions import reply_with_effect, set_good_reaction

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot, db: Database) -> None:
    user = message.from_user
    if not user:
        return

    settings = get_settings()
    is_new = await db.register_user(user.id, user.username)

    if is_new:
        await notify_admins(bot, message)

    subscribed = await check_channel_subscription(bot, settings.tgk, user.id)
    if not subscribed and user.id not in settings.admins:
        await message.answer(f"🍭Подпишись на {settings.tgk}, чтобы пользоваться ботом🍭")
        return

    blocked = await db.is_blocked(user.id)
    text = f"{make_hello()} {get_block_message() if blocked else get_start_message()}"
    await reply_with_effect(message, text, mood="good", reply=False)
    await set_good_reaction(bot, message.chat.id, message.message_id)


async def check_rate_limit(redis_client: redis.Redis, user_id: int) -> bool:
    key = f"proposal:rate:{user_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, get_rate_limit_seconds())
    return count <= 1
