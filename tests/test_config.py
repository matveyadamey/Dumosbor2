import pytest
from core.config import normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ""),
        (
            "postgres://u:p@h:5432/db",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        (
            "postgresql://u:p@h:5432/db",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        (
            "postgresql+asyncpg://u:p@h:5432/db",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        (
            "postgresql://u:p@h:5432/db?sslmode=require",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        (
            "postgres://u:p@h:5432/db?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        (
            "postgresql://u:p@h:5432/db?sslmode=require&application_name=x",
            "postgresql+asyncpg://u:p@h:5432/db?application_name=x",
        ),
    ],
)
def test_normalize_database_url(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected
