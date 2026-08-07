from __future__ import annotations

from aiogram import Router
from aiogram.types import Message

from common.db.repository import Database
from proposal_bot.filters import IsAdminFilter, IsNumericTextFilter
from proposal_bot.services.reactions import reply_with_effect, set_bad_reaction, set_good_reaction

router = Router(name="admin_block")


@router.message(IsAdminFilter(), IsNumericTextFilter())
async def admins_block_handler(message: Message, db: Database) -> None:
    assert message.text is not None
    selected_id = int(message.text.strip())
    blocked = await db.toggle_block(selected_id)

    if blocked:
        await set_bad_reaction(message.bot, message.chat.id, message.message_id)
        await reply_with_effect(message, "заблокирован :/", mood="bad")
    else:
        await set_good_reaction(message.bot, message.chat.id, message.message_id)
        await reply_with_effect(message, "разблокирован :)", mood="good")
