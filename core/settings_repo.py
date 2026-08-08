from typing import Optional

from sqlalchemy import select

from core.database import async_session_maker
from core.models import Setting


async def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    async with async_session_maker() as session:
        res = await session.execute(select(Setting).where(Setting.key == key))
        row = res.scalar_one_or_none()
        return row.value if row else default


async def set_setting(key: str, value: str) -> None:
    async with async_session_maker() as session:
        row = await session.get(Setting, key)
        if row:
            row.value = str(value)
        else:
            session.add(Setting(key=key, value=str(value)))
        await session.commit()