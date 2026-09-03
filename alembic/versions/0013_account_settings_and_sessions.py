"""Create tables for user privacy settings, notification preferences, and user sessions.

Revision ID: 0013_account_settings_and_sessions
Revises: 0012_report_integrity
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0013_account_settings_and_sessions"
down_revision: Union[str, None] = "0012_report_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. User Privacy Settings
    op.create_table(
        "user_privacy_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("is_private", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("allow_comments", sa.String(length=20), server_default="everyone", nullable=False),
        sa.Column("allow_mentions", sa.String(length=20), server_default="everyone", nullable=False),
        sa.Column("show_activity_status", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("search_discoverable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_privacy_settings_user_id"),
    )
    op.create_index(
        op.f("ix_user_privacy_settings_user_id"),
        "user_privacy_settings",
        ["user_id"],
        unique=True,
    )

    # 2. Notification Preferences
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("likes_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("comments_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("follows_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("mentions_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("community_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("quiet_hours_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=10), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )
    op.create_index(
        op.f("ix_notification_preferences_user_id"),
        "notification_preferences",
        ["user_id"],
        unique=True,
    )

    # 3. User Sessions
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_jti", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("device_name", sa.String(length=100), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_jti", name="uq_user_sessions_refresh_jti"),
    )
    op.create_index(
        op.f("ix_user_sessions_user_id"),
        "user_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_sessions_refresh_jti"),
        "user_sessions",
        ["refresh_jti"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_sessions_refresh_jti"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index(op.f("ix_notification_preferences_user_id"), table_name="notification_preferences")
    op.drop_table("notification_preferences")

    op.drop_index(op.f("ix_user_privacy_settings_user_id"), table_name="user_privacy_settings")
    op.drop_table("user_privacy_settings")
