"""Posts module containing Post and PostMedia models, schemas, services, and routers."""

from app.posts.models import Post, PostMedia
from app.posts.repository import PostRepository, post_repository
from app.posts.router import router as posts_router
from app.posts.schemas import (
    MediaItemCreate,
    MediaItemResponse,
    MediaUploadResponse,
    PaginatedPostsResponse,
    PostAuthorResponse,
    PostCommunityResponse,
    PostCreateRequest,
    PostResponse,
    PostUpdateRequest,
)
from app.posts.service import PostService, post_service

__all__ = [
    "Post",
    "PostMedia",
    "PostRepository",
    "post_repository",
    "PostService",
    "post_service",
    "MediaItemCreate",
    "MediaItemResponse",
    "PostCreateRequest",
    "PostUpdateRequest",
    "PostAuthorResponse",
    "PostCommunityResponse",
    "PostResponse",
    "PaginatedPostsResponse",
    "MediaUploadResponse",
    "posts_router",
]
