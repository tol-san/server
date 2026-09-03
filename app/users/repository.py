import uuid
from typing import Optional, Sequence, Tuple
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.users.models import Block, Follow, Profile, User, UserPrivacySettings


class UserRepository:
    """Repository handling database operations for User, Profile, Follow, and Block entities."""

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id).options(selectinload(User.profile))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.email) == email.lower().strip()).options(selectinload(User.profile))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.username) == username.lower().strip()).options(selectinload(User.profile))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, db: AsyncSession, identifier: str) -> Optional[User]:
        clean_identifier = identifier.strip().lower()
        stmt = (
            select(User)
            .where(
                or_(
                    func.lower(User.email) == clean_identifier,
                    func.lower(User.username) == clean_identifier,
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
        avatar_url: Optional[str] = None,
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

        default_avatar = avatar_url or f"https://api.dicebear.com/7.x/croodles/png?seed={username.strip()}"

        profile = Profile(
            user_id=user.id,
            display_name=display_name.strip() if display_name else user.username,
            avatar_url=default_avatar,
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
        user.token_version += 1
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

    # --- Follow Operations ---

    async def is_following(self, db: AsyncSession, follower_id: uuid.UUID, following_id: uuid.UUID) -> bool:
        stmt = select(Follow.id).where(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def follow_user(self, db: AsyncSession, follower_id: uuid.UUID, following_id: uuid.UUID) -> bool:
        # Check if already following
        stmt = select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return False  # Already following

        follow = Follow(follower_id=follower_id, following_id=following_id)
        db.add(follow)

        # Update follower's following_count
        await db.execute(
            update(Profile)
            .where(Profile.user_id == follower_id)
            .values(following_count=Profile.following_count + 1)
        )

        # Update following's follower_count
        await db.execute(
            update(Profile)
            .where(Profile.user_id == following_id)
            .values(follower_count=Profile.follower_count + 1)
        )

        await db.commit()
        return True

    async def unfollow_user(self, db: AsyncSession, follower_id: uuid.UUID, following_id: uuid.UUID) -> bool:
        stmt = select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
        follow = (await db.execute(stmt)).scalar_one_or_none()
        if not follow:
            return False  # Not following

        await db.delete(follow)

        # Update follower's following_count
        await db.execute(
            update(Profile)
            .where(Profile.user_id == follower_id)
            .values(following_count=case((Profile.following_count > 0, Profile.following_count - 1), else_=0))
        )

        # Update following's follower_count
        await db.execute(
            update(Profile)
            .where(Profile.user_id == following_id)
            .values(follower_count=case((Profile.follower_count > 0, Profile.follower_count - 1), else_=0))
        )

        await db.commit()
        return True

    async def get_followers(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[User], int]:
        count_stmt = select(func.count(Follow.id)).where(Follow.following_id == user_id)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(User)
            .join(Follow, Follow.follower_id == User.id)
            .where(Follow.following_id == user_id)
            .options(selectinload(User.profile))
            .order_by(Follow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def get_following(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[User], int]:
        count_stmt = select(func.count(Follow.id)).where(Follow.follower_id == user_id)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(User)
            .join(Follow, Follow.following_id == User.id)
            .where(Follow.follower_id == user_id)
            .options(selectinload(User.profile))
            .order_by(Follow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    # --- Block Operations ---

    async def is_blocking(self, db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        stmt = select(Block.id).where(
            Block.blocker_id == blocker_id,
            Block.blocked_id == blocked_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def is_blocked_bidirectional(self, db: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
        stmt = select(Block.id).where(
            or_(
                (Block.blocker_id == user_a) & (Block.blocked_id == user_b),
                (Block.blocker_id == user_b) & (Block.blocked_id == user_a),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def block_user(self, db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        # Check if already blocking
        stmt = select(Block).where(
            Block.blocker_id == blocker_id,
            Block.blocked_id == blocked_id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return False  # Already blocked

        block = Block(blocker_id=blocker_id, blocked_id=blocked_id)
        db.add(block)

        # Sever follow: blocker -> blocked (if exists)
        follow1 = (await db.execute(
            select(Follow).where(Follow.follower_id == blocker_id, Follow.following_id == blocked_id)
        )).scalar_one_or_none()
        if follow1:
            await db.delete(follow1)
            await db.execute(
                update(Profile)
                .where(Profile.user_id == blocker_id)
                .values(following_count=case((Profile.following_count > 0, Profile.following_count - 1), else_=0))
            )
            await db.execute(
                update(Profile)
                .where(Profile.user_id == blocked_id)
                .values(follower_count=case((Profile.follower_count > 0, Profile.follower_count - 1), else_=0))
            )

        # Sever follow: blocked -> blocker (if exists)
        follow2 = (await db.execute(
            select(Follow).where(Follow.follower_id == blocked_id, Follow.following_id == blocker_id)
        )).scalar_one_or_none()
        if follow2:
            await db.delete(follow2)
            await db.execute(
                update(Profile)
                .where(Profile.user_id == blocked_id)
                .values(following_count=case((Profile.following_count > 0, Profile.following_count - 1), else_=0))
            )
            await db.execute(
                update(Profile)
                .where(Profile.user_id == blocker_id)
                .values(follower_count=case((Profile.follower_count > 0, Profile.follower_count - 1), else_=0))
            )

        await db.commit()
        return True

    async def unblock_user(self, db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
        stmt = select(Block).where(
            Block.blocker_id == blocker_id,
            Block.blocked_id == blocked_id,
        )
        block = (await db.execute(stmt)).scalar_one_or_none()
        if not block:
            return False  # Not blocked

        await db.delete(block)
        await db.commit()
        return True

    async def get_blocked_users(
        self,
        db: AsyncSession,
        blocker_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[User], int]:
        count_stmt = select(func.count(Block.id)).where(Block.blocker_id == blocker_id)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(User)
            .join(Block, Block.blocked_id == User.id)
            .where(Block.blocker_id == blocker_id)
            .options(selectinload(User.profile))
            .order_by(Block.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def get_or_create_privacy(self, db: AsyncSession, user_id: uuid.UUID) -> UserPrivacySettings:
        stmt = select(UserPrivacySettings).where(UserPrivacySettings.user_id == user_id)
        result = await db.execute(stmt)
        privacy = result.scalar_one_or_none()
        if not privacy:
            privacy = UserPrivacySettings(user_id=user_id)
            db.add(privacy)
            await db.commit()
            await db.refresh(privacy)
        return privacy

    async def update_privacy(self, db: AsyncSession, user_id: uuid.UUID, **kwargs) -> UserPrivacySettings:
        privacy = await self.get_or_create_privacy(db, user_id)
        for key, value in kwargs.items():
            if value is not None and hasattr(privacy, key):
                setattr(privacy, key, value)
        await db.commit()
        await db.refresh(privacy)
        return privacy

    async def get_owned_communities_with_members(self, db: AsyncSession, user_id: uuid.UUID) -> Sequence:
        from app.communities.models import Community
        stmt = select(Community).where(Community.owner_id == user_id, Community.member_count > 1)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_user_hard(self, db: AsyncSession, user: User) -> None:
        from app.auth.models import UserSession
        from app.notifications.models import NotificationPreferences
        from sqlalchemy import delete
        await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
        await db.execute(delete(NotificationPreferences).where(NotificationPreferences.user_id == user.id))
        await db.delete(user)
        await db.commit()



user_repository = UserRepository()

