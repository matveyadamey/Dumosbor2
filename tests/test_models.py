from core.models import Image, Setting, TextRecord, YouTubeLink


def test_model_tablename() -> None:
    assert TextRecord.__tablename__ == "texts"
    assert Image.__tablename__ == "images"
    assert YouTubeLink.__tablename__ == "youtube_links"
    assert Setting.__tablename__ == "settings"


def test_text_record_fields() -> None:
    rec = TextRecord(message_id=1, content="x", short=True, synced=False)
    assert rec.message_id == 1
    assert rec.content == "x"
    assert rec.short is True
    assert rec.synced is False
