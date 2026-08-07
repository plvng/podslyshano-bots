from __future__ import annotations

import redis.asyncio as redis
from aiogram import Bot, Router
from aiogram.types import Message

from common.config import get_settings
from common.db.repository import Database
from common.greetings import make_hello
from proposal_bot.filters import IsNotAdminFilter, IsNotBlockedFilter, IsPostFilter
from proposal_bot.handlers.start import check_rate_limit
from proposal_bot.services.admin_notify import notify_admins
from proposal_bot.services.reactions import reply_with_effect, set_good_reaction

router = Router(name="user_post")


@router.message(IsNotAdminFilter(), IsNotBlockedFilter(), IsPostFilter())
async def users_post_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> None:
    user = message.from_user
    if not user:
        return

    if not await check_rate_limit(redis_client, user.id):
        await message.reply(f"{make_hello()} Подожди немного перед следующим сообщением :)")
        return

    settings = get_settings()
    await notify_admins(bot, message)
    await bot.copy_message(settings.tgk, message.chat.id, message.message_id)
    await set_good_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, f"{make_hello()} Твое сообщение опубликовано :)", mood="good")
