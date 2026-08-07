from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from common.config import get_chat_message, get_settings
from common.db.repository import Database
from common.keyboards import BTN_START_CHAT, BTN_STOP_CHAT, chat_keyboard
from common.subscription_cache import check_channel_subscription
from chat_bot.matching import ChatMatching
from chat_bot.message_map import MessageMap

router = Router(name="chat_dialog")


@router.message(F.text == BTN_START_CHAT)
async def start_dialog(
    message: Message,
    db: Database,
    matching: ChatMatching,
    redis_client,
) -> None:
    settings = get_settings()
    user = message.from_user
    if not user:
        return

    if not await check_channel_subscription(message.bot, settings.tgk, user.id, redis_client):
        await message.answer(f"🍭Подпишись на {settings.tgk} ЧТОБ РАБОТАЛО🍭")
        return

    if await matching.is_waiting(user.id):
        await message.answer(get_chat_message("find_message_2"), reply_markup=chat_keyboard(True))
        return

    if await matching.is_paired(user.id):
        await message.answer(get_chat_message("find_pair_message"), reply_markup=chat_keyboard(True))
        return

    partner_id = await matching.try_match(user.id)
    if partner_id:
        session_id = await db.create_chat_session(user.id, partner_id)
        await matching.set_session_id(user.id, partner_id, session_id)
        found = get_chat_message("found_message")
        await message.answer(found, reply_markup=chat_keyboard(True))
        await message.bot.send_message(partner_id, found, reply_markup=chat_keyboard(True))
        return

    await matching.add_to_waiting(user.id)
    await message.answer(get_chat_message("find_message"), reply_markup=chat_keyboard(True))


@router.message(F.text == BTN_STOP_CHAT)
async def stop_dialog(
    message: Message,
    db: Database,
    matching: ChatMatching,
    message_map: MessageMap,
) -> None:
    user = message.from_user
    if not user:
        return

    session_id = await matching.get_session_id(user.id) or await db.get_active_chat_session_for_user(user.id)
    status, partner_id = await matching.stop_user(user.id)
    if status == "pair":
        if session_id:
            await db.end_chat_session(session_id)
        stop_text = get_chat_message("stop_message")
        await message.answer(stop_text, reply_markup=chat_keyboard(False))
        if partner_id:
            await message.bot.send_message(partner_id, stop_text, reply_markup=chat_keyboard(False))
            await message_map.clear_for_users(user.id, partner_id)
    elif status == "waiting":
        await message.answer(get_chat_message("stop_find_message"), reply_markup=chat_keyboard(False))
    else:
        await message.answer(get_chat_message("idle_hint"), reply_markup=chat_keyboard(False))
