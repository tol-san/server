import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.comments.schemas import (
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    PaginatedCommentsResponse,
)
from app.comments.service import CommentService, comment_service
from app.core.database import get_db
from app.users.models import User

router = APIRouter(tags=["Discussions & Comments"])


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create comment or reply",
    description="Create a top-level comment or nested reply on a post.",
)
async def create_comment(
    post_id: uuid.UUID,
    payload: CommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommentService = Depends(lambda: comment_service),
) -> CommentResponse:
    return await service.create_comment(db, post_id, current_user, payload)


@router.get(
    "/posts/{post_id}/comments",
    response_model=PaginatedCommentsResponse,
    status_code=status.HTTP_200_OK,
    summary="List top-level comments on a post",
    description="Retrieve paginated top-level comments for a post.",
)
async def list_post_comments(
    post_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    service: CommentService = Depends(lambda: comment_service),
) -> PaginatedCommentsResponse:
    return await service.list_post_comments(db, post_id, limit, offset)


@router.get(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single comment details",
    description="Retrieve a comment by ID with author details and counters.",
)
async def get_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    service: CommentService = Depends(lambda: comment_service),
) -> CommentResponse:
    return await service.get_comment(db, comment_id)


@router.get(
    "/comments/{comment_id}/replies",
    response_model=PaginatedCommentsResponse,
    status_code=status.HTTP_200_OK,
    summary="List nested replies",
    description="Retrieve paginated nested replies under a parent comment.",
)
async def list_comment_replies(
    comment_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    service: CommentService = Depends(lambda: comment_service),
) -> PaginatedCommentsResponse:
    return await service.list_replies(db, comment_id, limit, offset)


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit comment content",
    description="Update comment content (Author only, marks is_edited=True).",
)
async def update_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommentService = Depends(lambda: comment_service),
) -> CommentResponse:
    return await service.update_comment(db, comment_id, current_user, payload)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete comment",
    description="Delete a comment and child replies (Authorized for: Comment Author, Post Author, Community Owner, Platform Admin).",
)
async def delete_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: CommentService = Depends(lambda: comment_service),
) -> dict:
    return await service.delete_comment(db, comment_id, current_user)
