from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

MEMBER_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


async def check_channel_subscription(bot: Bot, channel_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in MEMBER_STATUSES
    except TelegramAPIError as exc:
        logger.warning("Subscription check failed for user %s: %s", user_id, exc)
        return False


async def is_admin(bot: Bot, channel_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
    except TelegramAPIError:
        return False
