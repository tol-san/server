import uuid
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.communities.models import Community, CommunityMembership
from app.interests.models import Interest
from app.posts.models import Post
from app.users.models import Block, Follow, Profile, User


class SearchRepository:
    """Repository handling SQL-based searches and full database extraction for index sync."""

    def _get_blocked_subquery(self, user_id: Optional[uuid.UUID]):
        if not user_id:
            return select(Block.blocked_id).where(Block.id.is_(None))
        return (
            select(Block.blocked_id)
            .where(Block.blocker_id == user_id)
            .union(select(Block.blocker_id).where(Block.blocked_id == user_id))
        )

    def _get_joined_communities_subquery(self, user_id: Optional[uuid.UUID]):
        if not user_id:
            return select(CommunityMembership.community_id).where(
                CommunityMembership.id.is_(None)
            )
        return select(CommunityMembership.community_id).where(
            CommunityMembership.user_id == user_id
        )

    def _get_following_subquery(self, user_id: Optional[uuid.UUID]):
        if not user_id:
            return select(Follow.following_id).where(Follow.id.is_(None))
        return select(Follow.following_id).where(Follow.follower_id == user_id)

    async def search_users(
        self,
        db: AsyncSession,
        *,
        query: str,
        current_user_id: Optional[uuid.UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[User], int]:
        clean_q = f"%{query.strip().lower()}%"
        blocked_sub = self._get_blocked_subquery(current_user_id)

        filters = [
            User.is_active.is_(True),
            User.id.not_in(blocked_sub),
            or_(
                func.lower(User.username).like(clean_q),
                func.lower(Profile.display_name).like(clean_q),
                func.lower(Profile.bio).like(clean_q),
            ),
        ]

        count_stmt = (
            select(func.count(User.id))
            .join(Profile, Profile.user_id == User.id)
            .where(*filters)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(User)
            .join(Profile, Profile.user_id == User.id)
            .where(*filters)
            .options(selectinload(User.profile))
            .order_by(Profile.follower_count.desc(), User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def search_communities(
        self,
        db: AsyncSession,
        *,
        query: str,
        current_user_id: Optional[uuid.UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Community], int]:
        clean_q = f"%{query.strip().lower()}%"
        joined_sub = self._get_joined_communities_subquery(current_user_id)

        accessible_cond = or_(
            Community.is_private.is_(False),
            Community.id.in_(joined_sub),
        )

        filters = [
            accessible_cond,
            or_(
                func.lower(Community.name).like(clean_q),
                func.lower(Community.slug).like(clean_q),
                func.lower(Community.description).like(clean_q),
            ),
        ]

        count_stmt = select(func.count(Community.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Community)
            .where(*filters)
            .options(selectinload(Community.interest))
            .order_by(Community.member_count.desc(), Community.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def search_posts(
        self,
        db: AsyncSession,
        *,
        query: str,
        current_user_id: Optional[uuid.UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Post], int]:
        clean_q = f"%{query.strip().lower()}%"
        blocked_sub = self._get_blocked_subquery(current_user_id)
        following_sub = self._get_following_subquery(current_user_id)
        joined_comm_sub = self._get_joined_communities_subquery(current_user_id)

        public_communities_sub = select(Community.id).where(
            Community.is_private.is_(False)
        )

        accessible_community = or_(
            Post.community_id.is_(None),
            Post.community_id.in_(public_communities_sub),
            Post.community_id.in_(joined_comm_sub),
        )

        visibility_cond = or_(
            Post.visibility == "public",
            (Post.visibility == "followers_only")
            & (
                Post.author_id.in_(following_sub)
                | (Post.author_id == current_user_id if current_user_id else False)
            ),
            (Post.visibility == "private")
            & (Post.author_id == current_user_id if current_user_id else False),
        )

        filters = [
            Post.author_id.not_in(blocked_sub),
            accessible_community,
            visibility_cond,
            or_(
                func.lower(Post.title).like(clean_q),
                func.lower(Post.content).like(clean_q),
            ),
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
            .order_by(Post.like_count.desc(), Post.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def search_interests(
        self,
        db: AsyncSession,
        *,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Interest], int]:
        clean_q = f"%{query.strip().lower()}%"
        filters = [
            or_(
                func.lower(Interest.name).like(clean_q),
                func.lower(Interest.slug).like(clean_q),
                func.lower(Interest.description).like(clean_q),
            )
        ]

        count_stmt = select(func.count(Interest.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Interest)
            .where(*filters)
            .order_by(Interest.name.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.scalars().all(), total

    # --- Full Extraction for Index Syncing ---
    async def fetch_all_users_for_sync(self, db: AsyncSession) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.is_active.is_(True))
            .options(selectinload(User.profile))
        )
        return (await db.execute(stmt)).scalars().all()

    async def fetch_all_communities_for_sync(
        self, db: AsyncSession
    ) -> Sequence[Community]:
        stmt = select(Community).options(selectinload(Community.interest))
        return (await db.execute(stmt)).scalars().all()

    async def fetch_all_posts_for_sync(self, db: AsyncSession) -> Sequence[Post]:
        stmt = select(Post).options(
            selectinload(Post.author).selectinload(User.profile),
            selectinload(Post.community),
        )
        return (await db.execute(stmt)).scalars().all()

    async def fetch_all_interests_for_sync(
        self, db: AsyncSession
    ) -> Sequence[Interest]:
        stmt = select(Interest)
        return (await db.execute(stmt)).scalars().all()


search_repository = SearchRepository()
