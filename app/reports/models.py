import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.communities.models import Community
    from app.users.models import User


class Report(Base):
    """Report entity for user flagging of content, users, communities, and chat messages."""

    __tablename__ = "reports"
    __table_args__ = (
        Index(
            "uq_reports_open_reporter_target",
            "reporter_id",
            "report_type",
            "target_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'REVIEWING')"),
            sqlite_where=text("status IN ('PENDING', 'REVIEWING')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # user, post, comment, community, chat_message
    target_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("communities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # spam, harassment, inappropriate_content, hate_speech, violence, copyright, other
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True,
    )  # PENDING, REVIEWING, RESOLVED, REJECTED
    resolution_action: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )  # none, user_suspended, dismissed
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    reporter: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[reporter_id],
        backref="filed_reports",
    )
    reviewer: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[reviewed_by],
        backref="resolved_reports",
    )
    community: Mapped[Optional["Community"]] = relationship(  # noqa: F821
        "Community",
        foreign_keys=[community_id],
    )
