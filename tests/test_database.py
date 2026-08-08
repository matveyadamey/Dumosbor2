from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_get_db_yields_session(monkeypatch) -> None:
    from core import database

    session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr(database, "async_session_maker", MagicMock(return_value=cm))

    agen = database.get_db()
    got = await agen.__anext__()
    assert got is session
    await agen.aclose()
