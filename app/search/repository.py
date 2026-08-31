import uuid
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.communities.models import Community, CommunityMembership
from app.communities.access import community_access_filters
from app.interests.models import Interest
from app.posts.models import Post
from app.posts.access import post_access_filters
from app.users.models import Block, Follow, Profile, User


class SearchRepository:
    """Repository handling SQL-based searches and full database extraction for index sync."""

    def _get_blocked_conditions(self, col, user_id: Optional[uuid.UUID]):
        if not user_id:
            return []
        sub1 = select(Block.blocked_id).where(Block.blocker_id == user_id)
        sub2 = select(Block.blocker_id).where(Block.blocked_id == user_id)
        return [col.not_in(sub1), col.not_in(sub2)]

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

    async def get_blocked_user_ids(
        self, db: AsyncSession, user_id: Optional[uuid.UUID]
    ) -> set[str]:
        if not user_id:
            return set()
        stmt1 = select(Block.blocked_id).where(Block.blocker_id == user_id)
        stmt2 = select(Block.blocker_id).where(Block.blocked_id == user_id)
        res1 = await db.execute(stmt1)
        res2 = await db.execute(stmt2)
        return {str(uid) for uid in res1.scalars().all()} | {
            str(uid) for uid in res2.scalars().all()
        }

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

        filters = [
            User.is_active.is_(True),
            *self._get_blocked_conditions(User.id, current_user_id),
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
        filters = [
            *community_access_filters(current_user_id),
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
        filters = [
            *post_access_filters(current_user_id),
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
        stmt = (
            select(Community)
            .where(Community.is_private.is_(False))
            .options(selectinload(Community.interest))
        )
        return (await db.execute(stmt)).scalars().all()

    async def fetch_all_posts_for_sync(self, db: AsyncSession) -> Sequence[Post]:
        public_communities = select(Community.id).where(Community.is_private.is_(False))
        stmt = (
            select(Post)
            .where(
                Post.visibility == "public",
                or_(Post.community_id.is_(None), Post.community_id.in_(public_communities)),
            )
            .options(
                selectinload(Post.author).selectinload(User.profile),
                selectinload(Post.community),
            )
        )
        return (await db.execute(stmt)).scalars().all()

    async def fetch_all_interests_for_sync(
        self, db: AsyncSession
    ) -> Sequence[Interest]:
        stmt = select(Interest)
        return (await db.execute(stmt)).scalars().all()


search_repository = SearchRepository()
