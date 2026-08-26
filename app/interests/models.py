import uuid
from typing import Optional
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base, TimestampMixin


class Interest(Base, TimestampMixin):
    __tablename__ = "interests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    icon_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Interest id={self.id} name={self.name} slug={self.slug}>"


class UserInterest(Base, TimestampMixin):
    __tablename__ = "user_interests"
    __table_args__ = (
        UniqueConstraint("user_id", "interest_id", name="uq_user_interest_user_interest"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interest_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("interests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    interest: Mapped["Interest"] = relationship("Interest", foreign_keys=[interest_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<UserInterest id={self.id} user_id={self.user_id} interest_id={self.interest_id}>"
