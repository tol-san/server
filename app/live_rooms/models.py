"""SQLAlchemy ORM models for live rooms, sessions, and provider event idempotency."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class LiveRoom(Base):
    __tablename__ = "live_rooms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="LIVEKIT")
    provider_room_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="READY", index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    creator = relationship("User", foreign_keys=[created_by], lazy="selectin")
    sessions = relationship(
        "LiveSession",
        back_populates="room",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    class Status:
        READY = "READY"
        LIVE = "LIVE"
        ENDED = "ENDED"
        CANCELLED = "CANCELLED"


class LiveSession(Base):
    __tablename__ = "live_sessions"
    __table_args__ = (
        Index(
            "uq_live_sessions_one_active_per_room",
            "room_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("live_rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    peak_viewers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_viewers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_joins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    room = relationship("LiveRoom", back_populates="sessions", lazy="selectin")
    host = relationship("User", foreign_keys=[host_id], lazy="selectin")


class ProviderEvent(Base):
    """Stores processed provider webhook event IDs for idempotency."""
    __tablename__ = "provider_events"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", name="uq_provider_event_identity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
