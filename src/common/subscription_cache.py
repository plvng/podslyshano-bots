from __future__ import annotations

import logging

import redis.asyncio as redis
from aiogram import Bot

from common.config import get_settings
from common.subscription import check_channel_subscription as _check_subscription

logger = logging.getLogger(__name__)

CACHE_TTL = 600


async def check_channel_subscription(
    bot: Bot,
    channel_id: str,
    user_id: int,
    redis_client: redis.Redis | None = None,
) -> bool:
    settings = get_settings()
    if user_id in settings.admins:
        return True

    cache_key = f"sub:{user_id}"
    if redis_client is not None:
        cached = await redis_client.get(cache_key)
        if cached == "1":
            return True
        if cached == "0":
            return False

    subscribed = await _check_subscription(bot, channel_id, user_id)
    if redis_client is not None:
        await redis_client.setex(cache_key, CACHE_TTL, "1" if subscribed else "0")
    return subscribed
