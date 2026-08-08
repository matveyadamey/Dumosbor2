import asyncio
import logging
import os

import uvicorn

from api.main import app
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("runner")


async def main() -> None:
    os.makedirs(settings.media_dir, exist_ok=True)
    port = settings.port

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    tasks = [asyncio.create_task(server.serve())]

    if settings.bot_token:
        from bot.main import start_polling

        tasks.append(asyncio.create_task(start_polling()))
        logger.info("Bot + API started")
    else:
        logger.warning("BOT_TOKEN is empty; running API only")

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")