import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user, get_current_user
from app.communities.schemas import (
    CommunityCreateRequest,
    CommunityDetailResponse,
    CommunityResponse,
    CommunityUpdateRequest,
    JoinActionResponse,
    PaginatedCommunitiesResponse,
    PaginatedJoinRequestsResponse,
    PaginatedMembersResponse,
)
from app.communities.service import CommunityService, community_service
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/communities", tags=["Communities"])


@router.post(
    "",
    response_model=CommunityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a community",
    description="Create a new public or private community. The creator is automatically enrolled as Owner.",
)
async def create_community(
    payload: CommunityCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> CommunityResponse:
    return await service.create_community(db, current_user, payload)


@router.get(
    "",
    response_model=PaginatedCommunitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="Explore communities",
    description="Search and filter communities by name, description, interest category, or privacy mode.",
)
async def list_communities(
    search: Optional[str] = Query(None, description="Search query by name/description"),
    interest_id: Optional[uuid.UUID] = Query(None, description="Filter by interest UUID"),
    is_private: Optional[bool] = Query(None, description="Filter by private/public"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(lambda: community_service),
) -> PaginatedCommunitiesResponse:
    return await service.list_communities(
        db,
        search=search,
        interest_id=interest_id,
        is_private=is_private,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/me/joined",
    response_model=PaginatedCommunitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get my joined communities",
    description="Retrieve all communities the authenticated user is currently a member of.",
)
async def get_my_communities(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> PaginatedCommunitiesResponse:
    return await service.list_my_communities(db, current_user, limit, offset)


@router.get(
    "/{community_id}",
    response_model=CommunityDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get community details",
    description="Retrieve community info, owner details, and authenticated user's membership status.",
)
async def get_community(
    community_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(lambda: community_service),
) -> CommunityDetailResponse:
    return await service.get_community(db, community_id, current_user=None)


@router.patch(
    "/{community_id}",
    response_model=CommunityResponse,
    status_code=status.HTTP_200_OK,
    summary="Update community settings",
    description="Update community name, description, privacy, or interest category (Owner only).",
)
async def update_community(
    community_id: uuid.UUID,
    payload: CommunityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> CommunityResponse:
    return await service.update_community(db, community_id, current_user, payload)


@router.delete(
    "/{community_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete community",
    description="Delete a community and cascade all memberships and posts (Owner only).",
)
async def delete_community(
    community_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> dict:
    return await service.delete_community(db, community_id, current_user)


@router.post(
    "/{community_id}/cover",
    response_model=CommunityResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload community cover banner",
    description="Upload a cover banner image for the community (JPEG/PNG/WebP, max 5MB, Owner only).",
)
async def upload_community_cover(
    community_id: uuid.UUID,
    file: UploadFile = File(..., description="Cover banner image file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> CommunityResponse:
    return await service.upload_cover_image(db, community_id, current_user, file)


@router.post(
    "/{community_id}/join",
    response_model=JoinActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Join community or submit request",
    description="Instantly join a public community, or submit a join request for a private community.",
)
async def join_community(
    community_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> JoinActionResponse:
    return await service.join_community(db, community_id, current_user)


@router.delete(
    "/{community_id}/leave",
    status_code=status.HTTP_200_OK,
    summary="Leave community",
    description="Leave a joined community (Owner cannot leave without transferring ownership).",
)
async def leave_community(
    community_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> dict:
    return await service.leave_community(db, community_id, current_user)


@router.get(
    "/{community_id}/members",
    response_model=PaginatedMembersResponse,
    status_code=status.HTTP_200_OK,
    summary="List community members",
    description="Retrieve a paginated list of members in the community.",
)
async def list_community_members(
    community_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    service: CommunityService = Depends(lambda: community_service),
) -> PaginatedMembersResponse:
    return await service.list_members(db, community_id, limit, offset)


@router.delete(
    "/{community_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Kick community member",
    description="Remove a member from the community (Owner only).",
)
async def kick_community_member(
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> dict:
    return await service.kick_member(db, community_id, current_user, user_id)


@router.get(
    "/{community_id}/join-requests",
    response_model=PaginatedJoinRequestsResponse,
    status_code=status.HTTP_200_OK,
    summary="List join requests",
    description="Retrieve a paginated list of pending join requests for a private community (Owner only).",
)
async def list_join_requests(
    community_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> PaginatedJoinRequestsResponse:
    return await service.list_join_requests(db, community_id, current_user, limit, offset)


@router.post(
    "/{community_id}/join-requests/{request_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve join request",
    description="Approve a user's join request and grant community membership (Owner only).",
)
async def approve_join_request(
    community_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> dict:
    return await service.approve_join_request(db, community_id, request_id, current_user)


@router.post(
    "/{community_id}/join-requests/{request_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject join request",
    description="Reject a user's join request (Owner only).",
)
async def reject_join_request(
    community_id: uuid.UUID,
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommunityService = Depends(lambda: community_service),
) -> dict:
    return await service.reject_join_request(db, community_id, request_id, current_user)
