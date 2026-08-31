import uuid
from typing import Optional, Sequence, Tuple
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.communities.models import Community, CommunityMembership
from app.interests.models import UserInterest
from app.posts.models import Post
from app.posts.access import post_access_filters
from app.users.models import Block, Follow, User


class FeedRepository:
    """Repository handling database queries for multi-stream feeds."""

    def _get_blocked_subquery(self, user_id: uuid.UUID):
        """Subquery of user IDs blocked by or blocking the current user."""
        return (
            select(Block.blocked_id)
            .where(Block.blocker_id == user_id)
            .union(select(Block.blocker_id).where(Block.blocked_id == user_id))
        )

    def _get_joined_communities_subquery(self, user_id: uuid.UUID):
        """Subquery of community IDs where current user is a member."""
        return select(CommunityMembership.community_id).where(
            CommunityMembership.user_id == user_id
        )

    def _get_following_subquery(self, user_id: uuid.UUID):
        """Subquery of user IDs followed by current user."""
        return select(Follow.following_id).where(Follow.follower_id == user_id)

    def _get_user_interests_subquery(self, user_id: uuid.UUID):
        """Subquery of interest IDs selected by current user."""
        return select(UserInterest.interest_id).where(UserInterest.user_id == user_id)

    async def get_home_feed(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Post], int]:
        blocked_sub = self._get_blocked_subquery(user_id)
        following_sub = self._get_following_subquery(user_id)
        joined_comm_sub = self._get_joined_communities_subquery(user_id)

        source_condition = or_(
            Post.author_id.in_(following_sub),
            Post.community_id.in_(joined_comm_sub),
            Post.author_id == user_id,
        )

        filters = [
            source_condition,
            *post_access_filters(user_id),
        ]

        count_stmt = select(func.count(Post.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Post)
            .where(*filters)
            .options(
                selectinload(Post.author).selectinload(User.profile),
                selectinload(Post.community),
                selectinload(Post.media_items),
            )
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def get_discover_feed(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Post], int]:
        blocked_sub = self._get_blocked_subquery(user_id)
        joined_comm_sub = self._get_joined_communities_subquery(user_id)
        user_interests_sub = self._get_user_interests_subquery(user_id)

        public_communities_sub = select(Community.id).where(
            Community.is_private.is_(False)
        )

        accessible_community = or_(
            Post.community_id.is_(None),
            Post.community_id.in_(public_communities_sub),
            Post.community_id.in_(joined_comm_sub),
        )

        filters = [
            Post.visibility == "public",
            *post_access_filters(user_id),
        ]

        count_stmt = select(func.count(Post.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Interest match affinity bonus
        matched_comm_sub = select(Community.id).where(
            Community.interest_id.in_(user_interests_sub)
        )
        interest_bonus = case(
            (Post.community_id.in_(matched_comm_sub), 15),
            else_=0,
        )

        score_expr = (
            (Post.like_count * 2)
            + (Post.comment_count * 3)
            + (Post.save_count * 4)
            + (Post.share_count * 5)
            + interest_bonus
        )

        stmt = (
            select(Post)
            .where(*filters)
            .options(
                selectinload(Post.author).selectinload(User.profile),
                selectinload(Post.community),
                selectinload(Post.media_items),
            )
            .order_by(score_expr.desc(), Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def get_shorts_feed(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Post], int]:
        blocked_sub = self._get_blocked_subquery(user_id)
        joined_comm_sub = self._get_joined_communities_subquery(user_id)
        user_interests_sub = self._get_user_interests_subquery(user_id)

        public_communities_sub = select(Community.id).where(
            Community.is_private.is_(False)
        )

        accessible_community = or_(
            Post.community_id.is_(None),
            Post.community_id.in_(public_communities_sub),
            Post.community_id.in_(joined_comm_sub),
        )

        filters = [
            Post.post_type == "video",
            Post.visibility == "public",
            *post_access_filters(user_id),
        ]

        count_stmt = select(func.count(Post.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Interest match affinity bonus for vertical videos
        matched_comm_sub = select(Community.id).where(
            Community.interest_id.in_(user_interests_sub)
        )
        interest_bonus = case(
            (Post.community_id.in_(matched_comm_sub), 20),
            else_=0,
        )

        score_expr = (
            (Post.like_count * 2)
            + (Post.comment_count * 3)
            + (Post.save_count * 5)
            + (Post.share_count * 4)
            + interest_bonus
        )

        stmt = (
            select(Post)
            .where(*filters)
            .options(
                selectinload(Post.author).selectinload(User.profile),
                selectinload(Post.community),
                selectinload(Post.media_items),
            )
            .order_by(score_expr.desc(), Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all(), total


feed_repository = FeedRepository()
