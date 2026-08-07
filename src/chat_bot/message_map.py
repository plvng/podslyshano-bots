from __future__ import annotations

import redis.asyncio as redis

MESSAGE_MAP_PREFIX = "chat:msgmap:"
MESSAGE_MAP_TTL = 86400


class MessageMap:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    def _key(self, user_id: int, message_id: int) -> str:
        return f"{MESSAGE_MAP_PREFIX}{user_id}:{message_id}"

    async def get(self, user_id: int, message_id: int) -> int | None:
        value = await self.redis.get(self._key(user_id, message_id))
        return int(value) if value else None

    async def link(
        self,
        user_id: int,
        message_id: int,
        partner_id: int,
        partner_message_id: int,
    ) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(self._key(user_id, message_id), partner_message_id, ex=MESSAGE_MAP_TTL)
            pipe.set(self._key(partner_id, partner_message_id), message_id, ex=MESSAGE_MAP_TTL)
            await pipe.execute()

    async def clear_for_users(self, user_id: int, partner_id: int) -> None:
        pattern = f"{MESSAGE_MAP_PREFIX}*"
        keys = [key async for key in self.redis.scan_iter(match=pattern)]
        to_delete: list[str] = []
        for key in keys:
            parts = key.removeprefix(MESSAGE_MAP_PREFIX).split(":", 1)
            if len(parts) == 2 and parts[0] in {str(user_id), str(partner_id)}:
                to_delete.append(key)
        if to_delete:
            await self.redis.delete(*to_delete)

    async def clear_all(self) -> None:
        keys = [key async for key in self.redis.scan_iter(match=f"{MESSAGE_MAP_PREFIX}*")]
        if keys:
            await self.redis.delete(*keys)
