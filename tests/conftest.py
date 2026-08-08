"""Общие фикстуры. DATABASE_URL задаём до импорта приложения."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",
)
os.environ.setdefault("BOT_TOKEN", "")
os.environ.setdefault("MEDIA_DIR", str(Path("/tmp/dumosbor-media-test")))


@pytest.fixture(autouse=True)
def _media_dir(tmp_path, monkeypatch):
    media = tmp_path / "media"
    media.mkdir()
    monkeypatch.setenv("MEDIA_DIR", str(media))
    from core.config import get_settings

    get_settings.cache_clear()
    fresh = get_settings()
    monkeypatch.setattr("core.config.settings", fresh)
    monkeypatch.setattr("core.database.settings", fresh)
    try:
        import api.routes as routes

        monkeypatch.setattr(routes, "settings", fresh)
    except Exception:
        pass
    try:
        import bot.services as services

        monkeypatch.setattr(services, "settings", fresh)
    except Exception:
        pass
    return media


@pytest.fixture
def bearer_token() -> str:
    return "test-bearer-token-abc"


@pytest.fixture
def mock_get_setting(monkeypatch, bearer_token):
    async def _get(key: str, default=None):
        data = {
            "bearer_token": bearer_token,
            "admin_chat_id": "12345",
            "image_path": "attachments",
        }
        return data.get(key, default)

    monkeypatch.setattr("api.auth.get_setting", _get)
    monkeypatch.setattr("api.routes.get_setting", _get)
    monkeypatch.setattr("core.settings_repo.get_setting", _get)
    return _get


@pytest.fixture
def mock_session_factory(monkeypatch):
    """Фабрика async-сессий: session.execute / commit / get мокаются в тестах."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()

    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None

    factory = MagicMock(return_value=cm)
    monkeypatch.setattr("api.routes.async_session_maker", factory)
    monkeypatch.setattr("core.settings_repo.async_session_maker", factory)
    monkeypatch.setattr("bot.services.async_session_maker", factory)
    return session, factory
