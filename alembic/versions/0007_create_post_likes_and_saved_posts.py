"""create post_likes and saved_posts tables

Revision ID: 0007_create_post_likes_and_saved_posts
Revises: 0006_create_comments
Create Date: 2026-08-27 03:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_post_likes_saved_posts"
down_revision: Union[str, None] = "0006_create_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create post_likes table
    op.create_table(
        "post_likes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_post_likes_user_post"),
    )
    op.create_index(op.f("ix_post_likes_id"), "post_likes", ["id"], unique=False)
    op.create_index(op.f("ix_post_likes_post_id"), "post_likes", ["post_id"], unique=False)
    op.create_index(op.f("ix_post_likes_user_id"), "post_likes", ["user_id"], unique=False)

    # 2. Create saved_posts table
    op.create_table(
        "saved_posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_saved_posts_user_post"),
    )
    op.create_index(op.f("ix_saved_posts_id"), "saved_posts", ["id"], unique=False)
    op.create_index(op.f("ix_saved_posts_post_id"), "saved_posts", ["post_id"], unique=False)
    op.create_index(op.f("ix_saved_posts_user_id"), "saved_posts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_posts_user_id"), table_name="saved_posts")
    op.drop_index(op.f("ix_saved_posts_post_id"), table_name="saved_posts")
    op.drop_index(op.f("ix_saved_posts_id"), table_name="saved_posts")
    op.drop_table("saved_posts")

    op.drop_index(op.f("ix_post_likes_user_id"), table_name="post_likes")
    op.drop_index(op.f("ix_post_likes_post_id"), table_name="post_likes")
    op.drop_index(op.f("ix_post_likes_id"), table_name="post_likes")
    op.drop_table("post_likes")
