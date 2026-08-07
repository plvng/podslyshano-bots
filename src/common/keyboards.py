from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_PUBLISH = "📢 Опубликовать в канал"
BTN_SUPPORT = "💬 Написать админам"
BTN_START_CHAT = "🍭 Начать диалог"
BTN_STOP_CHAT = "🍭 Закончить диалог"


def proposal_keyboard(mode: str = "publish") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PUBLISH)],
            [KeyboardButton(text=BTN_SUPPORT)],
        ],
        resize_keyboard=True,
    )


def chat_keyboard(active: bool = False) -> ReplyKeyboardMarkup:
    label = BTN_STOP_CHAT if active else BTN_START_CHAT
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label)]],
        resize_keyboard=True,
    )
