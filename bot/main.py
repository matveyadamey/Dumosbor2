import logging

from aiogram import Bot, Dispatcher

from bot.handlers import router
from bot.middlewares import AdminFilterMiddleware, AlbumBufferMiddleware
from core.config import settings

logger = logging.getLogger("bot")


async def _run_polling() -> None:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.message.outer_middleware(AdminFilterMiddleware())
    dp.callback_query.outer_middleware(AdminFilterMiddleware())
    dp.message.middleware(AlbumBufferMiddleware())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Polling started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


async def start_polling() -> None:
    import asyncio

    while True:
        try:
            await _run_polling()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Bot crashed; restarting in 5s")
            await asyncio.sleep(5)
