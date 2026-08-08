from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_runner_api_mode(monkeypatch) -> None:
    import runner

    serve = AsyncMock()
    bot = AsyncMock()
    monkeypatch.setenv("APP_MODE", "api")
    monkeypatch.setattr(runner, "run_api", serve)
    monkeypatch.setattr(runner, "run_bot", bot)
    monkeypatch.setattr(
        runner,
        "settings",
        MagicMock(media_dir="/tmp/x", bot_token="t", port=8000),
    )
    with patch("os.makedirs"):
        await runner.main()
    serve.assert_awaited()
    bot.assert_not_awaited()


@pytest.mark.asyncio
async def test_runner_bot_mode(monkeypatch) -> None:
    import runner

    serve = AsyncMock()
    bot = AsyncMock()
    monkeypatch.setenv("APP_MODE", "bot")
    monkeypatch.setattr(runner, "run_api", serve)
    monkeypatch.setattr(runner, "run_bot", bot)
    monkeypatch.setattr(
        runner,
        "settings",
        MagicMock(media_dir="/tmp/x", bot_token="t", port=8000),
    )
    with patch("os.makedirs"):
        await runner.main()
    bot.assert_awaited()
    serve.assert_not_awaited()


@pytest.mark.asyncio
async def test_runner_all_mode_schedules_both(monkeypatch) -> None:
    import runner

    serve = AsyncMock()
    bot = AsyncMock()
    monkeypatch.setenv("APP_MODE", "all")
    monkeypatch.setattr(runner, "run_api", serve)
    monkeypatch.setattr(runner, "run_bot", bot)
    monkeypatch.setattr(
        runner,
        "settings",
        MagicMock(media_dir="/tmp/x", bot_token="token", port=8000),
    )
    with patch("os.makedirs"):
        await runner.main()
    serve.assert_awaited()
    bot.assert_awaited()
