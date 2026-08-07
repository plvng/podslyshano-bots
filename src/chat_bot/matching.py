from __future__ import annotations

import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)

WAITING_KEY = "chat:waiting"
PAIRS_KEY = "chat:pairs"
SESSION_KEY_PREFIX = "chat:session:"


class ChatMatching:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    def _session_key(self, user_id: int) -> str:
        return f"{SESSION_KEY_PREFIX}{user_id}"

    async def is_waiting(self, user_id: int) -> bool:
        position = await self.redis.lpos(WAITING_KEY, str(user_id))
        return position is not None

    async def is_paired(self, user_id: int) -> bool:
        partner = await self.redis.hget(PAIRS_KEY, str(user_id))
        return partner is not None

    async def is_active(self, user_id: int) -> bool:
        return await self.is_waiting(user_id) or await self.is_paired(user_id)

    async def get_partner(self, user_id: int) -> int | None:
        partner = await self.redis.hget(PAIRS_KEY, str(user_id))
        return int(partner) if partner else None

    async def get_session_id(self, user_id: int) -> int | None:
        value = await self.redis.get(self._session_key(user_id))
        return int(value) if value else None

    async def set_session_id(self, user_id: int, partner_id: int, session_id: int) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(self._session_key(user_id), str(session_id))
            pipe.set(self._session_key(partner_id), str(session_id))
            await pipe.execute()

    async def clear_session_id(self, user_id: int, partner_id: int | None) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(self._session_key(user_id))
            if partner_id is not None:
                pipe.delete(self._session_key(partner_id))
            await pipe.execute()

    async def add_to_waiting(self, user_id: int) -> None:
        await self.redis.rpush(WAITING_KEY, str(user_id))

    async def remove_from_waiting(self, user_id: int) -> None:
        await self.redis.lrem(WAITING_KEY, 0, str(user_id))

    async def try_match(self, user_id: int) -> int | None:
        while True:
            partner_raw = await self.redis.lpop(WAITING_KEY)
            if not partner_raw:
                return None
            partner_id = int(partner_raw)
            if partner_id == user_id:
                continue
            if await self.is_paired(partner_id):
                continue
            await self.create_pair(user_id, partner_id)
            return partner_id

    async def create_pair(self, user_id: int, partner_id: int) -> None:
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(PAIRS_KEY, str(user_id), str(partner_id))
            pipe.hset(PAIRS_KEY, str(partner_id), str(user_id))
            await pipe.execute()
        logger.info("Matched users %s and %s", user_id, partner_id)

    async def stop_user(self, user_id: int) -> tuple[str, int | None]:
        if await self.is_paired(user_id):
            partner_id = await self.get_partner(user_id)
            await self.break_pair(user_id, partner_id)
            return "pair", partner_id

        if await self.is_waiting(user_id):
            await self.remove_from_waiting(user_id)
            return "waiting", None

        return "idle", None

    async def break_pair(self, user_id: int, partner_id: int | None = None) -> None:
        if partner_id is None:
            partner_id = await self.get_partner(user_id)
        if partner_id is None:
            return

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hdel(PAIRS_KEY, str(user_id), str(partner_id))
            await pipe.execute()
        await self.clear_session_id(user_id, partner_id)
        logger.info("Stopped pair %s %s", user_id, partner_id)

    async def online_count(self) -> int:
        waiting = await self.redis.llen(WAITING_KEY)
        pairs = await self.redis.hlen(PAIRS_KEY)
        return waiting + pairs // 2

    async def get_all_active_users(self) -> tuple[list[int], list[int]]:
        waiting_raw = await self.redis.lrange(WAITING_KEY, 0, -1)
        waiting = [int(user_id) for user_id in waiting_raw]

        pairs_raw = await self.redis.hgetall(PAIRS_KEY)
        paired: list[int] = []
        seen: set[int] = set()
        for user_id_str in pairs_raw:
            user_id = int(user_id_str)
            if user_id in seen:
                continue
            seen.add(user_id)
            paired.append(user_id)

        return waiting, paired

    async def clear_all(self) -> None:
        keys = [key async for key in self.redis.scan_iter(match=f"{SESSION_KEY_PREFIX}*")]
        if keys:
            await self.redis.delete(*keys)
        await self.redis.delete(WAITING_KEY, PAIRS_KEY)
