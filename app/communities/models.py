import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base, TimestampMixin


class Community(Base, TimestampMixin):
    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interest_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("interests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )
    cover_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    member_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    post_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    owner = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    interest = relationship("Interest", foreign_keys=[interest_id], lazy="selectin")
    memberships = relationship(
        "CommunityMembership",
        back_populates="community",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    join_requests = relationship(
        "CommunityJoinRequest",
        back_populates="community",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Community id={self.id} name={self.name} is_private={self.is_private}>"


class CommunityMembership(Base, TimestampMixin):
    __tablename__ = "community_memberships"
    __table_args__ = (
        UniqueConstraint("community_id", "user_id", name="uq_community_membership_user"),
    )
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="member",
        nullable=False,
    )

    community = relationship("Community", back_populates="memberships", lazy="selectin")
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<CommunityMembership community_id={self.community_id} user_id={self.user_id} role={self.role}>"


class CommunityJoinRequest(Base, TimestampMixin):
    __tablename__ = "community_join_requests"
    __table_args__ = (
        UniqueConstraint("community_id", "user_id", name="uq_community_join_request_user"),
    )
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )

    community = relationship("Community", back_populates="join_requests", lazy="selectin")
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<CommunityJoinRequest community_id={self.community_id} user_id={self.user_id} status={self.status}>"
