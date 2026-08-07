from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from common.config import get_chat_message, get_settings
from common.subscription import check_channel_subscription
from chat_bot.matching import ChatMatching

router = Router(name="chat_find")


@router.message(Command("find"))
async def find_handler(message: Message, matching: ChatMatching) -> None:
    settings = get_settings()
    user = message.from_user
    if not user:
        return

    if not await check_channel_subscription(message.bot, settings.tgk, user.id):
        await message.answer(
            f"🍭Подпишись на {settings.tgk} ЧТОБ РАБОТАЛО🍭",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if await matching.is_waiting(user.id):
        await message.answer(
            get_chat_message("find_message_2"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if await matching.is_paired(user.id):
        await message.answer(
            get_chat_message("find_pair_message"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    partner_id = await matching.try_match(user.id)
    if partner_id:
        found = get_chat_message("found_message")
        await message.answer(found, reply_markup=ReplyKeyboardRemove())
        await message.bot.send_message(partner_id, found, reply_markup=ReplyKeyboardRemove())
        return

    await matching.add_to_waiting(user.id)
    await message.answer(get_chat_message("find_message"), reply_markup=ReplyKeyboardRemove())
