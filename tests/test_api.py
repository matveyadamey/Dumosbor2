from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from api.auth import require_token
from api.main import app
from core.models import TextRecord
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_require_token_missing() -> None:
    with pytest.raises(HTTPException) as exc:
        await require_token(None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_token_invalid(monkeypatch) -> None:
    async def fake_get(key, default=None):
        return "expected"

    monkeypatch.setattr("api.auth.get_setting", fake_get)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")
    with pytest.raises(HTTPException) as exc:
        await require_token(creds)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_token_ok(monkeypatch) -> None:
    async def fake_get(key, default=None):
        return "expected"

    monkeypatch.setattr("api.auth.get_setting", fake_get)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expected")
    assert await require_token(creds) == "expected"


@pytest.mark.asyncio
async def test_live_and_health(monkeypatch) -> None:
    conn = AsyncMock()
    conn.execute = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = conn
    cm.__aexit__.return_value = None

    fake_engine = MagicMock()
    fake_engine.connect = MagicMock(return_value=cm)
    monkeypatch.setattr("api.main.engine", fake_engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live = await client.get("/live")
        assert live.status_code == 200
        assert live.json()["status"] == "ok"

        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_health_db_down(monkeypatch) -> None:
    cm = AsyncMock()
    cm.__aenter__.side_effect = RuntimeError("db down")
    fake_engine = MagicMock()
    fake_engine.connect = MagicMock(return_value=cm)
    monkeypatch.setattr("api.main.engine", fake_engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 503


@pytest.mark.asyncio
async def test_texts_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/texts")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_texts(monkeypatch, mock_get_setting, bearer_token) -> None:
    from datetime import datetime

    rec = TextRecord(
        id=uuid4(),
        message_id=10,
        content="hello",
        short=True,
        created_at=datetime.utcnow(),
        synced=False,
    )
    rec.images = []

    result = MagicMock()
    result.scalars.return_value.all.return_value = [rec]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("api.routes.async_session_maker", MagicMock(return_value=cm))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/texts",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["message_id"] == 10
    assert data[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_ack_texts_by_message_id(monkeypatch, mock_get_setting, bearer_token) -> None:
    rec = MagicMock()
    rec.synced = False
    result = MagicMock()
    result.scalars.return_value.all.return_value = [rec]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("api.routes.async_session_maker", MagicMock(return_value=cm))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/texts/ack",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={"message_ids": [1, 2]},
        )
    assert res.status_code == 200
    assert res.json()["acked"] == 1
    assert rec.synced is True


@pytest.mark.asyncio
async def test_ack_youtube(monkeypatch, mock_get_setting, bearer_token) -> None:
    link = MagicMock()
    link.synced = False
    result = MagicMock()
    result.scalars.return_value.all.return_value = [link]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("api.routes.async_session_maker", MagicMock(return_value=cm))

    uid = str(uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/youtube/ack",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={"ids": [uid]},
        )
    assert res.status_code == 200
    assert res.json()["acked"] == 1
    assert link.synced is True


@pytest.mark.asyncio
async def test_get_media(monkeypatch, mock_get_setting, bearer_token, tmp_path) -> None:
    media = tmp_path / "media"
    media.mkdir(exist_ok=True)
    f = media / "42_1.jpg"
    f.write_bytes(b"abc")

    class FakeSettings:
        media_dir = str(media)
        bot_token = ""
        database_url = "postgresql+asyncpg://t:t@l/db"
        port = 8000

    monkeypatch.setattr("api.routes.settings", FakeSettings())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get(
            "/api/v1/media/42_1.jpg",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        missing = await client.get(
            "/api/v1/media/nope.jpg",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        traversal = await client.get(
            "/api/v1/media/../secret.txt",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert ok.status_code == 200
    assert ok.content == b"abc"
    assert missing.status_code == 404
    assert traversal.status_code == 404


@pytest.mark.asyncio
async def test_cleanup_truncates(monkeypatch, mock_get_setting, bearer_token, tmp_path) -> None:
    media = tmp_path / "media"
    media.mkdir(exist_ok=True)
    (media / "x.jpg").write_bytes(b"1")

    class FakeSettings:
        media_dir = str(media)
        bot_token = ""
        database_url = "postgresql+asyncpg://t:t@l/db"
        port = 8000

    monkeypatch.setattr("api.routes.settings", FakeSettings())

    # no bot_token → skip TG deletes
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("api.routes.async_session_maker", MagicMock(return_value=cm))

    conn = AsyncMock()
    conn.execute = AsyncMock()
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = conn
    begin_cm.__aexit__.return_value = None
    fake_engine = MagicMock()
    fake_engine.begin = MagicMock(return_value=begin_cm)
    monkeypatch.setattr("api.routes.engine", fake_engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete(
            "/api/v1/cleanup",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["db_cleared"] is True
    assert body["media_removed"] == 1
    assert not list(media.iterdir())
    conn.execute.assert_awaited()


@pytest.mark.asyncio
async def test_ack_texts_empty(monkeypatch, mock_get_setting, bearer_token) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/texts/ack",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={"message_ids": []},
        )
    assert res.status_code == 200
    assert res.json()["acked"] == 0


@pytest.mark.asyncio
async def test_get_youtube(monkeypatch, mock_get_setting, bearer_token) -> None:
    from datetime import datetime

    from core.models import YouTubeLink

    link = YouTubeLink(
        id=uuid4(),
        url="https://youtu.be/abcdefghijk",
        title="T",
        duration=12,
        created_at=datetime.utcnow(),
        synced=False,
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [link]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    monkeypatch.setattr("api.routes.async_session_maker", MagicMock(return_value=cm))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/youtube",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["url"] == "https://youtu.be/abcdefghijk"


@pytest.mark.asyncio
async def test_ack_youtube_empty_and_invalid(monkeypatch, mock_get_setting, bearer_token) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        empty = await client.post(
            "/api/v1/youtube/ack",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={"ids": []},
        )
        bad = await client.post(
            "/api/v1/youtube/ack",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={"ids": ["not-a-uuid"]},
        )
    assert empty.status_code == 200
    assert empty.json()["acked"] == 0
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_clear_media_dir_missing(monkeypatch, tmp_path) -> None:
    from api.routes import _clear_media_dir

    class FakeSettings:
        media_dir = str(tmp_path / "missing-dir")
        bot_token = ""
        database_url = "postgresql+asyncpg://t:t@l/db"
        port = 8000

    monkeypatch.setattr("api.routes.settings", FakeSettings())
    assert _clear_media_dir() == 0


@pytest.mark.asyncio
async def test_get_media_stream_error(
    monkeypatch, mock_get_setting, bearer_token, tmp_path
) -> None:
    media = tmp_path / "media"
    media.mkdir(exist_ok=True)
    f = media / "broken.jpg"
    f.write_bytes(b"x")

    class FakeSettings:
        media_dir = str(media)
        bot_token = ""
        database_url = "postgresql+asyncpg://t:t@l/db"
        port = 8000

    monkeypatch.setattr("api.routes.settings", FakeSettings())

    def boom(*args, **kwargs):
        raise OSError("fail")

    monkeypatch.setattr("api.routes.FileResponse", boom)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/media/broken.jpg",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert res.status_code == 500
