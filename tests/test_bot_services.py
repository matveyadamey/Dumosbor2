import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.services import (
    SHORT_THRESHOLD,
    fetch_youtube_meta,
    find_youtube_urls,
    handle_youtube,
)


@pytest.mark.parametrize(
    ("text", "expected_count"),
    [
        ("", 0),
        ("no links here", 0),
        ("see https://youtu.be/abcdefghijk", 1),
        ("https://www.youtube.com/watch?v=abcdefghijk cool", 1),
        ("https://youtube.com/shorts/abcdefghijk", 1),
        (
            "https://youtu.be/abcdefghijk and https://youtu.be/abcdefghijk",
            1,  # dedup in set
        ),
        (
            "https://youtu.be/aaaaaaaaaaa https://youtu.be/bbbbbbbbbbb",
            2,
        ),
    ],
)
def test_find_youtube_urls(text: str, expected_count: int) -> None:
    assert len(find_youtube_urls(text)) == expected_count


def test_short_threshold_constant() -> None:
    assert SHORT_THRESHOLD == 100


@pytest.mark.asyncio
async def test_fetch_youtube_meta_uses_to_thread() -> None:
    fake_info = {"title": "Hello", "duration": 125}

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            assert download is False
            return fake_info

    with patch("yt_dlp.YoutubeDL", FakeYDL):
        meta = await fetch_youtube_meta("https://youtu.be/abcdefghijk")
    assert meta == {"title": "Hello", "duration": 125}


@pytest.mark.asyncio
async def test_handle_youtube_skips_existing(monkeypatch) -> None:
    session = AsyncMock()
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = object()
    session.execute = AsyncMock(return_value=existing)
    session.add = MagicMock()
    session.commit = AsyncMock()

    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("bot.services.async_session_maker", MagicMock(return_value=cm))

    await handle_youtube("https://youtu.be/abcdefghijk")
    session.add.assert_not_called()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_handle_youtube_inserts_new(monkeypatch) -> None:
    session = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=missing)
    session.add = MagicMock()
    session.commit = AsyncMock()

    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("bot.services.async_session_maker", MagicMock(return_value=cm))

    async def fake_meta(url: str) -> dict:
        return {"title": "T", "duration": 10}

    monkeypatch.setattr("bot.services.fetch_youtube_meta", fake_meta)
    await handle_youtube("watch https://youtu.be/abcdefghijk please")
    assert session.add.call_count == 1
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_save_text_writes_db_and_file(monkeypatch, tmp_path) -> None:
    from bot.services import save_text

    media = tmp_path / "media"
    media.mkdir(exist_ok=True)

    class FakeSettings:
        media_dir = str(media)
        bot_token = ""
        database_url = "postgresql+asyncpg://t:t@l/db"
        port = 8000

    monkeypatch.setattr("bot.services.settings", FakeSettings())

    async def fake_get_setting(key, default=None):
        return default or "attachments"

    monkeypatch.setattr("bot.services.get_setting", fake_get_setting)

    photo = MagicMock()
    message = MagicMock()
    message.message_id = 42
    message.caption = "hi"
    message.text = None
    message.photo = [photo]
    message.video = None
    message.document = None
    message.bot = MagicMock()

    async def fake_download(file, destination):
        destination.write(b"IMG")

    message.bot.download = fake_download

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("bot.services.async_session_maker", MagicMock(return_value=cm))
    monkeypatch.setattr("bot.services.handle_youtube", AsyncMock())

    # photo[-1] used in _extract_media
    message.photo = [MagicMock(), MagicMock()]

    await save_text([message])

    assert session.add.call_count >= 1
    session.commit.assert_awaited()
    files = list(media.iterdir())
    assert len(files) == 1
    assert files[0].name.startswith("42_1.")


@pytest.mark.asyncio
async def test_extract_media_video_and_document() -> None:
    from bot.services import _extract_media

    video_msg = MagicMock()
    video_msg.photo = None
    video_msg.video = MagicMock()
    video_msg.document = None
    assert _extract_media(video_msg)[0][0] == "video"
    assert _extract_media(video_msg)[0][2] == ".mp4"

    doc_msg = MagicMock()
    doc_msg.photo = None
    doc_msg.video = None
    doc = MagicMock()
    doc.file_name = "note.PDF"
    doc_msg.document = doc
    assert _extract_media(doc_msg)[0][2] == ".PDF"

    bare = MagicMock()
    bare.photo = None
    bare.video = None
    bare.document = MagicMock()
    bare.document.file_name = None
    assert _extract_media(bare)[0][2] == ".bin"


@pytest.mark.asyncio
async def test_process_data_swallows_errors(monkeypatch) -> None:
    from bot.services import process_data

    monkeypatch.setattr("bot.services.save_text", AsyncMock(side_effect=RuntimeError("boom")))
    await process_data([MagicMock()])


@pytest.mark.asyncio
async def test_buffer_media_group_without_gid(monkeypatch) -> None:
    from bot.services import buffer_media_group

    called = AsyncMock()
    monkeypatch.setattr("bot.services.process_data", called)
    msg = MagicMock()
    msg.media_group_id = None
    await buffer_media_group(msg)
    called.assert_awaited()


@pytest.mark.asyncio
async def test_buffer_media_group_with_gid(monkeypatch) -> None:
    import bot.services as services

    monkeypatch.setattr(services, "ALBUM_FLUSH_DELAY", 0.01)
    process = AsyncMock()
    monkeypatch.setattr(services, "process_data", process)
    services._pending_albums.clear()
    services._pending_tasks.clear()

    msg = MagicMock()
    msg.media_group_id = "g1"
    await services.buffer_media_group(msg)
    await asyncio.sleep(0.05)
    process.assert_awaited()
    assert "g1" not in services._pending_albums


@pytest.mark.asyncio
async def test_save_text_skips_empty(monkeypatch) -> None:
    from bot.services import save_text

    async def fake_get_setting(key, default=None):
        return default or "attachments"

    monkeypatch.setattr("bot.services.get_setting", fake_get_setting)

    message = MagicMock()
    message.message_id = 7
    message.caption = None
    message.text = None
    message.photo = None
    message.video = None
    message.document = None
    message.bot = MagicMock()

    session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    factory = MagicMock(return_value=cm)
    monkeypatch.setattr("bot.services.async_session_maker", factory)

    await save_text([message])
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_handle_youtube_meta_failure(monkeypatch) -> None:
    session = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=missing)
    session.add = MagicMock()
    session.commit = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("bot.services.async_session_maker", MagicMock(return_value=cm))

    async def boom(url: str):
        raise RuntimeError("yt fail")

    monkeypatch.setattr("bot.services.fetch_youtube_meta", boom)
    await handle_youtube("https://youtu.be/abcdefghijk")
    assert session.add.call_count == 1
    session.commit.assert_awaited()
