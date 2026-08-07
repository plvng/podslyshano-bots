from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as redis
from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)

from chat_bot.matching import ChatMatching
from common.config import get_settings
from common.db.repository import Database

logger = logging.getLogger(__name__)
router = Router(name="panel")

ADMIN_REPLY_KEY = "admin:reply:{admin_id}"
ADMIN_REPLY_TTL = 900


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and user.id in get_settings().admins)


def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admins


def reply_key(admin_id: int) -> str:
    return ADMIN_REPLY_KEY.format(admin_id=admin_id)


def user_label(row: dict[str, Any]) -> str:
    username = row.get("username")
    full_name = row.get("full_name")
    user_id = row.get("user_id")
    if username:
        return f"@{username} ({user_id})"
    if full_name:
        return f"{full_name} ({user_id})"
    return str(user_id)


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Обращения", callback_data="adm:sup:list"),
                InlineKeyboardButton(text="Блокировки", callback_data="adm:blocks"),
            ],
            [
                InlineKeyboardButton(text="Онлайн", callback_data="adm:online"),
                InlineKeyboardButton(text="Обновить", callback_data="adm:refresh"),
            ],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="adm:refresh")]]
    )


async def build_dashboard_text(db: Database, redis_client: redis.Redis) -> str:
    stats = await db.dashboard_stats()
    matching = ChatMatching(redis_client)
    online = await matching.online_count()
    return (
        "<b>Админ-панель</b>\n\n"
        f"Пользователи: {stats['total_users']}\n"
        f"Посты сегодня: {stats['posts_today']} (за неделю: {stats['posts_week']})\n"
        f"Онлайн в анонке: {online}\n"
        f"Активных диалогов: {stats['active_chats']}\n"
        f"Открытых обращений: {stats['open_support']}\n"
        f"В блоке: {stats['blocked_users']}\n\n"
        "Команды: /ban &lt;id&gt; · /unban &lt;id&gt; · /stats"
    )


async def render_dashboard_message(
    message: Message,
    db: Database,
    redis_client: redis.Redis,
    *,
    edit: bool = False,
) -> None:
    text = await build_dashboard_text(db, redis_client)
    markup = main_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def render_support_list(message: Message, db: Database) -> None:
    threads = await db.list_support_threads(status="open")
    if not threads:
        text = "<b>Обращения</b>\n\nОткрытых обращений нет."
        markup = back_keyboard()
    else:
        text = f"<b>Открытые обращения ({len(threads)})</b>\nВыбери тред:"
        buttons = []
        for thread in threads[:20]:
            label = f"#{thread['id']} {user_label(thread)}"
            if len(label) > 60:
                label = label[:57] + "..."
            buttons.append(
                [InlineKeyboardButton(text=label, callback_data=f"adm:sup:{thread['id']}")]
            )
        buttons.append([InlineKeyboardButton(text="Назад", callback_data="adm:refresh")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.edit_text(text, reply_markup=markup)


async def render_support_thread(message: Message, db: Database, thread_id: int) -> None:
    threads = await db.list_support_threads()
    thread = next((item for item in threads if int(item["id"]) == thread_id), None)
    if not thread:
        await message.edit_text("Обращение не найдено.", reply_markup=back_keyboard())
        return

    messages = await db.get_support_messages(thread_id)
    lines = [
        f"<b>Обращение #{thread_id}</b>",
        f"Статус: {thread['status']}",
        f"Пользователь: {user_label(thread)}",
        "",
    ]
    recent = messages[-12:]
    if not recent:
        lines.append("(сообщений пока нет)")
    else:
        for msg in recent:
            who = "USER" if msg.get("direction") == "user" else "ADMIN"
            preview = (msg.get("preview") or msg.get("content_type") or "").strip()
            if len(preview) > 120:
                preview = preview[:117] + "..."
            lines.append(f"<b>{who}:</b> {preview}")

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ответить", callback_data=f"adm:sup:reply:{thread_id}"),
                InlineKeyboardButton(text="Закрыть", callback_data=f"adm:sup:close:{thread_id}"),
            ],
            [InlineKeyboardButton(text="К списку", callback_data="adm:sup:list")],
        ]
    )
    await message.edit_text("\n".join(lines), reply_markup=markup)


@router.message(Command("panel"), IsAdminFilter())
@router.message(Command("stats"), IsAdminFilter())
async def panel_handler(message: Message, db: Database, redis_client: redis.Redis) -> None:
    await render_dashboard_message(message, db, redis_client)


