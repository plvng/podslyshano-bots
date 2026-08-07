from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message, MessageReactionUpdated, ReplyKeyboardRemove

from common.config import get_chat_message, get_settings
from common.keyboards import BTN_START_CHAT, BTN_STOP_CHAT
from common.db.repository import Database
from chat_bot.matching import ChatMatching
from chat_bot.message_map import MessageMap

logger = logging.getLogger(__name__)
router = Router(name="chat_relay")


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


@router.message(~F.text.in_({BTN_START_CHAT, BTN_STOP_CHAT}))
async def relay_handler(
    message: Message,
    db: Database,
    matching: ChatMatching,
    message_map: MessageMap,
) -> None:
    if message.text and message.text.startswith("/"):
        return
    user = message.from_user
    if not user:
        return

    partner_id = await matching.get_partner(user.id)
    if not partner_id:
        return

    session_id = await matching.get_session_id(user.id)
    if session_id is None:
        session_id = await db.get_active_chat_session_for_user(user.id)

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
        if session_id:
            await db.add_chat_message(session_id, user.id, message, sent.message_id)
        text = message.text or "media"
        logger.info("%s %s", user.id, text)
    except Exception as exc:
        logger.warning("Relay failed for user %s: %s", user.id, exc)
