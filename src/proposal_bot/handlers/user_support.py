from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import Message

from common.config import get_settings
from common.greetings import make_hello
from proposal_bot.filters import IsNotAdminFilter, IsSupportFilter
from proposal_bot.services.admin_notify import notify_admins
from proposal_bot.services.moderation import is_support
from proposal_bot.services.reactions import reply_with_effect, set_good_reaction

router = Router(name="user_support")


@router.message(IsNotAdminFilter(), IsSupportFilter())
async def users_support_handler(message: Message, bot: Bot) -> None:
    settings = get_settings()
    await notify_admins(bot, message)
    await set_good_reaction(bot, message.chat.id, message.message_id)

    if is_support(message):
        answer = (
            f"{make_hello()} Обращение отправлено админам.\n"
            f"Если админ тебе пишет, отвечай (сдвигом влево, двойным нажатием или как там у тебя настроено) "
            f"на сообщения, чтобы оставаться в диалоге и не публиковаться в {settings.tgk} :)"
        )
    else:
        answer = "Ответ отправлен админам :)"

    await reply_with_effect(message, answer, mood="good")
