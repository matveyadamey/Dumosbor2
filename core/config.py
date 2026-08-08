from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Railway отдаёт postgres:// или postgresql:// — приводим к asyncpg.

    Убираем libpq-параметры (sslmode и т.п.): asyncpg их не понимает.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    if not parsed.query:
        return url

    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in ("sslmode", "ssl", "channel_binding"):
        params.pop(key, None)
    return urlunparse(parsed._replace(query=urlencode(params)))


class Settings(BaseSettings):
    bot_token: str = ""
    database_url: str
    media_dir: str = "/app/media_data"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _normalize_db_url(self) -> "Settings":
        self.database_url = normalize_database_url(self.database_url)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()