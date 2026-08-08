from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_run_polling_sets_up_and_closes(monkeypatch) -> None:
    import bot.main as bot_main

    bot = MagicMock()
    bot.delete_webhook = AsyncMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()

    class FakeBot:
        def __init__(self, token):
            self.token = token
            self.session = bot.session
            self.delete_webhook = bot.delete_webhook

    dp = MagicMock()
    dp.message = MagicMock()
    dp.message.outer_middleware = MagicMock()
    dp.message.middleware = MagicMock()
    dp.callback_query = MagicMock()
    dp.callback_query.outer_middleware = MagicMock()
    dp.include_router = MagicMock()
    dp.start_polling = AsyncMock()

    monkeypatch.setattr(bot_main, "Bot", FakeBot)
    monkeypatch.setattr(bot_main, "Dispatcher", MagicMock(return_value=dp))
    monkeypatch.setattr(bot_main, "settings", MagicMock(bot_token="tok"))

    await bot_main._run_polling()
    bot.delete_webhook.assert_awaited()
    dp.start_polling.assert_awaited()
    bot.session.close.assert_awaited()


@pytest.mark.asyncio
async def test_start_polling_restarts_then_cancel(monkeypatch) -> None:
    import asyncio

    import bot.main as bot_main

    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("crash")
        raise asyncio.CancelledError()

    monkeypatch.setattr(bot_main, "_run_polling", flaky)

    sleeps = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleeps)

    with pytest.raises(asyncio.CancelledError):
        await bot_main.start_polling()
    sleeps.assert_awaited()
