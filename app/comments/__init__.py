"""Comments module containing Comment model, schemas, service, and routers."""

from app.comments.models import Comment
from app.comments.repository import CommentRepository, comment_repository
from app.comments.router import router as comments_router
from app.comments.schemas import (
    CommentAuthorResponse,
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    PaginatedCommentsResponse,
)
from app.comments.service import CommentService, comment_service

__all__ = [
    "Comment",
    "CommentRepository",
    "comment_repository",
    "CommentService",
    "comment_service",
    "CommentCreateRequest",
    "CommentUpdateRequest",
    "CommentResponse",
    "CommentAuthorResponse",
    "PaginatedCommentsResponse",
    "comments_router",
]
