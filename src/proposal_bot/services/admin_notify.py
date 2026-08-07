from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import Message

from common.config import get_settings

logger = logging.getLogger(__name__)


def make_user_info(message: Message) -> str:
    user = message.from_user
    assert user is not None
    username = f" @{user.username}" if user.username else ""
    return f"<code>{user.id}</code>{username}"


async def notify_admins(bot: Bot, message: Message) -> None:
    settings = get_settings()
    for admin_id in settings.admins:
        try:
            await bot.send_message(admin_id, make_user_info(message), parse_mode="HTML")
            await bot.forward_message(admin_id, message.chat.id, message.message_id)
        except Exception as exc:
            logger.warning("Failed to notify admin %s: %s", admin_id, exc)
