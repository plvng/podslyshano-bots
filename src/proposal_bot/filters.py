from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from common.config import get_settings
from common.db.repository import Database
from proposal_bot.services.moderation import is_admin_parody, is_support, is_words_in


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        return bool(user and user.id in get_settings().admins)


class IsNotAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        return bool(user and user.id not in get_settings().admins)


class IsBlockedFilter(BaseFilter):
    async def __call__(self, message: Message, db: Database) -> bool:
        user = message.from_user
        if not user:
            return False
        return await db.is_blocked(user.id)


class IsNotBlockedFilter(BaseFilter):
    async def __call__(self, message: Message, db: Database) -> bool:
        user = message.from_user
        if not user:
            return False
        return not await db.is_blocked(user.id)


class IsSupportFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return is_support(message) or message.reply_to_message is not None


class IsAdminParodyFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return is_admin_parody(message) and not is_support(message)


class IsPostFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return not is_words_in(message) and message.reply_to_message is None


class IsReplyFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.reply_to_message is not None


class IsNumericTextFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.text and message.text.strip().isdigit())
