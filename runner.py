import asyncio
import logging
import os
import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import uvicorn

from api.main import app
from core.config import settings
from core.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("runner")


async def wait_for_db(max_retries=30, delay=5):
    """Ожидание готовности базы данных."""
    for attempt in range(max_retries):
        try:
            # Попытка подключения к базе данных
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info(f"Database is ready after {attempt + 1} attempts.")
            return True
        except OperationalError as e:
            logger.warning(f"Attempt {attempt + 1} to connect to DB failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("Failed to connect to DB after maximum retries.")
                return False
    return False


async def main() -> None:
    logger.info(">>> RUNNER STARTING <<<")
    os.makedirs(settings.media_dir, exist_ok=True)

    port = settings.port
    logger.info(">>> LISTENING ON PORT %s <<<", port)

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    tasks = [asyncio.create_task(server.serve())]

    if settings.bot_token:
        from bot.main import start_polling
        tasks.append(asyncio.create_task(start_polling()))
        logger.info(">>> BOT task scheduled <<<")
    else:
        logger.warning("BOT_TOKEN is empty; running API only")

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")