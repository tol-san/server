import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user, get_optional_current_user
from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.posts.schemas import (
    MediaUploadResponse,
    PaginatedPostsResponse,
    PostCreateRequest,
    PostLikeResponse,
    PostResponse,
    PostSaveResponse,
    PostShareResponse,
    PostUpdateRequest,
)
from app.posts.service import PostService, post_service
from app.users.models import User

router = APIRouter(prefix="/posts", tags=["Posts & Media"])


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post",
    description="Create a text post, multi-image carousel post, or short video post (Personal or Community).",
)
async def create_post(
    payload: PostCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PostResponse:
    return await service.create_post(db, current_user, payload)


@router.post(
    "/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload post media",
    description="Upload an image (auto-converted to WebP, max 10MB) or short video (MP4/MOV/WebM, max 50MB) to MinIO.",
)
async def upload_post_media(
    file: UploadFile = File(..., description="Image or video file to upload"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> MediaUploadResponse:
    return await service.upload_media(db, current_user, file)


@router.get(
    "",
    response_model=PaginatedPostsResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter posts",
    description="Retrieve posts with optional filtering by author ID, community ID, post type, visibility, or search query.",
)
async def list_posts(
    author_id: Optional[uuid.UUID] = Query(None, description="Filter by author UUID"),
    community_id: Optional[uuid.UUID] = Query(None, description="Filter by community UUID"),
    post_type: Optional[str] = Query(None, description="Filter by post type: text, image, video"),
    visibility: Optional[str] = Query(None, description="Filter by visibility: public, followers_only, private"),
    search: Optional[str] = Query(None, description="Search in post title and content"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    service: PostService = Depends(lambda: post_service),
) -> PaginatedPostsResponse:
    effective_author_id = author_id
    effective_visibility = visibility

    if current_user is None:
        # Anonymous users can only view public posts
        if visibility and visibility != "public":
            raise ForbiddenException("Authentication required to view non-public posts.")
        effective_visibility = "public"
    else:
        # Authenticated users: restrict private posts to their own
        if visibility == "private":
            effective_author_id = current_user.id
        elif visibility == "followers_only" and author_id is None:
            effective_author_id = current_user.id

    return await service.list_posts(
        db,
        author_id=effective_author_id,
        community_id=community_id,
        post_type=post_type,
        visibility=effective_visibility,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single post details",
    description="Retrieve complete post details including author info, community context, media items, and counters.",
)
async def get_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    service: PostService = Depends(lambda: post_service),
) -> PostResponse:
    return await service.get_post(db, post_id)


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
    summary="Update post content",
    description="Update title, content, or visibility for an existing post (Author only).",
)
async def update_post(
    post_id: uuid.UUID,
    payload: PostUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PostResponse:
    return await service.update_post(db, post_id, current_user, payload)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete post",
    description="Delete a post and associated media (Authorized for Author, Community Owner, or Platform Admin).",
)
async def delete_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> dict:
    return await service.delete_post(db, post_id, current_user)


# Engagement Endpoints
@router.post(
    "/{post_id}/like",
    response_model=PostLikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Like a post",
    description="Like a post. Idempotent: liking an already liked post keeps the like and returns current status.",
)
async def like_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PostLikeResponse:
    return await service.like_post(db, post_id, current_user)


@router.delete(
    "/{post_id}/like",
    response_model=PostLikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Unlike a post",
    description="Remove like from a post. Idempotent: unliking a non-liked post returns current status.",
)
async def unlike_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PostLikeResponse:
    return await service.unlike_post(db, post_id, current_user)


@router.post(
    "/{post_id}/save",
    response_model=PostSaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Save/bookmark a post",
    description="Save a post to personal collection. Idempotent: saving an already saved post keeps the bookmark.",
)
async def save_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PostSaveResponse:
    return await service.save_post(db, post_id, current_user)


@router.delete(
    "/{post_id}/save",
    response_model=PostSaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Unsave/remove bookmark from a post",
    description="Remove post from saved bookmarks collection. Idempotent.",
)
async def unsave_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PostSaveResponse:
    return await service.unsave_post(db, post_id, current_user)


@router.post(
    "/{post_id}/share",
    response_model=PostShareResponse,
    status_code=status.HTTP_200_OK,
    summary="Share a post",
    description="Increment share counter and return shareable link for a post.",
)
async def share_post(
    post_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: PostService = Depends(lambda: post_service),
) -> PostShareResponse:
    return await service.share_post(db, post_id, current_user)

