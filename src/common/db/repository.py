from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blocks (
    user_id INTEGER PRIMARY KEY,
    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    async def connect(self) -> aiosqlite.Connection:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(self.database_path)
        connection.row_factory = aiosqlite.Row
        await connection.executescript(SCHEMA)
        await connection.commit()
        return connection

    async def init(self) -> None:
        async with await self.connect() as connection:
            logger.info("Database initialized at %s", self.database_path)

    async def register_user(self, user_id: int, username: str | None) -> bool:
        async with await self.connect() as connection:
            cursor = await connection.execute(
                "SELECT user_id FROM users WHERE user_id = ?",
                (user_id,),
            )
            exists = await cursor.fetchone() is not None
            if exists:
                return False

            await connection.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username),
            )
            await connection.commit()
            return True

    async def is_blocked(self, user_id: int) -> bool:
        async with await self.connect() as connection:
            cursor = await connection.execute(
                "SELECT user_id FROM blocks WHERE user_id = ?",
                (user_id,),
            )
            return await cursor.fetchone() is not None

    async def toggle_block(self, user_id: int) -> bool:
        async with await self.connect() as connection:
            cursor = await connection.execute(
                "SELECT user_id FROM blocks WHERE user_id = ?",
                (user_id,),
            )
            blocked = await cursor.fetchone() is not None
            if blocked:
                await connection.execute("DELETE FROM blocks WHERE user_id = ?", (user_id,))
                await connection.commit()
                return False

            await connection.execute("INSERT INTO blocks (user_id) VALUES (?)", (user_id,))
            await connection.commit()
            return True

    async def import_users(self, user_ids: list[int]) -> int:
        inserted = 0
        async with await self.connect() as connection:
            for user_id in user_ids:
                cursor = await connection.execute(
                    "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                    (user_id,),
                )
                inserted += cursor.rowcount
            await connection.commit()
        return inserted

    async def import_blocks(self, user_ids: list[int]) -> int:
        inserted = 0
        async with await self.connect() as connection:
            for user_id in user_ids:
                cursor = await connection.execute(
                    "INSERT OR IGNORE INTO blocks (user_id) VALUES (?)",
                    (user_id,),
                )
                inserted += cursor.rowcount
            await connection.commit()
        return inserted
