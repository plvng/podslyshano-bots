from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from common.config import get_chat_message, get_settings
from common.greetings import make_hello
from common.subscription import check_channel_subscription

router = Router(name="chat_start")


def start_message() -> str:
    settings = get_settings()
    return (
        f"🍭{make_hello()} Знакомства в МГУТУ от админов {settings.tgk}!\n"
        "/find - найти собеседника\n"
        "/stop - прервать диалог/поиск\n"
        "/online - сколько сейчас в сети\n"
        "/contact - поделиться контактом\n"
        "Будь осторожней!🍭"
    )


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    settings = get_settings()
    user = message.from_user
    if not user:
        return

    subscribed = await check_channel_subscription(message.bot, settings.tgk, user.id)
    if not subscribed and user.id not in settings.admins:
        await message.answer(
            f"🍭Подпишись на {settings.tgk}, чтобы пользоваться ботом🍭",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await message.answer(start_message(), reply_markup=ReplyKeyboardRemove())
