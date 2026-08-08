import pytest
from bot.path_validation import is_valid_path


@pytest.mark.parametrize(
    "path",
    [
        "attachments",
        "folder/sub",
        "Images 2024",
        "a" * 200,
    ],
)
def test_valid_paths(path: str) -> None:
    assert is_valid_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "",
        "   ",
        "bad:path",
        "a<b",
        "a>b",
        "a|b",
        "a?b",
        "a*b",
        'say"hi',
        "a\x00b",
    ],
)
def test_invalid_paths(path: str) -> None:
    assert is_valid_path(path) is False
