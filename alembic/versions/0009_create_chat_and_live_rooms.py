"""Create chat_messages, live_rooms, live_sessions, provider_events, outbox_events, dead_letter_events

Revision ID: 0009_chat_live_rooms
Revises: 0008_notifications_reports
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "0009_chat_live_rooms"
down_revision = "0008_notifications_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # chat_messages
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Idempotency: mobile can safely retry without creating duplicates
        sa.Column("client_message_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "message_type",
            sa.String(30),
            nullable=False,
            server_default="TEXT",
        ),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column(
            "reply_to_message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "sender_id", "client_message_id", name="uq_chat_msg_sender_client_id"
        ),
    )
    # Composite index for keyset / cursor pagination
    op.create_index(
        "ix_chat_messages_community_created_id",
        "chat_messages",
        ["community_id", sa.text("created_at DESC"), sa.text("id DESC")],
        postgresql_using="btree",
    )
    op.create_index("ix_chat_messages_sender_id", "chat_messages", ["sender_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # live_rooms
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "live_rooms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # Provider abstraction — allows future Agora / Daily.co swap
        sa.Column(
            "provider",
            sa.String(30),
            nullable=False,
            server_default="LIVEKIT",
        ),
        sa.Column("provider_room_name", sa.String(150), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="READY",
            index=True,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )
    op.create_index("ix_live_rooms_community_id", "live_rooms", ["community_id"])
    op.create_index("ix_live_rooms_created_by", "live_rooms", ["created_by"])

    # ─────────────────────────────────────────────────────────────────────────
    # live_sessions
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "live_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("live_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "host_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_session_id", sa.String(255), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("peak_viewers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unique_viewers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_joins", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_live_sessions_room_id", "live_sessions", ["room_id"])
    op.create_index("ix_live_sessions_host_id", "live_sessions", ["host_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # provider_events (webhook idempotency)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "provider_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "provider", "provider_event_id", name="uq_provider_event_id"
        ),
    )
    op.create_index(
        "ix_provider_events_type", "provider_events", ["provider", "event_type"]
    )

    # ─────────────────────────────────────────────────────────────────────────
    # outbox_events (transactional outbox for reliable event delivery)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "outbox_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("aggregate_type", sa.String(60), nullable=False, index=True),
        sa.Column("aggregate_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            index=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # dead_letter_events (failed events after exhausting retries)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "dead_letter_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_event_id", UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_type", sa.String(60), nullable=False),
        sa.Column("aggregate_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("worker", sa.String(60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("dead_letter_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_provider_events_type", table_name="provider_events")
    op.drop_table("provider_events")
    op.drop_index("ix_live_sessions_host_id", table_name="live_sessions")
    op.drop_index("ix_live_sessions_room_id", table_name="live_sessions")
    op.drop_table("live_sessions")
    op.drop_index("ix_live_rooms_created_by", table_name="live_rooms")
    op.drop_index("ix_live_rooms_community_id", table_name="live_rooms")
    op.drop_table("live_rooms")
    op.drop_index("ix_chat_messages_sender_id", table_name="chat_messages")
    op.drop_index(
        "ix_chat_messages_community_created_id", table_name="chat_messages"
    )
    op.drop_table("chat_messages")
