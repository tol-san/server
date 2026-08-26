import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.posts.schemas import PaginatedSavedPostsResponse
from app.posts.service import PostService, post_service
from app.users.models import User

router = APIRouter(prefix="/saved-posts", tags=["Saved Posts (Bookmarks)"])


@router.get(
    "",
    response_model=PaginatedSavedPostsResponse,
    status_code=status.HTTP_200_OK,
    summary="List saved posts (bookmarks)",
    description="Retrieve paginated list of posts bookmarked/saved by the authenticated user in descending order of save time.",
)
async def list_saved_posts(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PaginatedSavedPostsResponse:
    return await service.list_saved_posts(
        db, current_user=current_user, limit=limit, offset=offset
    )
