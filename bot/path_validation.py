import re

# Недопустимые символы для путей в большинстве ОС + управляющие символы
_INVALID_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')


def is_valid_path(path: str) -> bool:
    """Проверяет именно синтаксис пути (без обращения к ФС)."""
    path = (path or "").strip()
    if not path:
        return False
    if _INVALID_CHARS.search(path):
        return False
    return True