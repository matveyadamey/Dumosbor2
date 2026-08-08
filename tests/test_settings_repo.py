from unittest.mock import AsyncMock, MagicMock

import pytest
from core.models import Setting
from core.settings_repo import get_setting, set_setting


@pytest.mark.asyncio
async def test_get_setting_default(monkeypatch) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("core.settings_repo.async_session_maker", MagicMock(return_value=cm))

    assert await get_setting("missing", "fallback") == "fallback"


@pytest.mark.asyncio
async def test_get_setting_value(monkeypatch) -> None:
    row = Setting(key="k", value="v")
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("core.settings_repo.async_session_maker", MagicMock(return_value=cm))

    assert await get_setting("k") == "v"


@pytest.mark.asyncio
async def test_set_setting_insert(monkeypatch) -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.commit = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("core.settings_repo.async_session_maker", MagicMock(return_value=cm))

    await set_setting("k", "v")
    session.add.assert_called_once()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_set_setting_update(monkeypatch) -> None:
    row = Setting(key="k", value="old")
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.add = MagicMock()
    session.commit = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("core.settings_repo.async_session_maker", MagicMock(return_value=cm))

    await set_setting("k", "new")
    assert row.value == "new"
    session.add.assert_not_called()
    session.commit.assert_awaited()
