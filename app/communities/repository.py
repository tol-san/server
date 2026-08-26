import uuid
from typing import Optional, Sequence, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.communities.models import Community, CommunityJoinRequest, CommunityMembership
from app.users.models import Profile, User


class CommunityRepository:
    """Repository handling database operations for Community, Membership, and Join Requests."""

    async def get_by_id(self, db: AsyncSession, community_id: uuid.UUID) -> Optional[Community]:
        stmt = (
            select(Community)
            .where(Community.id == community_id)
            .options(
                selectinload(Community.owner).selectinload(User.profile),
                selectinload(Community.interest),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[Community]:
        stmt = (
            select(Community)
            .where(Community.slug == slug.lower().strip())
            .options(
                selectinload(Community.owner).selectinload(User.profile),
                selectinload(Community.interest),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        owner_id: uuid.UUID,
        name: str,
        slug: str,
        description: Optional[str] = None,
        interest_id: Optional[uuid.UUID] = None,
        cover_image_url: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_private: bool = False,
    ) -> Community:
        community = Community(
            owner_id=owner_id,
            name=name.strip(),
            slug=slug.lower().strip(),
            description=description.strip() if description else None,
            interest_id=interest_id,
            cover_image_url=cover_image_url.strip() if cover_image_url else None,
            avatar_url=avatar_url.strip() if avatar_url else None,
            is_private=is_private,
            member_count=1,
            post_count=0,
        )
        db.add(community)
        await db.flush()  # Generate community.id

        # Creator automatically becomes the Owner member
        membership = CommunityMembership(
            community_id=community.id,
            user_id=owner_id,
            role="owner",
        )
        db.add(membership)

        await db.commit()
        await db.refresh(community)
        return community

    async def update(
        self,
        db: AsyncSession,
        community: Community,
        **kwargs,
    ) -> Community:
        for key, value in kwargs.items():
            if hasattr(community, key) and value is not None:
                setattr(community, key, value)

        db.add(community)
        await db.commit()
        await db.refresh(community)
        return community

    async def delete(self, db: AsyncSession, community: Community) -> None:
        await db.delete(community)
        await db.commit()

    async def list_communities(
        self,
        db: AsyncSession,
        *,
        search: Optional[str] = None,
        interest_id: Optional[uuid.UUID] = None,
        is_private: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Community], int]:
        filters = []
        if search:
            search_clean = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Community.name).like(search_clean),
                    func.lower(Community.description).like(search_clean),
                )
            )
        if interest_id is not None:
            filters.append(Community.interest_id == interest_id)
        if is_private is not None:
            filters.append(Community.is_private == is_private)

        count_stmt = select(func.count(Community.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Community)
            .options(
                selectinload(Community.owner).selectinload(User.profile),
                selectinload(Community.interest),
            )
            .order_by(Community.member_count.desc(), Community.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def list_user_communities(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Community], int]:
        count_stmt = (
            select(func.count(CommunityMembership.id))
            .where(CommunityMembership.user_id == user_id)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Community)
            .join(CommunityMembership, CommunityMembership.community_id == Community.id)
            .where(CommunityMembership.user_id == user_id)
            .options(
                selectinload(Community.owner).selectinload(User.profile),
                selectinload(Community.interest),
            )
            .order_by(CommunityMembership.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    # --- Memberships ---

    async def get_membership(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CommunityMembership]:
        stmt = (
            select(CommunityMembership)
            .where(
                CommunityMembership.community_id == community_id,
                CommunityMembership.user_id == user_id,
            )
            .options(selectinload(CommunityMembership.user).selectinload(User.profile))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> CommunityMembership:
        membership = CommunityMembership(
            community_id=community_id,
            user_id=user_id,
            role=role,
        )
        db.add(membership)

        community = (await db.execute(select(Community).where(Community.id == community_id))).scalar_one_or_none()
        if community:
            community.member_count += 1
            db.add(community)

        await db.commit()
        await db.refresh(membership)
        return membership

    async def remove_member(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        membership = await self.get_membership(db, community_id, user_id)
        if not membership:
            return False

        await db.delete(membership)

        community = (await db.execute(select(Community).where(Community.id == community_id))).scalar_one_or_none()
        if community:
            community.member_count = max(0, community.member_count - 1)
            db.add(community)

        await db.commit()
        return True

    async def get_members(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[CommunityMembership], int]:
        count_stmt = select(func.count(CommunityMembership.id)).where(CommunityMembership.community_id == community_id)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(CommunityMembership)
            .where(CommunityMembership.community_id == community_id)
            .options(selectinload(CommunityMembership.user).selectinload(User.profile))
            .order_by(CommunityMembership.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    # --- Join Requests ---

    async def get_join_request(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CommunityJoinRequest]:
        stmt = (
            select(CommunityJoinRequest)
            .where(
                CommunityJoinRequest.community_id == community_id,
                CommunityJoinRequest.user_id == user_id,
            )
            .options(selectinload(CommunityJoinRequest.user).selectinload(User.profile))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_join_request_by_id(
        self,
        db: AsyncSession,
        request_id: uuid.UUID,
    ) -> Optional[CommunityJoinRequest]:
        stmt = (
            select(CommunityJoinRequest)
            .where(CommunityJoinRequest.id == request_id)
            .options(
                selectinload(CommunityJoinRequest.community),
                selectinload(CommunityJoinRequest.user).selectinload(User.profile),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_join_request(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CommunityJoinRequest:
        request = CommunityJoinRequest(
            community_id=community_id,
            user_id=user_id,
            status="pending",
        )
        db.add(request)
        await db.commit()
        await db.refresh(request)
        return request

    async def delete_join_request(
        self,
        db: AsyncSession,
        request: CommunityJoinRequest,
    ) -> None:
        await db.delete(request)
        await db.commit()

    async def get_pending_requests(
        self,
        db: AsyncSession,
        community_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[CommunityJoinRequest], int]:
        count_stmt = select(func.count(CommunityJoinRequest.id)).where(
            CommunityJoinRequest.community_id == community_id,
            CommunityJoinRequest.status == "pending",
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(CommunityJoinRequest)
            .where(
                CommunityJoinRequest.community_id == community_id,
                CommunityJoinRequest.status == "pending",
            )
            .options(selectinload(CommunityJoinRequest.user).selectinload(User.profile))
            .order_by(CommunityJoinRequest.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total


community_repository = CommunityRepository()
