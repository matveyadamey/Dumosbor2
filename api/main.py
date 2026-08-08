import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from api.routes import router as api_router
from core.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("api")

app = FastAPI(title="TG -> Obsidian API", version="1.0.0")
app.include_router(api_router)


@app.get("/health")
async def health():
    """Healthcheck без авторизации."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        logger.exception("Healthcheck failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "disconnected"},
        )