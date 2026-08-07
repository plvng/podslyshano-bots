from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from chat_bot.matching import ChatMatching
from chat_bot.message_map import MessageMap

logger = logging.getLogger(__name__)
router = Router(name="chat_relay")


@router.message(F.contact)
async def contact_handler(message: Message, matching: ChatMatching) -> None:
    user = message.from_user
    if not user or not message.contact:
        return

    partner_id = await matching.get_partner(user.id)
    if not partner_id:
        return

    await message.bot.send_contact(
        partner_id,
        phone_number=message.contact.phone_number,
        first_name=message.contact.first_name,
        last_name=message.contact.last_name,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(~Command())
async def relay_handler(message: Message, matching: ChatMatching, message_map: MessageMap) -> None:
    user = message.from_user
    if not user:
        return

    partner_id = await matching.get_partner(user.id)
    if not partner_id:
        return

    reply_to_id = None
    if message.reply_to_message:
        reply_to_id = await message_map.get(user.id, message.reply_to_message.message_id)

    try:
        sent = await message.bot.copy_message(
            chat_id=partner_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            reply_to_message_id=reply_to_id,
            reply_markup=ReplyKeyboardRemove(),
        )
        await message_map.link(user.id, message.message_id, partner_id, sent.message_id)
        text = message.text or (message.contact.phone_number if message.contact else "media")
        logger.info("%s %s", user.id, text)
    except Exception as exc:
        logger.warning("Relay failed for user %s: %s", user.id, exc)
