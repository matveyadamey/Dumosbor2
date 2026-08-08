import asyncio
import logging
import os

import uvicorn

from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("runner")


async def run_api() -> None:
    from api.main import app

    port = settings.port
    logger.info(">>> API LISTENING ON PORT %s <<<", port)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot() -> None:
    from bot.main import start_polling

    if not settings.bot_token:
        logger.error("BOT_TOKEN is empty; cannot start bot")
        return
    logger.info(">>> BOT STARTING <<<")
    await start_polling()


async def main() -> None:
    logger.info(">>> RUNNER STARTING <<<")
    os.makedirs(settings.media_dir, exist_ok=True)

    # all (Railway) | api | bot (docker-compose)
    mode = (os.getenv("APP_MODE") or "all").strip().lower()
    logger.info("APP_MODE=%s", mode)

    if mode == "api":
        await run_api()
        return
    if mode == "bot":
        await run_bot()
        return

    tasks = [asyncio.create_task(run_api())]
    if settings.bot_token:
        tasks.append(asyncio.create_task(run_bot()))
        logger.info(">>> BOT task scheduled <<<")
    else:
        logger.warning("BOT_TOKEN is empty; running API only")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")
