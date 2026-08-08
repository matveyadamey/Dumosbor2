from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="ℹ️ О боте", callback_data="about")
    kb.button(text="Указать путь к изображениям", callback_data="set_image_path")
    kb.button(text="Получить токен", callback_data="get_token")
    kb.adjust(1)
    return kb.as_markup()