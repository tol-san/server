"""Posts module containing Post and PostMedia models, schemas, services, and routers."""

from app.posts.models import Post, PostLike, PostMedia, SavedPost
from app.posts.repository import PostRepository, post_repository
from app.posts.router import router as posts_router
from app.posts.schemas import (
    MediaItemCreate,
    MediaItemResponse,
    MediaUploadResponse,
    PaginatedPostsResponse,
    PaginatedSavedPostsResponse,
    PostAuthorResponse,
    PostCommunityResponse,
    PostCreateRequest,
    PostLikeResponse,
    PostResponse,
    PostSaveResponse,
    PostShareResponse,
    PostUpdateRequest,
)
from app.posts.service import PostService, post_service

__all__ = [
    "Post",
    "PostMedia",
    "PostLike",
    "SavedPost",
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
    "PostLikeResponse",
    "PostSaveResponse",
    "PostShareResponse",
    "PaginatedPostsResponse",
    "PaginatedSavedPostsResponse",
    "MediaUploadResponse",
    "posts_router",
]
