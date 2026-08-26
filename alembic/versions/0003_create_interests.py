"""create interests and user_interests tables with seed data

Revision ID: 0003_create_interests
Revises: 0002_create_follows_and_blocks
Create Date: 2026-08-27 02:40:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_create_interests"
down_revision: Union[str, None] = "0002_create_follows_and_blocks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_INTERESTS = [
    {"id": uuid.uuid4(), "name": "Technology", "slug": "technology", "description": "Latest tech, gadgets, AI, and software"},
    {"id": uuid.uuid4(), "name": "Gaming", "slug": "gaming", "description": "PC, console, mobile gaming, and esports"},
    {"id": uuid.uuid4(), "name": "Music", "slug": "music", "description": "Pop, Hip-Hop, Indie, EDM, Rock, and live shows"},
    {"id": uuid.uuid4(), "name": "Movies & Anime", "slug": "movies-anime", "description": "Cinema, TV series, streaming, and anime"},
    {"id": uuid.uuid4(), "name": "Sports & Fitness", "slug": "sports-fitness", "description": "Gym, running, football, basketball, and athletics"},
    {"id": uuid.uuid4(), "name": "Art & Design", "slug": "art-design", "description": "Digital art, UI/UX, graphic design, and illustration"},
    {"id": uuid.uuid4(), "name": "Photography", "slug": "photography", "description": "Street photography, portrait, landscape, and videography"},
    {"id": uuid.uuid4(), "name": "Travel & Adventure", "slug": "travel-adventure", "description": "Backpacking, road trips, culture, and exploration"},
    {"id": uuid.uuid4(), "name": "Fashion & Lifestyle", "slug": "fashion-lifestyle", "description": "Streetwear, beauty, trends, and daily lifestyle"},
    {"id": uuid.uuid4(), "name": "Food & Cooking", "slug": "food-cooking", "description": "Recipes, street food, baking, and dining out"},
    {"id": uuid.uuid4(), "name": "Programming & AI", "slug": "programming-ai", "description": "Coding, web development, open source, and machine learning"},
]


def upgrade() -> None:
    # Create interests table
    interests_table = op.create_table(
        "interests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_interests_id"), "interests", ["id"], unique=False)
    op.create_index(op.f("ix_interests_name"), "interests", ["name"], unique=True)
    op.create_index(op.f("ix_interests_slug"), "interests", ["slug"], unique=True)

    # Create user_interests table
    op.create_table(
        "user_interests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("interest_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["interest_id"], ["interests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "interest_id", name="uq_user_interest_user_interest"),
    )
    op.create_index(op.f("ix_user_interests_id"), "user_interests", ["id"], unique=False)
    op.create_index(op.f("ix_user_interests_interest_id"), "user_interests", ["interest_id"], unique=False)
    op.create_index(op.f("ix_user_interests_user_id"), "user_interests", ["user_id"], unique=False)

    # Seed default interests
    op.bulk_insert(interests_table, SEED_INTERESTS)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_interests_user_id"), table_name="user_interests")
    op.drop_index(op.f("ix_user_interests_interest_id"), table_name="user_interests")
    op.drop_index(op.f("ix_user_interests_id"), table_name="user_interests")
    op.drop_table("user_interests")

    op.drop_index(op.f("ix_interests_slug"), table_name="interests")
    op.drop_index(op.f("ix_interests_name"), table_name="interests")
    op.drop_index(op.f("ix_interests_id"), table_name="interests")
    op.drop_table("interests")
