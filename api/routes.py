import logging
import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete, select

from api.auth import require_token
from core.config import settings
from core.database import async_session_maker
from core.models import Image, TextRecord, YouTubeLink
from core.settings_repo import get_setting

logger = logging.getLogger("api.routes")

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_token)])


class AckRequest(BaseModel):
    ids: List[str]  # uuid записей, которые плагин успешно сохранил


# ─────────────────────────── TEXTS ───────────────────────────
@router.get("/texts")
async def get_texts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Возвращает несинхронизированные записи (synced=false)."""
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
async def ack_texts(req: AckRequest):
    """Плагин подтверждает получение — ставим synced=true."""
    if not req.ids:
        return {"acked": 0}
    try:
        uuid_ids = [uuid.UUID(i) for i in req.ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID in ids")

    async with async_session_maker() as session:
        res = await session.execute(
            select(TextRecord).where(TextRecord.id.in_(uuid_ids))
        )
        records = res.scalars().all()
        for r in records:
            r.synced = True
        await session.commit()
        return {"acked": len(records)}


# ─────────────────────────── MEDIA ───────────────────────────
@router.get("/media/{file_name}")
async def get_media(file_name: str):
    """Стриминг файла картинки из MEDIA_DIR."""
    safe_name = os.path.basename(file_name)  # защита от path traversal
    path = os.path.join(settings.media_dir, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


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
                "id": str(l.id),
                "url": l.url,
                "title": l.title,
                "duration": l.duration,
                "created_at": l.created_at.isoformat(),
            }
            for l in links
        ]


@router.post("/youtube/ack")
async def ack_youtube(req: AckRequest):
    if not req.ids:
        return {"acked": 0}
    try:
        uuid_ids = [uuid.UUID(i) for i in req.ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID in ids")

    async with async_session_maker() as session:
        res = await session.execute(
            select(YouTubeLink).where(YouTubeLink.id.in_(uuid_ids))
        )
        links = res.scalars().all()
        for l in links:
            l.synced = True
        await session.commit()
        return {"acked": len(links)}


# ─────────────────────────── CLEANUP ───────────────────────────
@router.delete("/cleanup")
async def cleanup():
    """Удаляет сообщения из ТГ (по возможности) и очищает БД."""
    admin_chat_id = await get_setting("admin_chat_id")
    deleted_in_tg = 0
    failed_in_tg = 0

    # 1) Пробуем удалить сообщения из Telegram
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
        finally:
            await bot.session.close()
    else:
        logger.warning("cleanup: нет admin_chat_id или bot_token — пропускаем удаление из ТГ")

    # 2) Очищаем БД
    async with async_session_maker() as session:
        await session.execute(delete(Image))
        await session.execute(delete(TextRecord))
        await session.execute(delete(YouTubeLink))
        await session.commit()

    return {
        "deleted_in_tg": deleted_in_tg,
        "failed_in_tg": failed_in_tg,
        "db_cleared": True,
    }