@router.callback_query(F.data == "adm:refresh", IsAdminFilter())
async def refresh_panel(callback: CallbackQuery, db: Database, redis_client: redis.Redis) -> None:
    if not callback.message:
        await callback.answer()
        return
    await render_dashboard_message(callback.message, db, redis_client, edit=True)
    await callback.answer()


@router.callback_query(F.data == "adm:online", IsAdminFilter())
async def online_panel(callback: CallbackQuery, redis_client: redis.Redis) -> None:
    if not callback.message:
        await callback.answer()
        return
    matching = ChatMatching(redis_client)
    waiting, paired = await matching.get_all_active_users()
    online = await matching.online_count()
    text = (
        f"<b>Онлайн в анонке: {online}</b>\n\n"
        f"В очереди: {len(waiting)}\n"
        f"В диалоге: {len(paired)}"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:blocks", IsAdminFilter())
async def blocks_panel(callback: CallbackQuery, db: Database) -> None:
    if not callback.message:
        await callback.answer()
        return
    blocks = await db.list_blocks()
    if not blocks:
        text = "<b>Блокировки</b>\n\nСписок пуст.\n\nБан: /ban &lt;id&gt;\nРазбан: /unban &lt;id&gt;"
    else:
        lines = ["<b>Блокировки</b>", ""]
        for row in blocks[:30]:
            lines.append(f"• {user_label(row)}")
        if len(blocks) > 30:
            lines.append(f"…и ещё {len(blocks) - 30}")
        lines.extend(["", "Бан: /ban <id>", "Разбан: /unban <id>"])
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:sup:list", IsAdminFilter())
async def support_list(callback: CallbackQuery, db: Database) -> None:
    if not callback.message:
        await callback.answer()
        return
    await render_support_list(callback.message, db)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adm:sup:\d+$"), IsAdminFilter())
async def support_thread_view(callback: CallbackQuery, db: Database) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return
    thread_id = int(callback.data.rsplit(":", 1)[-1])
    await render_support_thread(callback.message, db, thread_id)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adm:sup:reply:\d+$"), IsAdminFilter())
async def support_reply_start(callback: CallbackQuery, redis_client: redis.Redis) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        await callback.answer()
        return
    thread_id = int(callback.data.rsplit(":", 1)[-1])
    await redis_client.setex(reply_key(callback.from_user.id), ADMIN_REPLY_TTL, str(thread_id))
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data=f"adm:sup:cancel:{thread_id}")]
        ]
    )
    await callback.message.edit_text(
        f"Ответ на обращение #{thread_id}.\n"
        "Пришли следующее сообщение — оно уйдёт пользователю.",
        reply_markup=markup,
    )
    await callback.answer("Жду сообщение")


@router.callback_query(F.data.regexp(r"^adm:sup:cancel:\d+$"), IsAdminFilter())
async def support_reply_cancel(
    callback: CallbackQuery,
    redis_client: redis.Redis,
    db: Database,
) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        await callback.answer()
        return
    await redis_client.delete(reply_key(callback.from_user.id))
    thread_id = int(callback.data.rsplit(":", 1)[-1])
    await render_support_thread(callback.message, db, thread_id)
    await callback.answer("Отменено")


@router.callback_query(F.data.regexp(r"^adm:sup:close:\d+$"), IsAdminFilter())
async def support_close(callback: CallbackQuery, db: Database) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return
    thread_id = int(callback.data.rsplit(":", 1)[-1])
    await db.close_support_thread(thread_id)
    await render_support_list(callback.message, db)
    await callback.answer("Закрыто")


@router.message(Command("ban"), IsAdminFilter())
async def ban_command(message: Message, command: CommandObject, db: Database) -> None:
    args = (command.args or "").strip()
    if not args.isdigit():
        await message.answer("Использование: /ban &lt;telegram_id&gt;")
        return
    target_id = int(args)
    await db.set_block(target_id, True)
    await message.answer(f"Пользователь {target_id} заблокирован.")


@router.message(Command("unban"), IsAdminFilter())
async def unban_command(message: Message, command: CommandObject, db: Database) -> None:
    args = (command.args or "").strip()
    if not args.isdigit():
        await message.answer("Использование: /unban &lt;telegram_id&gt;")
        return
    target_id = int(args)
    await db.set_block(target_id, False)
    await message.answer(f"Пользователь {target_id} разблокирован.")
