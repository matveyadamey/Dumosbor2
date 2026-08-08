from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message


@pytest.mark.asyncio
async def test_cmd_start_sets_admin(monkeypatch) -> None:
    from bot.handlers import cmd_start

    async def fake_get(key, default=None):
        return None

    set_setting = AsyncMock()
    monkeypatch.setattr("bot.handlers.get_setting", fake_get)
    monkeypatch.setattr("bot.handlers.set_setting", set_setting)

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(id=777)
    message.answer = AsyncMock()

    await cmd_start(message)
    set_setting.assert_awaited_with("admin_chat_id", "777")
    message.answer.assert_awaited()


@pytest.mark.asyncio
async def test_set_image_path_valid(monkeypatch) -> None:
    from bot.handlers import cmd_set_image_path

    set_setting = AsyncMock()
    monkeypatch.setattr("bot.handlers.set_setting", set_setting)

    message = MagicMock(spec=Message)
    message.text = "/set_image_path attachments/tg"
    message.answer = AsyncMock()

    await cmd_set_image_path(message)
    set_setting.assert_awaited_with("image_path", "attachments/tg")


@pytest.mark.asyncio
async def test_set_image_path_invalid(monkeypatch) -> None:
    from bot.handlers import cmd_set_image_path

    set_setting = AsyncMock()
    monkeypatch.setattr("bot.handlers.set_setting", set_setting)

    message = MagicMock(spec=Message)
    message.text = "/set_image_path bad:path"
    message.answer = AsyncMock()

    await cmd_set_image_path(message)
    set_setting.assert_not_awaited()
    message.answer.assert_awaited()


@pytest.mark.asyncio
async def test_get_token(monkeypatch) -> None:
    from bot.handlers import cmd_get_token

    set_setting = AsyncMock()
    monkeypatch.setattr("bot.handlers.set_setting", set_setting)
    monkeypatch.setattr("bot.handlers.secrets.token_hex", lambda n: "a" * 64)

    message = MagicMock(spec=Message)
    message.answer = AsyncMock()

    await cmd_get_token(message)
    set_setting.assert_awaited_with("bearer_token", "a" * 64)
    message.answer.assert_awaited()


@pytest.mark.asyncio
async def test_content_handler_skips_album(monkeypatch) -> None:
    from bot.handlers import content_handler

    process = AsyncMock()
    monkeypatch.setattr("bot.handlers.process_data", process)

    message = MagicMock(spec=Message)
    message.media_group_id = "g1"
    await content_handler(message)
    process.assert_not_awaited()


@pytest.mark.asyncio
async def test_content_handler_processes(monkeypatch) -> None:
    from bot.handlers import content_handler

    process = AsyncMock()
    monkeypatch.setattr("bot.handlers.process_data", process)

    message = MagicMock(spec=Message)
    message.media_group_id = None
    await content_handler(message)
    process.assert_awaited_once_with([message])
