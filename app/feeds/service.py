import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.feeds.repository import FeedRepository, feed_repository
from app.posts.schemas import PaginatedPostsResponse, PostResponse
from app.posts.service import map_post_to_response
from app.users.models import User


class FeedService:
    """Service handling multi-stream feed generation, personalization, ranking, and Redis caching."""

    def __init__(self, repo: FeedRepository = feed_repository):
        self.repo = repo

    async def get_home_feed(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostsResponse:
        cache_key = f"cache:feed:home:{current_user.id}:{limit}:{offset}"
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return PaginatedPostsResponse.model_validate(cached_data)

        posts, total = await self.repo.get_home_feed(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [map_post_to_response(p) for p in posts]
        resp = PaginatedPostsResponse(
            items=items, total=total, limit=limit, offset=offset
        )

        await cache_service.set(cache_key, resp.model_dump(mode="json"), ttl=60)
        return resp

    async def get_discover_feed(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostsResponse:
        cache_key = f"cache:feed:discover:{limit}:{offset}"
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return PaginatedPostsResponse.model_validate(cached_data)

        posts, total = await self.repo.get_discover_feed(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [map_post_to_response(p) for p in posts]
        resp = PaginatedPostsResponse(
            items=items, total=total, limit=limit, offset=offset
        )

        await cache_service.set(cache_key, resp.model_dump(mode="json"), ttl=120)
        return resp

    async def get_shorts_feed(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostsResponse:
        cache_key = f"cache:feed:shorts:{current_user.id}:{limit}:{offset}"
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return PaginatedPostsResponse.model_validate(cached_data)

        posts, total = await self.repo.get_shorts_feed(
            db, user_id=current_user.id, limit=limit, offset=offset
        )
        items = [map_post_to_response(p) for p in posts]
        resp = PaginatedPostsResponse(
            items=items, total=total, limit=limit, offset=offset
        )

        await cache_service.set(cache_key, resp.model_dump(mode="json"), ttl=180)
        return resp

    async def invalidate_user_feeds(self, user_id: uuid.UUID) -> None:
        """Invalidate timeline and shorts cache for a specific user."""
        await cache_service.delete_pattern(f"cache:feed:home:{user_id}:*")
        await cache_service.delete_pattern(f"cache:feed:shorts:{user_id}:*")

    async def invalidate_global_feeds(self) -> None:
        """Invalidate discover/trending feeds when new public content appears."""
        await cache_service.delete_pattern("cache:feed:discover:*")


feed_service = FeedService()

