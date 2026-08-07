from __future__ import annotations

from aiogram.types import Message

from common.config import get_badwords, get_keywords


def get_message_text(message: Message) -> str:
    if message.text:
        return message.text
    if message.caption:
        return message.caption
    return ""


def is_support(message: Message) -> bool:
    text = get_message_text(message).lower()
    return any(keyword.lower() in text for keyword in get_keywords())


def is_admin_parody(message: Message) -> bool:
    text = get_message_text(message).lower()
    return any(word.lower() in text for word in get_badwords())


def is_words_in(message: Message) -> bool:
    text = get_message_text(message).lower()
    words = [word.lower() for word in get_keywords() + get_badwords()]
    return any(keyword in text for keyword in words)
