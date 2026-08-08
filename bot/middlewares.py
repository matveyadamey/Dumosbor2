from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.services import buffer_media_group
from core.settings_repo import get_setting


class AdminFilterMiddleware(BaseMiddleware):
    """Пропускает только админа. До регистрации админа разрешает только /start."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Optional[Any]:
        user = getattr(event, "from_user", None)
        admin_raw = await get_setting("admin_chat_id")

        if admin_raw is None:
            if isinstance(event, Message) and event.text:
                cmd = event.text.strip().split()[0].split("@")[0]
                if cmd == "/start":
                    return await handler(event, data)
            return None

        if user is not None and user.id == int(admin_raw):
            return await handler(event, data)

        return None


class AlbumBufferMiddleware(BaseMiddleware):
    """Группирует сообщения альбома по media_group_id с задержкой 1.5с."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Optional[Any]:
        if isinstance(event, Message) and event.media_group_id:
            await buffer_media_group(event)
            return None
        return await handler(event, data)
