import uuid
from typing import Optional, Sequence, Union
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.interests.models import Interest, UserInterest


class InterestRepository:
    """Repository handling database operations for Interest and UserInterest entities."""

    async def get_all(self, db: AsyncSession) -> Sequence[Interest]:
        stmt = select(Interest).order_by(Interest.name.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, interest_id: uuid.UUID) -> Optional[Interest]:
        stmt = select(Interest).where(Interest.id == interest_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, db: AsyncSession, interest_ids: Sequence[uuid.UUID]) -> Sequence[Interest]:
        if not interest_ids:
            return []
        stmt = select(Interest).where(Interest.id.in_(interest_ids))
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_slugs_or_ids(
        self, db: AsyncSession, identifiers: Sequence[Union[uuid.UUID, str]]
    ) -> Sequence[Interest]:
        if not identifiers:
            return []

        uuid_list = []
        slug_list = []
        for item in identifiers:
            if isinstance(item, uuid.UUID):
                uuid_list.append(item)
            else:
                s = str(item).strip()
                try:
                    uuid_list.append(uuid.UUID(s))
                except ValueError:
                    slug_list.append(s.lower())

        conditions = []
        if uuid_list:
            conditions.append(Interest.id.in_(uuid_list))
        if slug_list:
            conditions.append(func.lower(Interest.slug).in_(slug_list))
            conditions.append(func.lower(Interest.name).in_(slug_list))

        if not conditions:
            return []

        stmt = select(Interest).where(or_(*conditions))
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Interest]:
        stmt = select(Interest).where(func.lower(Interest.name) == name.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[Interest]:
        stmt = select(Interest).where(Interest.slug == slug.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        name: str,
        slug: str,
        icon_url: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Interest:
        interest = Interest(
            name=name.strip(),
            slug=slug.lower().strip(),
            icon_url=icon_url.strip() if icon_url else None,
            description=description.strip() if description else None,
        )
        db.add(interest)
        await db.commit()
        await db.refresh(interest)
        return interest

    async def get_user_interests(self, db: AsyncSession, user_id: uuid.UUID) -> Sequence[Interest]:
        stmt = (
            select(Interest)
            .join(UserInterest, UserInterest.interest_id == Interest.id)
            .where(UserInterest.user_id == user_id)
            .order_by(Interest.name.asc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def set_user_interests(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        interest_ids: Sequence[uuid.UUID],
    ) -> Sequence[Interest]:
        # 1. Delete existing user interests
        delete_stmt = delete(UserInterest).where(UserInterest.user_id == user_id)
        await db.execute(delete_stmt)

        # 2. Add new unique user interests
        unique_ids = list(dict.fromkeys(interest_ids))
        for interest_id in unique_ids:
            db.add(UserInterest(user_id=user_id, interest_id=interest_id))

        await db.commit()

        # 3. Return updated list of interests
        return await self.get_user_interests(db, user_id)


interest_repository = InterestRepository()
