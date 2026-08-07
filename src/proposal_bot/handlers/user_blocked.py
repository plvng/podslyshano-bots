from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import Message

from common.config import get_block_message
from common.db.repository import Database
from common.greetings import make_hello
from proposal_bot.filters import IsBlockedFilter, IsNotAdminFilter, IsPostFilter
from proposal_bot.services.admin_notify import notify_admins
from proposal_bot.services.reactions import reply_with_effect, set_bad_reaction

router = Router(name="user_blocked")


@router.message(IsNotAdminFilter(), IsBlockedFilter(), IsPostFilter())
async def users_blocked_handler(message: Message, bot: Bot, db: Database) -> None:
    await notify_admins(bot, message)
    await set_bad_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, f"{make_hello()} {get_block_message()}", mood="bad")
