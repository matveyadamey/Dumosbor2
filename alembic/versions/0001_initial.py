"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "texts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("short", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("synced", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_texts_message_id", "texts", ["message_id"])

    op.create_table(
        "images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "text_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("texts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
    )
    op.create_index("ix_images_text_id", "images", ["text_id"])

    op.create_table(
        "youtube_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("synced", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("youtube_links")
    op.drop_index("ix_images_text_id", table_name="images")
    op.drop_table("images")
    op.drop_index("ix_texts_message_id", table_name="texts")
    op.drop_table("texts")