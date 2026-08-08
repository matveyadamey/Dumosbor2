import secrets

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu_kb
from bot.path_validation import is_valid_path
from bot.services import buffer_media_group, process_and_save
from core.settings_repo import get_setting, set_setting

router = Router(name="main")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    admin_raw = await get_setting("admin_chat_id")
    if admin_raw is None:
        await set_setting("admin_chat_id", str(message.from_user.id))
    await message.answer(
        "Привет! Я буду сохранять твои сообщения в Obsidian.\nВыбери действие:",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("set_image_path"))
async def cmd_set_image_path(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: /set_image_path <путь>")
        return
    path = parts[1].strip()
    if is_valid_path(path):
        await set_setting("image_path", path)
        await message.answer(f"✅ Путь к изображениям сохранён: {path}")
    else:
        await message.answer('❌ Некорректный путь. Убери недопустимые символы: < > : " | ? *')


async def _issue_token(message: Message) -> None:
    token = secrets.token_hex(32)
    await set_setting("bearer_token", token)
    await message.answer(
        f"🔑 Твой Bearer-токен:\n\n{token}\n\nВставь его в настройки Obsidian-плагина."
    )


@router.message(Command("get_token"))
async def cmd_get_token(message: Message) -> None:
    await _issue_token(message)


# --- Callbacks ---
@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Бот для синхронизации Telegram → Obsidian (текст, картинки, YouTube)."
    )
    await callback.answer()


@router.callback_query(F.data == "set_image_path")
async def cb_set_image_path(callback: CallbackQuery) -> None:
    await callback.message.answer("Отправь команду: /set_image_path <путь>")
    await callback.answer()


@router.callback_query(F.data == "get_token")
async def cb_get_token(callback: CallbackQuery) -> None:
    await _issue_token(callback.message)
    await callback.answer()


# --- Контент ---
# Альбомы собираем в буфер
@router.message(lambda m: bool(m.media_group_id))
async def media_group_handler(message: Message) -> None:
    await buffer_media_group(message)


# Одиночные сообщения (текст / фото / видео / документ)
@router.message(F.text | F.photo | F.video | F.document)
async def content_handler(message: Message) -> None:
    await process_and_save([message])