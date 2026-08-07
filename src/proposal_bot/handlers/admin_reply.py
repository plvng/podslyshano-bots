from __future__ import annotations

import re

from aiogram import Bot, Router
from aiogram.types import Message

from proposal_bot.filters import IsAdminFilter, IsReplyFilter
from proposal_bot.services.reactions import reply_with_effect, set_bad_reaction, set_good_reaction

router = Router(name="admin_reply")


@router.message(IsAdminFilter(), IsReplyFilter())
async def admins_reply_handler(message: Message, bot: Bot) -> None:
    reply = message.reply_to_message
    if not reply or not reply.text:
        await set_bad_reaction(bot, message.chat.id, message.message_id)
        await reply_with_effect(
            message,
            "чтобы ответить пользователю ответь на сообщение в начале которого есть id пользователя :/",
            mood="bad",
        )
        return

    match = re.search(r"\d+", reply.text)
    if not match:
        await set_bad_reaction(bot, message.chat.id, message.message_id)
        await reply_with_effect(
            message,
            "чтобы ответить пользователю ответь на сообщение в начале которого есть id пользователя :/",
            mood="bad",
        )
        return

    await bot.copy_message(int(match.group()), message.chat.id, message.message_id)
    await set_good_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, "отвечено :0", mood="good")
