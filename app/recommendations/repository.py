import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.communities.models import Community, CommunityMembership
from app.interests.models import Interest, UserInterest
from app.users.models import Block, Follow, Profile, User


class RecommendationRepository:
    """Repository handling rule-based recommendation queries for communities and users."""

    def _get_blocked_subquery(self, user_id: uuid.UUID):
        return (
            select(Block.blocked_id)
            .where(Block.blocker_id == user_id)
            .union(select(Block.blocker_id).where(Block.blocked_id == user_id))
        )

    def _get_following_subquery(self, user_id: uuid.UUID):
        return select(Follow.following_id).where(Follow.follower_id == user_id)

    def _get_joined_communities_subquery(self, user_id: uuid.UUID):
        return select(CommunityMembership.community_id).where(
            CommunityMembership.user_id == user_id
        )

    def _get_user_interests_subquery(self, user_id: uuid.UUID):
        return select(UserInterest.interest_id).where(UserInterest.user_id == user_id)

    async def recommend_communities(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        joined_sub = self._get_joined_communities_subquery(user_id)
        user_interests_sub = self._get_user_interests_subquery(user_id)

        filters = [Community.id.not_in(joined_sub)]

        count_stmt = select(func.count(Community.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Prioritize communities matching user's selected interests
        match_priority = case(
            (Community.interest_id.in_(user_interests_sub), 1),
            else_=0,
        )

        stmt = (
            select(Community)
            .where(*filters)
            .options(selectinload(Community.interest))
            .order_by(
                match_priority.desc(),
                Community.member_count.desc(),
                Community.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        communities = result.scalars().all()

        # Fetch user's interest IDs to flag exact matches
        user_interest_ids = set((await db.execute(user_interests_sub)).scalars().all())

        items = []
        for comm in communities:
            is_matched = bool(
                comm.interest_id and comm.interest_id in user_interest_ids
            )
            items.append(
                {
                    "id": comm.id,
                    "name": comm.name,
                    "slug": comm.slug,
                    "description": comm.description,
                    "avatar_url": comm.avatar_url,
                    "cover_image_url": comm.cover_image_url,
                    "is_private": comm.is_private,
                    "member_count": comm.member_count,
                    "post_count": comm.post_count,
                    "interest_id": comm.interest_id,
                    "interest_name": comm.interest.name if comm.interest else None,
                    "is_matched_interest": is_matched,
                }
            )

        return items, total

    async def recommend_users(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        blocked_sub = self._get_blocked_subquery(user_id)
        following_sub = self._get_following_subquery(user_id)
        user_interests_sub = self._get_user_interests_subquery(user_id)

        # Count mutual interests per user
        mutual_subquery = (
            select(
                UserInterest.user_id.label("uid"),
                func.count(UserInterest.interest_id).label("mutual_count"),
            )
            .where(UserInterest.interest_id.in_(user_interests_sub))
            .group_by(UserInterest.user_id)
            .subquery()
        )

        filters = [
            User.id != user_id,
            User.is_active.is_(True),
            User.id.not_in(following_sub),
            User.id.not_in(blocked_sub),
        ]

        count_stmt = select(func.count(User.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        mutual_count_expr = func.coalesce(mutual_subquery.c.mutual_count, 0)

        stmt = (
            select(User, mutual_count_expr.label("mutual_interests"))
            .join(Profile, Profile.user_id == User.id)
            .outerjoin(mutual_subquery, mutual_subquery.c.uid == User.id)
            .where(*filters)
            .options(selectinload(User.profile))
            .order_by(
                mutual_count_expr.desc(),
                Profile.follower_count.desc(),
                User.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        user_ids = [row[0].id for row in rows]

        # Fetch names of shared interests for these users
        shared_interests_by_user: Dict[uuid.UUID, List[str]] = {
            uid: [] for uid in user_ids
        }
        if user_ids:
            names_stmt = (
                select(UserInterest.user_id, Interest.name)
                .join(Interest, Interest.id == UserInterest.interest_id)
                .where(
                    UserInterest.user_id.in_(user_ids),
                    UserInterest.interest_id.in_(user_interests_sub),
                )
            )
            names_res = await db.execute(names_stmt)
            for target_uid, interest_name in names_res.all():
                shared_interests_by_user[target_uid].append(interest_name)

        items = []
        for user_obj, mutual_count in rows:
            prof = user_obj.profile
            items.append(
                {
                    "id": user_obj.id,
                    "username": user_obj.username,
                    "display_name": prof.display_name if prof else user_obj.username,
                    "avatar_url": prof.avatar_url if prof else None,
                    "bio": prof.bio if prof else None,
                    "follower_count": prof.follower_count if prof else 0,
                    "mutual_interest_count": int(mutual_count or 0),
                    "shared_interests": shared_interests_by_user.get(user_obj.id, []),
                }
            )

        return items, total


recommendation_repository = RecommendationRepository()
