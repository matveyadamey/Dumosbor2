import logging
import os
import uuid

from core.config import settings
from core.database import async_session_maker, engine
from core.models import TextRecord, YouTubeLink
from core.settings_repo import get_setting
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from api.auth import require_token

logger = logging.getLogger("api.routes")

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_token)])


class TextsAckRequest(BaseModel):
    """ACK по message_id — как в ТЗ."""

    message_ids: list[int] = Field(default_factory=list)


class YoutubeAckRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


# ─────────────────────────── TEXTS ───────────────────────────
@router.get("/texts")
async def get_texts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Несинхронизированные записи (synced=false) с пагинацией."""
    async with async_session_maker() as session:
        q = (
            select(TextRecord)
            .where(TextRecord.synced == False)  # noqa: E712
            .order_by(TextRecord.created_at)
            .limit(limit)
            .offset(offset)
        )
        res = await session.execute(q)
        records = res.scalars().all()
        return [
            {
                "id": str(r.id),
                "message_id": r.message_id,
                "content": r.content,
                "short": r.short,
                "created_at": r.created_at.isoformat(),
                "images": [img.file_name for img in r.images],
            }
            for r in records
        ]


@router.post("/texts/ack")
async def ack_texts(req: TextsAckRequest):
    """Плагин подтверждает получение — synced=true по message_id."""
    if not req.message_ids:
        return {"acked": 0}

    async with async_session_maker() as session:
        res = await session.execute(
            select(TextRecord).where(TextRecord.message_id.in_(req.message_ids))
        )
        records = res.scalars().all()
        for r in records:
            r.synced = True
        await session.commit()
        return {"acked": len(records)}


# ─────────────────────────── MEDIA ───────────────────────────
@router.get("/media/{file_name}")
async def get_media(file_name: str):
    """Стриминг файла из shared volume (MEDIA_DIR)."""
    safe_name = os.path.basename(file_name)
    path = os.path.join(settings.media_dir, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        return FileResponse(path)
    except Exception:
        logger.exception("Failed to stream media file=%s", safe_name)
        raise HTTPException(status_code=500, detail="Failed to read media file") from None


# ─────────────────────────── YOUTUBE ───────────────────────────
@router.get("/youtube")
async def get_youtube():
    async with async_session_maker() as session:
        res = await session.execute(
            select(YouTubeLink)
            .where(YouTubeLink.synced == False)  # noqa: E712
            .order_by(YouTubeLink.created_at)
        )
        links = res.scalars().all()
        return [
            {
                "id": str(link.id),
                "url": link.url,
                "title": link.title,
                "duration": link.duration,
                "created_at": link.created_at.isoformat(),
            }
            for link in links
        ]


@router.post("/youtube/ack")
async def ack_youtube(req: YoutubeAckRequest):
    if not req.ids:
        return {"acked": 0}
    try:
        uuid_ids = [uuid.UUID(i) for i in req.ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID in ids") from None

    async with async_session_maker() as session:
        res = await session.execute(select(YouTubeLink).where(YouTubeLink.id.in_(uuid_ids)))
        links = res.scalars().all()
        for link in links:
            link.synced = True
        await session.commit()
        return {"acked": len(links)}


# ─────────────────────────── CLEANUP ───────────────────────────
def _clear_media_dir() -> int:
    """Удаляет файлы из shared volume. Возвращает число удалённых."""
    removed = 0
    media_dir = settings.media_dir
    if not os.path.isdir(media_dir):
        return 0
    for name in os.listdir(media_dir):
        path = os.path.join(media_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            os.remove(path)
            removed += 1
        except OSError:
            logger.exception("Failed to delete media file=%s", path)
    return removed


@router.delete("/cleanup")
async def cleanup():
    """Удаляет сообщения из ТГ (по возможности), TRUNCATE таблиц, чистит media."""
    admin_chat_id = await get_setting("admin_chat_id")
    deleted_in_tg = 0
    failed_in_tg = 0

    if admin_chat_id and settings.bot_token:
        from aiogram import Bot

        bot = Bot(token=settings.bot_token)
        try:
            async with async_session_maker() as session:
                res = await session.execute(select(TextRecord.message_id))
                message_ids = [row[0] for row in res.all()]

            for mid in message_ids:
                try:
                    await bot.delete_message(chat_id=int(admin_chat_id), message_id=mid)
                    deleted_in_tg += 1
                except Exception:
                    # старше 48ч или уже удалено — не критично
                    failed_in_tg += 1
                    logger.debug("TG delete_message failed for message_id=%s", mid, exc_info=True)
        finally:
            await bot.session.close()
    else:
        logger.warning("cleanup: нет admin_chat_id или bot_token — пропускаем удаление из ТГ")

    media_removed = _clear_media_dir()

    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE TABLE images, texts, youtube_links RESTART IDENTITY CASCADE")
        )

    return {
        "deleted_in_tg": deleted_in_tg,
        "failed_in_tg": failed_in_tg,
        "media_removed": media_removed,
        "db_cleared": True,
    }
