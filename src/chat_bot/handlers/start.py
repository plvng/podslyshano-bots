from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from common.config import get_chat_message, get_settings
from common.db.repository import Database
from common.greetings import make_hello
from common.keyboards import chat_keyboard
from common.subscription_cache import check_channel_subscription
from chat_bot.matching import ChatMatching

router = Router(name="chat_start")


@router.message(CommandStart())
async def start_handler(
    message: Message,
    db: Database,
    matching: ChatMatching,
    redis_client,
) -> None:
    settings = get_settings()
    user = message.from_user
    if not user:
        return

    await db.upsert_user(user.id, user.username, user.full_name)

    subscribed = await check_channel_subscription(message.bot, settings.tgk, user.id, redis_client)
    if not subscribed and user.id not in settings.admins:
        await message.answer(f"Подпишись на {settings.tgk}, чтобы пользоваться ботом.")
        return

    active = await matching.is_active(user.id)
    text = (
        f"{make_hello()} Анонимные знакомства от админов {settings.tgk}.\n"
        f"{get_chat_message('idle_hint', default='Нажми «Начать диалог», чтобы найти собеседника.')}\n"
        "Будь осторожен."
    )
    await message.answer(text, reply_markup=chat_keyboard(active))
