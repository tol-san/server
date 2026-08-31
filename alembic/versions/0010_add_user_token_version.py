"""Add user token version for session revocation.

Revision ID: 0010_user_token_version
Revises: 0009_chat_live_rooms
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_user_token_version"
down_revision = "0009_chat_live_rooms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
