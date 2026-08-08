import asyncio
import logging
import os
import re
from io import BytesIO

from aiogram.types import Message
from core.config import settings
from core.database import async_session_maker
from core.models import Image, TextRecord, YouTubeLink
from core.settings_repo import get_setting
from sqlalchemy import select

logger = logging.getLogger("bot.services")

SHORT_THRESHOLD = 100
ALBUM_FLUSH_DELAY = 1.5

_pending_albums: dict[str, list[Message]] = {}
_pending_tasks: dict[str, asyncio.Task] = {}

YOUTUBE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w-]{11}"
)


def find_youtube_urls(text: str) -> list[str]:
    return list({m.group(0) for m in YOUTUBE_RE.finditer(text or "")})


def _extract_media(message: Message) -> list[tuple[str, object, str]]:
    """Возвращает список (kind, file_object, extension) для сообщения."""
    items: list[tuple[str, object, str]] = []
    if message.photo:
        items.append(("photo", message.photo[-1], ".jpg"))
    elif message.video:
        items.append(("video", message.video, ".mp4"))
    elif message.document:
        ext = ".bin"
        if message.document.file_name:
            e = os.path.splitext(message.document.file_name)[1]
            if e:
                ext = e
        items.append(("document", message.document, ext))
    return items


async def buffer_media_group(message: Message) -> None:
    """Собирает альбом (media_group) и обрабатывает его целиком после паузы 1.5с."""
    gid = message.media_group_id
    if not gid:
        await process_data([message])
        return
    _pending_albums.setdefault(gid, []).append(message)
    task = _pending_tasks.get(gid)
    if task is None or task.done():
        _pending_tasks[gid] = asyncio.create_task(_flush_album(gid))


async def _flush_album(gid: str) -> None:
    await asyncio.sleep(ALBUM_FLUSH_DELAY)
    messages = _pending_albums.pop(gid, [])
    _pending_tasks.pop(gid, None)
    if messages:
        await process_data(messages)


async def process_data(messages: list[Message]) -> None:
    """Точка входа обработки входящих данных (альбом или одиночное сообщение)."""
    try:
        await save_text(messages)
    except Exception:
        logger.exception("Failed to process message(s)")


# backward-compatible aliases
process_and_save = process_data


async def save_text(messages: list[Message]) -> None:
    """Запись в БД + сохранение медиа в shared volume."""
    bot = messages[0].bot
    base_message_id = messages[0].message_id
    image_path = await get_setting("image_path", "attachments")

    texts = []
    for m in messages:
        t = m.caption or m.text
        if t and t.strip():
            texts.append(t.strip())
    original_text = "\n".join(texts).strip()

    image_links: list[str] = []
    image_rows: list[tuple[str, str]] = []
    index = 0
    for m in messages:
        for _kind, file_obj, ext in _extract_media(m):
            index += 1
            file_name = f"{base_message_id}_{index}{ext}"
            try:
                buf = BytesIO()
                await bot.download(file_obj, destination=buf)
                dest = os.path.join(settings.media_dir, file_name)
                os.makedirs(settings.media_dir, exist_ok=True)
                with open(dest, "wb") as fh:
                    fh.write(buf.getvalue())
            except Exception:
                logger.exception(
                    "Failed to download/save media message_id=%s file=%s",
                    base_message_id,
                    file_name,
                )
                continue
            image_links.append(f"![[{image_path}/{file_name}]]\n")
            image_rows.append((file_name, file_name))

    content = "".join(image_links)
    if original_text:
        content += original_text

    # short по «чистому» тексту без вики-ссылок на картинки
    short = len(original_text) < SHORT_THRESHOLD

    # не сохраняем пустые апдейты без текста и медиа
    if not content.strip():
        logger.info("Skip empty message_id=%s", base_message_id)
        return

    async with async_session_maker() as session:
        rec = TextRecord(message_id=base_message_id, content=content, short=short)
        session.add(rec)
        await session.flush()
        for file_name, file_path in image_rows:
            session.add(Image(text_id=rec.id, file_name=file_name, file_path=file_path))
        await session.commit()

    logger.info("Saved message_id=%s images=%s short=%s", base_message_id, len(image_rows), short)

    if original_text:
        await handle_youtube(original_text)


async def handle_youtube(text: str) -> None:
    urls = find_youtube_urls(text)
    if not urls:
        return
    async with async_session_maker() as session:
        for url in urls:
            exists = await session.execute(select(YouTubeLink).where(YouTubeLink.url == url))
            if exists.scalar_one_or_none() is not None:
                continue
            try:
                meta = await fetch_youtube_meta(url)
            except Exception:
                logger.exception("yt_dlp failed for %s", url)
                meta = {"title": url, "duration": None}
            session.add(
                YouTubeLink(
                    url=url,
                    title=meta.get("title") or url,
                    duration=meta.get("duration"),
                )
            )
        await session.commit()


async def fetch_youtube_meta(url: str) -> dict:
    import yt_dlp

    def _run() -> dict:
        opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"title": info.get("title"), "duration": info.get("duration")}

    return await asyncio.to_thread(_run)
