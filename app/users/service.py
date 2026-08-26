from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.users.repository import UserRepository, user_repository
from app.users.schemas import UserPublicResponse


class UserService:
    """Service handling user-related queries and operations."""

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


user_service = UserService()
