from __future__ import annotations

from typing import Any, Awaitable, Callable

import redis.asyncio as redis
from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject

from common.config import get_settings
from common.subscription_cache import check_channel_subscription

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, *, skip_commands: tuple[str, ...] = ()) -> None:
        self.skip_commands = skip_commands

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        if event.text and event.text.startswith("/"):
            command = event.text.split()[0].split("@")[0]
            if command in self.skip_commands:
                return await handler(event, data)

        bot: Bot = data["bot"]
        settings = get_settings()
        user_id = event.from_user.id
        redis_client: redis.Redis | None = data.get("redis_client")

        if await check_channel_subscription(bot, settings.tgk, user_id, redis_client):
            return await handler(event, data)

        await bot.send_message(
            user_id,
            f"🍭Подпишись на {settings.tgk}, чтобы пользоваться ботом🍭",
        )
        return None
