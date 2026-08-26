from typing import Optional, Union
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_superuser, get_current_active_user
from app.core.database import get_db
from app.core.exceptions import BadRequestException
from app.search.schemas import (
    PaginatedCommunitySearchResponse,
    PaginatedInterestSearchResponse,
    PaginatedPostSearchResponse,
    PaginatedUserSearchResponse,
    SyncIndexResponse,
    UnifiedSearchResponse,
)
from app.search.service import SearchService, search_service
from app.users.models import User

router = APIRouter(prefix="/search", tags=["Search Engine"])


@router.get(
    "",
    response_model=Union[
        UnifiedSearchResponse,
        PaginatedUserSearchResponse,
        PaginatedCommunitySearchResponse,
        PaginatedPostSearchResponse,
        PaginatedInterestSearchResponse,
    ],
    status_code=status.HTTP_200_OK,
    summary="Global multi-entity search",
    description="Search across Users, Communities, Posts, and Interests with Meilisearch and database fallback.",
)
async def search_all(
    q: str = Query(..., min_length=1, description="Search keyword or query"),
    type: str = Query(
        "all",
        description="Filter domain: all, users, communities, posts, interests",
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user),
    service: SearchService = Depends(lambda: search_service),
):
    clean_type = type.lower().strip()
    if clean_type == "all":
        return await service.search_unified(
            db, current_user, query=q, limit=limit, offset=offset
        )
    elif clean_type == "users":
        return await service.search_users(
            db, current_user, query=q, limit=limit, offset=offset
        )
    elif clean_type == "communities":
        return await service.search_communities(
            db, current_user, query=q, limit=limit, offset=offset
        )
    elif clean_type == "posts":
        return await service.search_posts(
            db, current_user, query=q, limit=limit, offset=offset
        )
    elif clean_type == "interests":
        return await service.search_interests(
            db, current_user, query=q, limit=limit, offset=offset
        )
    else:
        raise BadRequestException(
            f"Invalid search type '{type}'. Allowed: all, users, communities, posts, interests"
        )


@router.get(
    "/users",
    response_model=PaginatedUserSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search users",
    description="Search platform users by username, display name, or bio.",
)
async def search_users(
    q: str = Query(..., min_length=1, description="Search keyword"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user),
    service: SearchService = Depends(lambda: search_service),
) -> PaginatedUserSearchResponse:
    return await service.search_users(
        db, current_user, query=q, limit=limit, offset=offset
    )


@router.get(
    "/communities",
    response_model=PaginatedCommunitySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search communities",
    description="Search communities by name, slug, or description.",
)
async def search_communities(
    q: str = Query(..., min_length=1, description="Search keyword"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user),
    service: SearchService = Depends(lambda: search_service),
) -> PaginatedCommunitySearchResponse:
    return await service.search_communities(
        db, current_user, query=q, limit=limit, offset=offset
    )


@router.get(
    "/posts",
    response_model=PaginatedPostSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search posts",
    description="Search posts by title or text body.",
)
async def search_posts(
    q: str = Query(..., min_length=1, description="Search keyword"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user),
    service: SearchService = Depends(lambda: search_service),
) -> PaginatedPostSearchResponse:
    return await service.search_posts(
        db, current_user, query=q, limit=limit, offset=offset
    )


@router.get(
    "/interests",
    response_model=PaginatedInterestSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search interests",
    description="Search predefined master interests taxonomy.",
)
async def search_interests(
    q: str = Query(..., min_length=1, description="Search keyword"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user),
    service: SearchService = Depends(lambda: search_service),
) -> PaginatedInterestSearchResponse:
    return await service.search_interests(
        db, current_user, query=q, limit=limit, offset=offset
    )


@router.post(
    "/sync",
    response_model=SyncIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-sync search indexes (Admin only)",
    description="Trigger full database extraction and synchronization to Meilisearch indexes.",
)
async def sync_indexes(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
    service: SearchService = Depends(lambda: search_service),
) -> SyncIndexResponse:
    return await service.sync_all_indexes(db)
