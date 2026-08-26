from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.feeds.service import FeedService, feed_service
from app.posts.schemas import PaginatedPostsResponse
from app.users.models import User

router = APIRouter(prefix="/feeds", tags=["Feeds & Discovery"])


@router.get(
    "/home",
    response_model=PaginatedPostsResponse,
    status_code=status.HTTP_200_OK,
    summary="Personalized Home Feed",
    description="Retrieve personalized timeline from followed users and joined communities, ranked by recency.",
)
async def get_home_feed(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: FeedService = Depends(lambda: feed_service),
) -> PaginatedPostsResponse:
    return await service.get_home_feed(
        db, current_user=current_user, limit=limit, offset=offset
    )


@router.get(
    "/discover",
    response_model=PaginatedPostsResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Feed",
    description="Retrieve trending and recommended posts across the platform scored by engagement and interest relevance.",
)
async def get_discover_feed(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: FeedService = Depends(lambda: feed_service),
) -> PaginatedPostsResponse:
    return await service.get_discover_feed(
        db, current_user=current_user, limit=limit, offset=offset
    )


@router.get(
    "/shorts",
    response_model=PaginatedPostsResponse,
    status_code=status.HTTP_200_OK,
    summary="Short Video Feed",
    description="Retrieve vertical short video stream scored by engagement, user interest affinity, and recency.",
)
async def get_shorts_feed(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: FeedService = Depends(lambda: feed_service),
) -> PaginatedPostsResponse:
    return await service.get_shorts_feed(
        db, current_user=current_user, limit=limit, offset=offset
    )
