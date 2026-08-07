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
        # Only trust positive cache. A cached "0" would block users
        # who re-subscribe within TTL — always recheck Telegram then.
        if cached == "1":
            return True

    subscribed = await _check_subscription(bot, channel_id, user_id)
    if redis_client is not None:
        if subscribed:
            await redis_client.setex(cache_key, CACHE_TTL, "1")
        else:
            # Drop stale positive cache after unsubscribe; do not cache "0".
            await redis_client.delete(cache_key)
    return subscribed
