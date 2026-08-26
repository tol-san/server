import uuid
from typing import List, Optional
from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base, TimestampMixin


class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    post_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(20),
        default="public",
        nullable=False,
    )
    like_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    comment_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    share_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    save_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    author = relationship("User", foreign_keys=[author_id], lazy="selectin")
    community = relationship("Community", foreign_keys=[community_id], lazy="selectin")
    media_items = relationship(
        "PostMedia",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PostMedia.order.asc()",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Post id={self.id} author_id={self.author_id} post_type={self.post_type}>"


class PostMedia(Base, TimestampMixin):
    __tablename__ = "post_media"
    __mapper_args__ = {
        "confirm_deleted_rows": False,
    }

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    duration: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    post = relationship("Post", back_populates="media_items", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PostMedia id={self.id} post_id={self.post_id} media_type={self.media_type}>"


class PostLike(Base, TimestampMixin):
    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_post_likes_user_post"),
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
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    post = relationship("Post", foreign_keys=[post_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<PostLike id={self.id} user_id={self.user_id} post_id={self.post_id}>"


class SavedPost(Base, TimestampMixin):
    __tablename__ = "saved_posts"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_saved_posts_user_post"),
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
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    post = relationship("Post", foreign_keys=[post_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<SavedPost id={self.id} user_id={self.user_id} post_id={self.post_id}>"

