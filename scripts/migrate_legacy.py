#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from common.config import get_settings
from common.db.repository import Database


def load_json_list(path: Path) -> list[int]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")
    return [int(item) for item in data]


def load_blocked(path: Path) -> list[int]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, list):
        return [int(item) for item in data]
    if isinstance(data, dict) and "blocked" in data:
        return [int(item) for item in data["blocked"]]
    raise ValueError(f"{path} must be a list or {{\"blocked\": [...]}}")


async def run(users_path: Path, blocked_path: Path) -> None:
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()

    users = load_json_list(users_path)
    blocked = load_blocked(blocked_path)

    users_inserted = await db.import_users(users)
    blocks_inserted = await db.import_blocks(blocked)

    print(f"Users in file: {len(users)}")
    print(f"Users imported: {users_inserted}")
    print(f"Blocked in file: {len(blocked)}")
    print(f"Blocks imported: {blocks_inserted}")
    print(f"Database: {settings.database_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy users.json and blocked list to SQLite")
    parser.add_argument("--users", type=Path, default=Path("users.json"), help="Path to users.json")
    parser.add_argument("--blocked", type=Path, default=Path("blocked.json"), help="Path to blocked.json")
    args = parser.parse_args()
    asyncio.run(run(args.users, args.blocked))


if __name__ == "__main__":
    main()
