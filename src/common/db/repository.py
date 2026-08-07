from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from common.db.schema import SCHEMA

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")


def _message_preview(message: Any) -> tuple[str, str, str | None]:
    content_type = "text"
    preview = ""
    payload: dict[str, Any] = {}

    if getattr(message, "text", None):
        content_type = "text"
        preview = message.text[:500]
        payload = {"text": message.text}
    elif getattr(message, "caption", None):
        content_type = message.content_type or "media"
        preview = message.caption[:500]
        payload = {"caption": message.caption, "content_type": content_type}
    elif getattr(message, "photo", None):
        content_type = "photo"
        preview = "[photo]"
        payload = {"content_type": "photo"}
    else:
        content_type = getattr(message, "content_type", None) or "unknown"
        preview = f"[{content_type}]"
        payload = {"content_type": content_type}

    return content_type, preview, json.dumps(payload, ensure_ascii=False)


class Database:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        if self._connection is None:
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
            self._connection = await aiosqlite.connect(self.database_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA journal_mode=WAL")
            await self._connection.execute("PRAGMA busy_timeout=5000")
            await self._connection.executescript(SCHEMA)
            await self._connection.commit()
        return self._connection

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def init(self) -> None:
        await self.connect()
        logger.info("Database initialized at %s", self.database_path)

    async def upsert_user(self, user_id: int, username: str | None, full_name: str | None) -> bool:
        db = await self.connect()
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = await cursor.fetchone() is not None
        await db.execute(
            """
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
            """,
            (user_id, username, full_name),
        )
        await db.commit()
        return not exists

    async def register_user(self, user_id: int, username: str | None) -> bool:
        return await self.upsert_user(user_id, username, None)

    async def is_blocked(self, user_id: int) -> bool:
        db = await self.connect()
        cursor = await db.execute("SELECT user_id FROM blocks WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

    async def toggle_block(self, user_id: int) -> bool:
        db = await self.connect()
        cursor = await db.execute("SELECT user_id FROM blocks WHERE user_id = ?", (user_id,))
        blocked = await cursor.fetchone() is not None
        if blocked:
            await db.execute("DELETE FROM blocks WHERE user_id = ?", (user_id,))
            await db.commit()
            return False
        await db.execute("INSERT INTO blocks (user_id) VALUES (?)", (user_id,))
        await db.commit()
        return True

    async def set_block(self, user_id: int, blocked: bool) -> None:
        if blocked:
            db = await self.connect()
            await db.execute("INSERT OR IGNORE INTO blocks (user_id) VALUES (?)", (user_id,))
            await db.commit()
        else:
            db = await self.connect()
            await db.execute("DELETE FROM blocks WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_mode(self, user_id: int, bot: str = "proposal") -> str:
        db = await self.connect()
        cursor = await db.execute(
            "SELECT mode FROM user_modes WHERE user_id = ? AND bot = ?",
            (user_id, bot),
        )
        row = await cursor.fetchone()
        return row["mode"] if row else "publish"

    async def set_mode(self, user_id: int, mode: str, bot: str = "proposal") -> None:
        db = await self.connect()
        await db.execute(
            """
            INSERT INTO user_modes (user_id, bot, mode, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, bot) DO UPDATE SET mode = excluded.mode, updated_at = excluded.updated_at
            """,
            (user_id, bot, mode, _utcnow()),
        )
        await db.commit()

    async def create_proposal_post(
        self,
        user_id: int,
        channel_message_id: int | None,
        message: Any,
    ) -> int:
        content_type, preview, _ = _message_preview(message)
        db = await self.connect()
        cursor = await db.execute(
            """
            INSERT INTO proposal_posts (user_id, channel_message_id, content_type, preview, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, channel_message_id, content_type, preview, _utcnow()),
        )
        await db.commit()
        return cursor.lastrowid or 0

    async def get_or_create_open_support_thread(self, user_id: int) -> int:
        db = await self.connect()
        cursor = await db.execute(
            "SELECT id FROM support_threads WHERE user_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row:
            return int(row["id"])
        cursor = await db.execute(
            "INSERT INTO support_threads (user_id, status, opened_at) VALUES (?, 'open', ?)",
            (user_id, _utcnow()),
        )
        await db.commit()
        return cursor.lastrowid or 0

    async def add_support_message(
        self,
        thread_id: int,
        user_id: int,
        direction: str,
        message: Any,
        tg_message_id: int | None = None,
    ) -> int:
        content_type, preview, content_json = _message_preview(message)
        db = await self.connect()
        cursor = await db.execute(
            """
            INSERT INTO support_messages
            (thread_id, user_id, direction, tg_message_id, content_type, preview, content_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (thread_id, user_id, direction, tg_message_id, content_type, preview, content_json, _utcnow()),
        )
        await db.commit()
        return cursor.lastrowid or 0

    async def close_support_thread(self, thread_id: int) -> None:
        db = await self.connect()
        await db.execute(
            "UPDATE support_threads SET status = 'closed', closed_at = ? WHERE id = ?",
            (_utcnow(), thread_id),
        )
        await db.commit()

    async def create_chat_session(self, user_a: int, user_b: int) -> int:
        db = await self.connect()
        cursor = await db.execute(
            "INSERT INTO chat_sessions (user_a, user_b, status, started_at) VALUES (?, ?, 'active', ?)",
            (user_a, user_b, _utcnow()),
        )
        await db.commit()
        return cursor.lastrowid or 0

    async def end_chat_session(self, session_id: int) -> None:
        db = await self.connect()
        await db.execute(
            "UPDATE chat_sessions SET status = 'ended', ended_at = ? WHERE id = ?",
            (_utcnow(), session_id),
        )
        await db.commit()

    async def get_active_chat_session_for_user(self, user_id: int) -> int | None:
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT id FROM chat_sessions
            WHERE status = 'active' AND (user_a = ? OR user_b = ?)
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, user_id),
        )
        row = await cursor.fetchone()
        return int(row["id"]) if row else None

    async def add_chat_message(
        self,
        session_id: int,
        sender_id: int,
        message: Any,
        tg_message_id: int | None = None,
    ) -> int:
        content_type, preview, content_json = _message_preview(message)
        db = await self.connect()
        cursor = await db.execute(
            """
            INSERT INTO chat_messages
            (session_id, sender_id, tg_message_id, content_type, preview, content_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, sender_id, tg_message_id, content_type, preview, content_json, _utcnow()),
        )
        await db.commit()
        return cursor.lastrowid or 0

    async def create_admin_token(self, admin_id: int, ttl_minutes: int = 15) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        db = await self.connect()
        await db.execute(
            "INSERT INTO admin_tokens (token_hash, admin_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token_hash, admin_id, expires_at.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds"), _utcnow()),
        )
        await db.commit()
        return token

    async def consume_admin_token(self, token: str) -> int | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT id, admin_id, expires_at, used_at FROM admin_tokens
            WHERE token_hash = ?
            """,
            (token_hash,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        if row["used_at"] is not None:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc).replace(tzinfo=None):
            return None
        await db.execute(
            "UPDATE admin_tokens SET used_at = ? WHERE id = ?",
            (_utcnow(), row["id"]),
        )
        await db.commit()
        return int(row["admin_id"])

    async def create_web_session(self, admin_id: int, ttl_hours: int = 24) -> str:
        session = secrets.token_urlsafe(32)
        session_hash = hashlib.sha256(session.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        db = await self.connect()
        await db.execute(
            "INSERT INTO admin_web_sessions (session_hash, admin_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (
                session_hash,
                admin_id,
                expires_at.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds"),
                _utcnow(),
            ),
        )
        await db.commit()
        return session

    async def get_admin_by_session(self, session: str) -> int | None:
        session_hash = hashlib.sha256(session.encode()).hexdigest()
        db = await self.connect()
        cursor = await db.execute(
            "SELECT admin_id, expires_at FROM admin_web_sessions WHERE session_hash = ?",
            (session_hash,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc).replace(tzinfo=None):
            return None
        return int(row["admin_id"])

    async def import_users(self, user_ids: list[int]) -> int:
        inserted = 0
        db = await self.connect()
        for user_id in user_ids:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,),
            )
            inserted += cursor.rowcount
        await db.commit()
        return inserted

    async def import_blocks(self, user_ids: list[int]) -> int:
        inserted = 0
        db = await self.connect()
        for user_id in user_ids:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO blocks (user_id) VALUES (?)",
                (user_id,),
            )
            inserted += cursor.rowcount
        await db.commit()
        return inserted

    # --- Admin web queries ---

    async def dashboard_stats(self) -> dict[str, int]:
        db = await self.connect()
        stats: dict[str, int] = {}
        queries = {
            "posts_today": "SELECT COUNT(*) AS c FROM proposal_posts WHERE date(created_at) = date('now')",
            "posts_week": "SELECT COUNT(*) AS c FROM proposal_posts WHERE created_at >= datetime('now', '-7 days')",
            "open_support": "SELECT COUNT(*) AS c FROM support_threads WHERE status = 'open'",
            "active_chats": "SELECT COUNT(*) AS c FROM chat_sessions WHERE status = 'active'",
            "total_users": "SELECT COUNT(*) AS c FROM users",
            "blocked_users": "SELECT COUNT(*) AS c FROM blocks",
        }
        for key, query in queries.items():
            cursor = await db.execute(query)
            row = await cursor.fetchone()
            stats[key] = int(row["c"]) if row else 0
        return stats

    async def activity_by_day(self, days: int = 7) -> list[dict[str, Any]]:
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM proposal_posts
            WHERE created_at >= datetime('now', ?)
            GROUP BY date(created_at)
            ORDER BY day
            """,
            (f"-{days} days",),
        )
        rows = await cursor.fetchall()
        return [{"day": row["day"], "count": row["count"]} for row in rows]

    async def list_posts(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT p.*, u.username, u.full_name
            FROM proposal_posts p
            LEFT JOIN users u ON u.user_id = p.user_id
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def list_support_threads(self, status: str | None = None) -> list[dict[str, Any]]:
        db = await self.connect()
        if status:
            cursor = await db.execute(
                """
                SELECT t.*, u.username, u.full_name
                FROM support_threads t
                LEFT JOIN users u ON u.user_id = t.user_id
                WHERE t.status = ?
                ORDER BY t.opened_at DESC
                """,
                (status,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT t.*, u.username, u.full_name
                FROM support_threads t
                LEFT JOIN users u ON u.user_id = t.user_id
                ORDER BY t.opened_at DESC
                """
            )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_support_messages(self, thread_id: int) -> list[dict[str, Any]]:
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT m.*, u.username, u.full_name
            FROM support_messages m
            LEFT JOIN users u ON u.user_id = m.user_id
            WHERE m.thread_id = ?
            ORDER BY m.created_at ASC
            """,
            (thread_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def list_chat_sessions(self, status: str | None = None) -> list[dict[str, Any]]:
        db = await self.connect()
        query = """
            SELECT s.*,
                   ua.username AS user_a_username, ua.full_name AS user_a_name,
                   ub.username AS user_b_username, ub.full_name AS user_b_name
            FROM chat_sessions s
            LEFT JOIN users ua ON ua.user_id = s.user_a
            LEFT JOIN users ub ON ub.user_id = s.user_b
        """
        if status:
            query += " WHERE s.status = ? ORDER BY s.started_at DESC"
            cursor = await db.execute(query, (status,))
        else:
            query += " ORDER BY s.started_at DESC"
            cursor = await db.execute(query)
        return [dict(row) for row in await cursor.fetchall()]

    async def get_chat_messages(self, session_id: int) -> list[dict[str, Any]]:
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT m.*, u.username, u.full_name
            FROM chat_messages m
            LEFT JOIN users u ON u.user_id = m.sender_id
            WHERE m.session_id = ?
            ORDER BY m.created_at ASC
            """,
            (session_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def search_users(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        db = await self.connect()
        like = f"%{query}%"
        if query.isdigit():
            cursor = await db.execute(
                """
                SELECT u.*, CASE WHEN b.user_id IS NOT NULL THEN 1 ELSE 0 END AS is_blocked
                FROM users u
                LEFT JOIN blocks b ON b.user_id = u.user_id
                WHERE u.user_id = ? OR u.username LIKE ? OR u.full_name LIKE ?
                ORDER BY u.first_seen_at DESC
                LIMIT ?
                """,
                (int(query), like, like, limit),
            )
        else:
            cursor = await db.execute(
                """
                SELECT u.*, CASE WHEN b.user_id IS NOT NULL THEN 1 ELSE 0 END AS is_blocked
                FROM users u
                LEFT JOIN blocks b ON b.user_id = u.user_id
                WHERE u.username LIKE ? OR u.full_name LIKE ?
                ORDER BY u.first_seen_at DESC
                LIMIT ?
                """,
                (like, like, limit),
            )
        return [dict(row) for row in await cursor.fetchall()]

    async def list_blocks(self) -> list[dict[str, Any]]:
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT b.*, u.username, u.full_name
            FROM blocks b
            LEFT JOIN users u ON u.user_id = b.user_id
            ORDER BY b.blocked_at DESC
            """
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def get_user_card(self, user_id: int) -> dict[str, Any] | None:
        db = await self.connect()
        cursor = await db.execute(
            """
            SELECT u.*, CASE WHEN b.user_id IS NOT NULL THEN 1 ELSE 0 END AS is_blocked
            FROM users u
            LEFT JOIN blocks b ON b.user_id = u.user_id
            WHERE u.user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        card = dict(row)
        cursor = await db.execute(
            "SELECT COUNT(*) AS c FROM proposal_posts WHERE user_id = ?",
            (user_id,),
        )
        card["posts_count"] = (await cursor.fetchone())["c"]
        cursor = await db.execute(
            "SELECT COUNT(*) AS c FROM support_threads WHERE user_id = ?",
            (user_id,),
        )
        card["support_count"] = (await cursor.fetchone())["c"]
        cursor = await db.execute(
            "SELECT COUNT(*) AS c FROM chat_sessions WHERE user_a = ? OR user_b = ?",
            (user_id, user_id),
        )
        card["chat_count"] = (await cursor.fetchone())["c"]
        return card
