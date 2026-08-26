"""create communities, memberships, and join requests tables

Revision ID: 0004_create_communities
Revises: 0003_create_interests
Create Date: 2026-08-27 02:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_create_communities"
down_revision: Union[str, None] = "0003_create_interests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create communities table
    op.create_table(
        "communities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("interest_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("cover_image_url", sa.String(length=500), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("is_private", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("member_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("post_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["interest_id"], ["interests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_communities_id"), "communities", ["id"], unique=False)
    op.create_index(op.f("ix_communities_interest_id"), "communities", ["interest_id"], unique=False)
    op.create_index(op.f("ix_communities_name"), "communities", ["name"], unique=False)
    op.create_index(op.f("ix_communities_owner_id"), "communities", ["owner_id"], unique=False)
    op.create_index(op.f("ix_communities_slug"), "communities", ["slug"], unique=True)

    # 2. Create community_memberships table
    op.create_table(
        "community_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("community_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default=sa.text("'member'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("community_id", "user_id", name="uq_community_membership_user"),
    )
    op.create_index(op.f("ix_community_memberships_community_id"), "community_memberships", ["community_id"], unique=False)
    op.create_index(op.f("ix_community_memberships_id"), "community_memberships", ["id"], unique=False)
    op.create_index(op.f("ix_community_memberships_user_id"), "community_memberships", ["user_id"], unique=False)

    # 3. Create community_join_requests table
    op.create_table(
        "community_join_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("community_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["community_id"], ["communities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("community_id", "user_id", name="uq_community_join_request_user"),
    )
    op.create_index(op.f("ix_community_join_requests_community_id"), "community_join_requests", ["community_id"], unique=False)
    op.create_index(op.f("ix_community_join_requests_id"), "community_join_requests", ["id"], unique=False)
    op.create_index(op.f("ix_community_join_requests_user_id"), "community_join_requests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_community_join_requests_user_id"), table_name="community_join_requests")
    op.drop_index(op.f("ix_community_join_requests_id"), table_name="community_join_requests")
    op.drop_index(op.f("ix_community_join_requests_community_id"), table_name="community_join_requests")
    op.drop_table("community_join_requests")

    op.drop_index(op.f("ix_community_memberships_user_id"), table_name="community_memberships")
    op.drop_index(op.f("ix_community_memberships_id"), table_name="community_memberships")
    op.drop_index(op.f("ix_community_memberships_community_id"), table_name="community_memberships")
    op.drop_table("community_memberships")

    op.drop_index(op.f("ix_communities_slug"), table_name="communities")
    op.drop_index(op.f("ix_communities_owner_id"), table_name="communities")
    op.drop_index(op.f("ix_communities_name"), table_name="communities")
    op.drop_index(op.f("ix_communities_interest_id"), table_name="communities")
    op.drop_index(op.f("ix_communities_id"), table_name="communities")
    op.drop_table("communities")
