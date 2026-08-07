from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from common.config import get_chat_message
from chat_bot.matching import ChatMatching
from chat_bot.message_map import MessageMap

router = Router(name="chat_stop")


@router.message(Command("stop"))
async def stop_handler(message: Message, matching: ChatMatching, message_map: MessageMap) -> None:
    user = message.from_user
    if not user:
        return

    status, partner_id = await matching.stop_user(user.id)
    if status == "pair":
        stop_text = get_chat_message("stop_message")
        await message.answer(stop_text, reply_markup=ReplyKeyboardRemove())
        if partner_id:
            await message.bot.send_message(partner_id, stop_text, reply_markup=ReplyKeyboardRemove())
            await message_map.clear_for_users(user.id, partner_id)
    elif status == "waiting":
        await message.answer(get_chat_message("stop_find_message"), reply_markup=ReplyKeyboardRemove())
