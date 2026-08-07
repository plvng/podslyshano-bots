from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from common.config import get_block_message, get_config_value
from common.db.repository import Database
from common.greetings import make_hello
from common.keyboards import BTN_PUBLISH, BTN_SUPPORT, proposal_keyboard
from proposal_bot.services.reactions import reply_with_effect

router = Router(name="mode")


@router.message(F.text == BTN_SUPPORT)
async def switch_to_support(message: Message, db: Database) -> None:
    user = message.from_user
    if not user or await db.is_blocked(user.id):
        await message.answer(get_block_message(), reply_markup=proposal_keyboard())
        return

    await db.set_mode(user.id, "support")
    hint = get_config_value("proposal", "support_mode_hint", default="Режим переписки с админами.")
    await reply_with_effect(message, f"{make_hello()} {hint}", mood="good")
    await message.answer("Режим: переписка с админами.", reply_markup=proposal_keyboard("support"))


@router.message(F.text == BTN_PUBLISH)
async def switch_to_publish(message: Message, db: Database) -> None:
    user = message.from_user
    if not user or await db.is_blocked(user.id):
        await message.answer(get_block_message(), reply_markup=proposal_keyboard())
        return

    await db.set_mode(user.id, "publish")
    hint = get_config_value("proposal", "publish_mode_hint", default="Режим публикации в канал.")
    await reply_with_effect(message, f"{make_hello()} {hint}", mood="good")
    await message.answer("Режим: публикация в канал.", reply_markup=proposal_keyboard("publish"))
