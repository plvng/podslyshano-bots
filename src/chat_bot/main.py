from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

import redis.asyncio as redis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.config import get_chat_message, get_settings
from common.middleware.subscription import SubscriptionMiddleware
from chat_bot.handlers.admin import router as admin_router
from chat_bot.handlers.find import router as find_router
from chat_bot.handlers.relay import router as relay_router
from chat_bot.handlers.start import router as start_router
from chat_bot.handlers.stop import router as stop_router
from chat_bot.matching import ChatMatching
from chat_bot.message_map import MessageMap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def graceful_shutdown(bot: Bot, matching: ChatMatching, message_map: MessageMap) -> None:
    waiting, paired = await matching.get_all_active_users()
    stop_text = get_chat_message("stop_message")
    stop_find_text = get_chat_message("stop_find_message")

    for user_id in waiting:
        try:
            await bot.send_message(user_id, stop_find_text)
        except Exception as exc:
            logger.debug("Could not notify waiting user %s: %s", user_id, exc)

    notified: set[int] = set()
    for user_id in paired:
        if user_id in notified:
            continue
        partner_id = await matching.get_partner(user_id)
        notified.add(user_id)
        if partner_id:
            notified.add(partner_id)
        try:
            await bot.send_message(user_id, stop_text)
        except Exception as exc:
            logger.debug("Could not notify paired user %s: %s", user_id, exc)

    await message_map.clear_all()
    await matching.clear_all()
    logger.info("Graceful shutdown completed")


async def main() -> None:
    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    matching = ChatMatching(redis_client)
    message_map = MessageMap(redis_client)

    bot = Bot(token=settings.chat_bot_token, default=DefaultBotProperties())
    dispatcher = Dispatcher()
    dispatcher["matching"] = matching
    dispatcher["message_map"] = message_map
    dispatcher["redis_client"] = redis_client

    dispatcher.message.middleware(SubscriptionMiddleware(skip_commands=("/start",)))

    dispatcher.include_router(start_router)
    dispatcher.include_router(find_router)
    dispatcher.include_router(stop_router)
    dispatcher.include_router(admin_router)
    dispatcher.include_router(relay_router)

    shutdown_event = asyncio.Event()

    def _handle_signal(*_: object) -> None:
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    logger.info("Chat bot started")
    polling_task = asyncio.create_task(
        dispatcher.start_polling(
            bot,
            matching=matching,
            message_map=message_map,
            redis_client=redis_client,
        )
    )

    await shutdown_event.wait()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    await graceful_shutdown(bot, matching, message_map)
    await redis_client.aclose()
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
