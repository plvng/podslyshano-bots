from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, MessageReactionUpdated, ReplyKeyboardMarkup, ReplyKeyboardRemove

from common.config import get_chat_message, get_settings
from common.subscription import is_admin
from chat_bot.matching import ChatMatching
from chat_bot.message_map import MessageMap

logger = logging.getLogger(__name__)
router = Router(name="chat_admin")


def make_user_info(user) -> str:
    username = f" @{user.username}" if user.username else ""
    return f"{user.full_name}{username}"


@router.message(Command("online"))
async def online_handler(message: Message, matching: ChatMatching) -> None:
    online_num = await matching.online_count()
    text = get_chat_message("online_message", default="🍭ОНЛАЙН: 🍭")
    await message.answer(f"{text[:-1]}{online_num}{text[-1]}", reply_markup=ReplyKeyboardRemove())


@router.message(Command("get"))
async def get_info_handler(message: Message) -> None:
    settings = get_settings()
    user = message.from_user
    if not user or not await is_admin(message.bot, settings.tgk, user.id):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        return

    target_id = int(parts[1])
    member = await message.bot.get_chat_member(chat_id=settings.tgk, user_id=target_id)
    await message.answer(make_user_info(member.user), reply_markup=ReplyKeyboardRemove())


@router.message(Command("contact"))
async def contact_command_handler(message: Message, matching: ChatMatching) -> None:
    user = message.from_user
    if not user or not await matching.is_paired(user.id):
        return

    button_text = get_chat_message("contact_button", default="даю свой контакт собеседнику")
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=button_text, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(get_chat_message("contact_message"), reply_markup=markup)


@router.message_reaction()
async def reaction_handler(
    event: MessageReactionUpdated,
    matching: ChatMatching,
    message_map: MessageMap,
) -> None:
    user = event.user
    if not user:
        return

    partner_id = await matching.get_partner(user.id)
    if not partner_id:
        return

    partner_message_id = await message_map.get(user.id, event.message_id)
    if not partner_message_id:
        return

    new_reaction = event.new_reaction
    try:
        await event.bot.set_message_reaction(
            chat_id=partner_id,
            message_id=partner_message_id,
            reaction=[] if not new_reaction else [new_reaction[0]],
        )
    except Exception:
        await event.bot.send_message(user.id, get_chat_message("premium_message"))
