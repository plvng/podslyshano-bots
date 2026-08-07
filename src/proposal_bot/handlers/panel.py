from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from common.config import get_settings
from common.db.repository import Database

router = Router(name="panel")


@router.message(Command("panel"))
async def panel_handler(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return

    settings = get_settings()
    if user.id not in settings.admins:
        return

    token = await db.create_admin_token(user.id)
    url = f"{settings.admin_web_url.rstrip('/')}/auth?token={token}"
    await message.answer(
        "Ссылка для входа в админ-панель (действует 15 минут):\n"
        f"{url}"
    )
