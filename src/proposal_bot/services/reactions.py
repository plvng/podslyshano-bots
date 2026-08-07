from __future__ import annotations

import logging
import random

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, ReactionTypeEmoji

from common.config import get_emoji, get_effects

logger = logging.getLogger(__name__)


def pick_effect(mood: str) -> str | None:
    effects = get_effects(mood)
    return random.choice(effects) if effects else None


def pick_reactions(mood: str) -> list[ReactionTypeEmoji] | None:
    emojis = get_emoji(mood)
    if not emojis:
        return None
    return [ReactionTypeEmoji(emoji=random.choice(emojis))]


async def set_good_reaction(bot: Bot, chat_id: int, message_id: int) -> None:
    reactions = pick_reactions("good")
    if not reactions:
        return
    try:
        await bot.set_message_reaction(chat_id=chat_id, message_id=message_id, reaction=reactions, is_big=True)
    except TelegramAPIError as exc:
        logger.debug("Reaction not set: %s", exc)


async def set_bad_reaction(bot: Bot, chat_id: int, message_id: int) -> None:
    reactions = pick_reactions("bad")
    if not reactions:
        return
    try:
        await bot.set_message_reaction(chat_id=chat_id, message_id=message_id, reaction=reactions, is_big=True)
    except TelegramAPIError as exc:
        logger.debug("Reaction not set: %s", exc)


async def reply_with_effect(
    message: Message,
    text: str,
    *,
    mood: str,
    reply: bool = True,
) -> Message:
    kwargs = {"message_effect_id": effect} if (effect := pick_effect(mood)) else {}
    if reply:
        return await message.reply(text, **kwargs)
    return await message.answer(text, **kwargs)
