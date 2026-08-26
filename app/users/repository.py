import uuid
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.users.models import Profile, User


class UserRepository:
    """Repository handling database operations for User and Profile entities."""

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id).options(selectinload(User.profile))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip()).options(selectinload(User.profile))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username.strip()).options(selectinload(User.profile))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, db: AsyncSession, identifier: str) -> Optional[User]:
        clean_identifier = identifier.strip()
        stmt = (
            select(User)
            .where(
                or_(
                    User.email == clean_identifier.lower(),
                    User.username == clean_identifier.lower(),
                )
            )
            .options(selectinload(User.profile))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_with_profile(
        self,
        db: AsyncSession,
        *,
        email: str,
        username: str,
        hashed_password: str,
        display_name: Optional[str] = None,
    ) -> User:
        user = User(
            email=email.lower().strip(),
            username=username.strip(),
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.flush()  # Flush to generate user.id

        profile = Profile(
            user_id=user.id,
            display_name=display_name.strip() if display_name else user.username,
            follower_count=0,
            following_count=0,
            post_count=0,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(user)
        return user

    async def update_password(self, db: AsyncSession, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def update_profile(
        self,
        db: AsyncSession,
        user: User,
        *,
        display_name: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Profile:
        if user.profile is None:
            profile = Profile(
                user_id=user.id,
                display_name=display_name.strip() if display_name is not None else user.username,
                bio=bio.strip() if bio is not None else None,
                avatar_url=avatar_url.strip() if avatar_url is not None else None,
                follower_count=0,
                following_count=0,
                post_count=0,
            )
            db.add(profile)
        else:
            profile = user.profile
            if display_name is not None:
                profile.display_name = display_name.strip()
            if bio is not None:
                profile.bio = bio.strip() if bio else None
            if avatar_url is not None:
                profile.avatar_url = avatar_url.strip() if avatar_url else None
            db.add(profile)

        await db.commit()
        await db.refresh(profile)
        await db.refresh(user)
        return profile


user_repository = UserRepository()
