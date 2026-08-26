from sqlalchemy.ext.asyncio import AsyncSession

from app.feeds.repository import FeedRepository, feed_repository
from app.posts.schemas import PaginatedPostsResponse
from app.posts.service import map_post_to_response
from app.users.models import User


class FeedService:
    """Service handling multi-stream feed generation, personalization, and ranking."""

    def __init__(self, repo: FeedRepository = feed_repository):
        self.repo = repo

    async def get_home_feed(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostsResponse:
        posts, total = await self.repo.get_home_feed(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [map_post_to_response(p) for p in posts]
        return PaginatedPostsResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def get_discover_feed(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostsResponse:
        posts, total = await self.repo.get_discover_feed(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [map_post_to_response(p) for p in posts]
        return PaginatedPostsResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def get_shorts_feed(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostsResponse:
        posts, total = await self.repo.get_shorts_feed(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [map_post_to_response(p) for p in posts]
        return PaginatedPostsResponse(
            items=items, total=total, limit=limit, offset=offset
        )


feed_service = FeedService()
