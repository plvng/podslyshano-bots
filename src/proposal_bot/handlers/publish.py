from __future__ import annotations

import asyncio
import logging

import redis.asyncio as redis
from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from common.config import get_block_message, get_settings
from common.db.repository import Database
from common.greetings import make_hello
from common.keyboards import BTN_PUBLISH, BTN_SUPPORT, proposal_keyboard
from proposal_bot.services.reactions import reply_with_effect, set_good_reaction

logger = logging.getLogger(__name__)
router = Router(name="publish")

# Collect album parts, then publish once. Never use forward_* — only copy_*
# so the channel post has no author / nickname / "forwarded from".
ALBUM_KEY = "proposal:album:{user_id}:{group_id}"
ALBUM_WAIT_SECONDS = 1.2


async def check_rate_limit(redis_client: redis.Redis, user_id: int) -> bool:
    from common.config import get_rate_limit_seconds

    key = f"proposal:rate:{user_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, get_rate_limit_seconds())
    return count <= 1


async def _ensure_can_publish(
    message: Message,
    db: Database,
    redis_client: redis.Redis,
    *,
    apply_rate_limit: bool,
) -> str | None:
    """Return None if ok, 'skip' to UNHANDLED, 'stop' if already answered."""
    user = message.from_user
    if not user:
        return "skip"

    if message.text and message.text.startswith("/"):
        return "skip"

    if await db.is_blocked(user.id):
        await message.answer(get_block_message(), reply_markup=proposal_keyboard())
        return "stop"

    if await db.get_mode(user.id) != "publish":
        return "skip"

    if apply_rate_limit and not await check_rate_limit(redis_client, user.id):
        await message.reply(f"{make_hello()} Подожди немного перед следующим сообщением :)")
        return "stop"

    return None


async def _copy_anonymous(
    bot: Bot,
    chat_id: str,
    from_chat_id: int,
    message_ids: list[int],
) -> int:
    """Copy without forward header / author. Prefer copy_messages for albums."""
    if len(message_ids) == 1:
        copied = await bot.copy_message(chat_id, from_chat_id, message_ids[0])
        return copied.message_id

    # Bot API copyMessages keeps media group and strips authorship.
    result = await bot.copy_messages(chat_id, from_chat_id, message_ids)
    if not result:
        raise RuntimeError("copy_messages returned empty")
    return int(result[0].message_id)

async def _finish_publish(
    message: Message,
    bot: Bot,
    db: Database,
    channel_message_id: int,
) -> None:
    user = message.from_user
    assert user
    await db.create_proposal_post(user.id, channel_message_id, message)
    await set_good_reaction(bot, message.chat.id, message.message_id)
    await reply_with_effect(message, f"{make_hello()} Твое сообщение опубликовано :)", mood="good")


async def _publish_album(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    user = message.from_user
    if not user or not message.media_group_id:
        return UNHANDLED

    gate = await _ensure_can_publish(message, db, redis_client, apply_rate_limit=False)
    if gate == "skip":
        return UNHANDLED
    if gate == "stop":
        return None

    group_id = message.media_group_id
    key = ALBUM_KEY.format(user_id=user.id, group_id=group_id)
    await redis_client.rpush(key, str(message.message_id))
    await redis_client.expire(key, 30)

    # Debounce: wait for remaining album parts to arrive.
    await asyncio.sleep(ALBUM_WAIT_SECONDS)

    raw_ids = await redis_client.lrange(key, 0, -1)
    if not raw_ids:
        return None

    # Only the "last waiter" that still sees the full list should publish.
    # Delete key first so concurrent waiters exit.
    deleted = await redis_client.delete(key)
    if not deleted:
        return None

    message_ids = sorted({int(item) for item in raw_ids})
    if not await check_rate_limit(redis_client, user.id):
        await message.reply(f"{make_hello()} Подожди немного перед следующим сообщением :)")
        return None

    settings = get_settings()
    try:
        channel_message_id = await _copy_anonymous(
            bot, settings.tgk, message.chat.id, message_ids
        )
    except (TelegramAPIError, RuntimeError) as exc:
        logger.exception("Failed to publish album from %s to %s", user.id, settings.tgk)
        err = getattr(exc, "message", str(exc))
        await message.answer(
            f"Не удалось опубликовать альбом в {settings.tgk}. "
            f"Проверь, что бот — админ канала. Ошибка: {err}"
        )
        return None

    await _finish_publish(message, bot, db, channel_message_id)
    logger.info("Published album of %s items from %s", len(message_ids), user.id)
    return None


async def _publish_single(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    if message.media_group_id:
        return await _publish_album(message, bot, db, redis_client)

    gate = await _ensure_can_publish(message, db, redis_client, apply_rate_limit=True)
    if gate == "skip":
        return UNHANDLED
    if gate == "stop":
        return None

    settings = get_settings()
    user = message.from_user
    assert user
    try:
        channel_message_id = await _copy_anonymous(
            bot, settings.tgk, message.chat.id, [message.message_id]
        )
    except (TelegramAPIError, RuntimeError) as exc:
        logger.exception("Failed to publish message from %s to %s", user.id, settings.tgk)
        err = getattr(exc, "message", str(exc))
        await message.answer(
            f"Не удалось опубликовать в {settings.tgk}. "
            f"Проверь, что бот — админ канала. Ошибка: {err}"
        )
        return None

    await _finish_publish(message, bot, db, channel_message_id)
    return None


@router.message(F.text, ~F.text.in_({BTN_PUBLISH, BTN_SUPPORT}))
async def publish_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    return await _publish_single(message, bot, db, redis_client)


@router.message(~F.text)
async def publish_media_handler(
    message: Message,
    bot: Bot,
    db: Database,
    redis_client: redis.Redis,
) -> object:
    return await _publish_single(message, bot, db, redis_client)
