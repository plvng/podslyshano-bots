from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import redis.asyncio as redis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.config import get_settings
from common.db.repository import Database
from common.middleware.subscription import SubscriptionMiddleware
from proposal_bot.handlers.admin_actions import router as admin_actions_router
from proposal_bot.handlers.mode import router as mode_router
from proposal_bot.handlers.panel import router as panel_router
from proposal_bot.handlers.publish import router as publish_router
from proposal_bot.handlers.start import router as start_router
from proposal_bot.handlers.support import router as support_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    bot = Bot(
        token=settings.proposal_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.message.middleware(
        SubscriptionMiddleware(skip_commands=("/start", "/panel", "/stats", "/ban", "/unban"))
    )

    dispatcher.include_router(start_router)
    dispatcher.include_router(panel_router)
    dispatcher.include_router(admin_actions_router)
    dispatcher.include_router(mode_router)
    dispatcher.include_router(support_router)
    dispatcher.include_router(publish_router)

    logger.info("Proposal bot started")
    try:
        await dispatcher.start_polling(bot, db=db, redis_client=redis_client)
    finally:
        await redis_client.aclose()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
