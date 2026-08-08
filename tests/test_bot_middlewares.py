from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message
from bot.middlewares import AdminFilterMiddleware, AlbumBufferMiddleware


@pytest.mark.asyncio
async def test_admin_allows_start_before_registration(monkeypatch) -> None:
    async def fake_get(key, default=None):
        return None

    monkeypatch.setattr("bot.middlewares.get_setting", fake_get)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=1)
    event.text = "/start"

    handler = AsyncMock(return_value="ok")
    mw = AdminFilterMiddleware()
    assert await mw(handler, event, {}) == "ok"
    handler.assert_awaited()


@pytest.mark.asyncio
async def test_admin_blocks_non_start_before_registration(monkeypatch) -> None:
    async def fake_get(key, default=None):
        return None

    monkeypatch.setattr("bot.middlewares.get_setting", fake_get)

    event = MagicMock(spec=Message)
    event.from_user = MagicMock(id=1)
    event.text = "hello"

    handler = AsyncMock(return_value="ok")
    mw = AdminFilterMiddleware()
    assert await mw(handler, event, {}) is None
    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_allows_matching_user(monkeypatch) -> None:
    async def fake_get(key, default=None):
        return "99"

    monkeypatch.setattr("bot.middlewares.get_setting", fake_get)

    event = MagicMock()
    event.from_user = MagicMock(id=99)

    handler = AsyncMock(return_value="ok")
    mw = AdminFilterMiddleware()
    assert await mw(handler, event, {}) == "ok"


@pytest.mark.asyncio
async def test_admin_blocks_other_user(monkeypatch) -> None:
    async def fake_get(key, default=None):
        return "99"

    monkeypatch.setattr("bot.middlewares.get_setting", fake_get)

    event = MagicMock()
    event.from_user = MagicMock(id=1)

    handler = AsyncMock(return_value="ok")
    mw = AdminFilterMiddleware()
    assert await mw(handler, event, {}) is None


@pytest.mark.asyncio
async def test_album_middleware_buffers(monkeypatch) -> None:
    called = AsyncMock()
    monkeypatch.setattr("bot.middlewares.buffer_media_group", called)

    event = MagicMock(spec=Message)
    event.media_group_id = "g1"

    handler = AsyncMock()
    mw = AlbumBufferMiddleware()
    assert await mw(handler, event, {}) is None
    called.assert_awaited_once_with(event)
    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_album_middleware_passes_through(monkeypatch) -> None:
    event = MagicMock(spec=Message)
    event.media_group_id = None

    handler = AsyncMock(return_value="next")
    mw = AlbumBufferMiddleware()
    assert await mw(handler, event, {}) == "next"
    handler.assert_awaited()
