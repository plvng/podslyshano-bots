from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from common.config import get_block_message, get_settings
from common.db.repository import Database
from common.greetings import make_hello
from common.keyboards import BTN_PUBLISH, BTN_SUPPORT, proposal_keyboard
from proposal_bot.services.reactions import reply_with_effect, set_good_reaction

logger = logging.getLogger(__name__)
router = Router(name="support")


async def notify_admins_new_support(bot: Bot, thread_id: int, user_id: int) -> None:
    settings = get_settings()
    text = f"Новое обращение #{thread_id} от пользователя {user_id}"
    for admin_id in settings.admins:
        try:
            await bot.send_message(admin_id, text)
        except Exception as exc:
            logger.warning("Failed to notify admin %s: %s", admin_id, exc)


@router.message(~F.text.in_({BTN_PUBLISH, BTN_SUPPORT}))
async def support_handler(message: Message, bot: Bot, db: Database) -> None:
    user = message.from_user
    if not user:
        return

    if await db.is_blocked(user.id):
        await message.answer(get_block_message(), reply_markup=proposal_keyboard())
        return

    if await db.get_mode(user.id) != "support":
        return

    thread_id = await db.get_or_create_open_support_thread(user.id)
    await db.add_support_message(thread_id, user.id, "user", message, message.message_id)
    await set_good_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(
        message,
        f"{make_hello()} Сообщение отправлено админам (обращение #{thread_id}).",
        mood="good",
    )
    await notify_admins_new_support(bot, thread_id, user.id)
