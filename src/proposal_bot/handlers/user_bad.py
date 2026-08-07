from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import Message

from common.config import get_settings
from common.db.repository import Database
from common.greetings import make_hello
from proposal_bot.filters import IsAdminParodyFilter, IsNotAdminFilter, IsNotBlockedFilter
from proposal_bot.services.admin_notify import notify_admins
from proposal_bot.services.reactions import reply_with_effect, set_bad_reaction

router = Router(name="user_bad")


@router.message(IsNotAdminFilter(), IsNotBlockedFilter(), IsAdminParodyFilter())
async def users_bad_handler(message: Message, bot: Bot, db: Database) -> None:
    await notify_admins(bot, message)
    await set_bad_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, f"{make_hello()} Ты не админ :(", mood="bad")
