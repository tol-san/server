import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.users.models import User
from app.users.repository import UserRepository, user_repository
from app.users.schemas import (
    BlockActionResponse,
    FollowActionResponse,
    PaginatedUsersResponse,
    RelationshipResponse,
    UserItemResponse,
    UserPublicResponse,
)


class UserService:
    """Service handling user-related queries, follows, and blocking operations."""

    def __init__(self, user_repo: UserRepository = user_repository):
        self.user_repo = user_repo

    async def get_public_profile(
        self,
        db: AsyncSession,
        username: str,
    ) -> UserPublicResponse:
        user = await self.user_repo.get_by_username(db, username)
        if not user or not user.is_active:
            raise NotFoundException(f"User '{username}' not found.")

        profile = user.profile
        return UserPublicResponse(
            id=user.id,
            username=user.username,
            display_name=profile.display_name if profile and profile.display_name else user.username,
            bio=profile.bio if profile else None,
            avatar_url=profile.avatar_url if profile else None,
            follower_count=profile.follower_count if profile else 0,
            following_count=profile.following_count if profile else 0,
            post_count=profile.post_count if profile else 0,
            created_at=user.created_at,
        )

    async def follow_user(
        self,
        db: AsyncSession,
        current_user: User,
        target_user_id: uuid.UUID,
    ) -> FollowActionResponse:
        if current_user.id == target_user_id:
            raise BadRequestException("You cannot follow yourself.")

        target_user = await self.user_repo.get_by_id(db, target_user_id)
        if not target_user or not target_user.is_active:
            raise NotFoundException("User not found.")

        # Check block restrictions
        if await self.user_repo.is_blocked_bidirectional(db, current_user.id, target_user_id):
            raise ForbiddenException("Cannot follow this user.")

        await self.user_repo.follow_user(db, current_user.id, target_user_id)

        from app.notifications.service import notification_service
        await notification_service.notify_user(
            db,
            recipient_id=target_user_id,
            actor_id=current_user.id,
            notification_type="new_follower",
            title="New Follower",
            message=f"{current_user.username} started following you.",
            entity_type="user",
            entity_id=current_user.id,
        )

        return FollowActionResponse(
            is_following=True,
            message=f"You are now following {target_user.username}.",
        )

    async def unfollow_user(
        self,
        db: AsyncSession,
        current_user: User,
        target_user_id: uuid.UUID,
    ) -> FollowActionResponse:
        if current_user.id == target_user_id:
            raise BadRequestException("You cannot unfollow yourself.")

        target_user = await self.user_repo.get_by_id(db, target_user_id)
        if not target_user or not target_user.is_active:
            raise NotFoundException("User not found.")

        await self.user_repo.unfollow_user(db, current_user.id, target_user_id)
        return FollowActionResponse(
            is_following=False,
            message=f"You have unfollowed {target_user.username}.",
        )

    async def block_user(
        self,
        db: AsyncSession,
        current_user: User,
        target_user_id: uuid.UUID,
    ) -> BlockActionResponse:
        if current_user.id == target_user_id:
            raise BadRequestException("You cannot block yourself.")

        target_user = await self.user_repo.get_by_id(db, target_user_id)
        if not target_user:
            raise NotFoundException("User not found.")

        await self.user_repo.block_user(db, current_user.id, target_user_id)
        return BlockActionResponse(
            is_blocking=True,
            message=f"You have blocked {target_user.username}.",
        )

    async def unblock_user(
        self,
        db: AsyncSession,
        current_user: User,
        target_user_id: uuid.UUID,
    ) -> BlockActionResponse:
        if current_user.id == target_user_id:
            raise BadRequestException("You cannot unblock yourself.")

        target_user = await self.user_repo.get_by_id(db, target_user_id)
        if not target_user:
            raise NotFoundException("User not found.")

        await self.user_repo.unblock_user(db, current_user.id, target_user_id)
        return BlockActionResponse(
            is_blocking=False,
            message=f"You have unblocked {target_user.username}.",
        )

    async def get_followers(
        self,
        db: AsyncSession,
        target_user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedUsersResponse:
        target_user = await self.user_repo.get_by_id(db, target_user_id)
        if not target_user or not target_user.is_active:
            raise NotFoundException("User not found.")

        users, total = await self.user_repo.get_followers(db, target_user_id, limit, offset)
        items = [
            UserItemResponse(
                id=u.id,
                username=u.username,
                display_name=u.profile.display_name if u.profile else u.username,
                avatar_url=u.profile.avatar_url if u.profile else None,
                bio=u.profile.bio if u.profile else None,
                follower_count=u.profile.follower_count if u.profile else 0,
                following_count=u.profile.following_count if u.profile else 0,
            )
            for u in users
        ]
        return PaginatedUsersResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_following(
        self,
        db: AsyncSession,
        target_user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedUsersResponse:
        target_user = await self.user_repo.get_by_id(db, target_user_id)
        if not target_user or not target_user.is_active:
            raise NotFoundException("User not found.")

        users, total = await self.user_repo.get_following(db, target_user_id, limit, offset)
        items = [
            UserItemResponse(
                id=u.id,
                username=u.username,
                display_name=u.profile.display_name if u.profile else u.username,
                avatar_url=u.profile.avatar_url if u.profile else None,
                bio=u.profile.bio if u.profile else None,
                follower_count=u.profile.follower_count if u.profile else 0,
                following_count=u.profile.following_count if u.profile else 0,
            )
            for u in users
        ]
        return PaginatedUsersResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_relationship(
        self,
        db: AsyncSession,
        current_user: User,
        target_user_id: uuid.UUID,
    ) -> RelationshipResponse:
        if current_user.id == target_user_id:
            return RelationshipResponse(
                is_following=False,
                is_followed_by=False,
                is_blocking=False,
                is_blocked_by=False,
            )

        target_user = await self.user_repo.get_by_id(db, target_user_id)
        if not target_user or not target_user.is_active:
            raise NotFoundException("User not found.")

        is_following = await self.user_repo.is_following(db, current_user.id, target_user_id)
        is_followed_by = await self.user_repo.is_following(db, target_user_id, current_user.id)
        is_blocking = await self.user_repo.is_blocking(db, current_user.id, target_user_id)
        is_blocked_by = await self.user_repo.is_blocking(db, target_user_id, current_user.id)

        return RelationshipResponse(
            is_following=is_following,
            is_followed_by=is_followed_by,
            is_blocking=is_blocking,
            is_blocked_by=is_blocked_by,
        )

    async def get_blocked_users(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedUsersResponse:
        users, total = await self.user_repo.get_blocked_users(db, current_user.id, limit, offset)
        items = [
            UserItemResponse(
                id=u.id,
                username=u.username,
                display_name=u.profile.display_name if u.profile else u.username,
                avatar_url=u.profile.avatar_url if u.profile else None,
                bio=u.profile.bio if u.profile else None,
                follower_count=u.profile.follower_count if u.profile else 0,
                following_count=u.profile.following_count if u.profile else 0,
            )
            for u in users
        ]
        return PaginatedUsersResponse(items=items, total=total, limit=limit, offset=offset)


user_service = UserService()
