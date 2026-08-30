import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MediaItemCreate(BaseModel):
    media_type: str = Field(..., description="Media type: image or video")
    url: str = Field(..., max_length=500, description="Media asset URL")
    thumbnail_url: Optional[str] = Field(None, max_length=500, description="Video thumbnail URL")
    duration: Optional[float] = Field(None, description="Video duration in seconds")
    width: Optional[int] = Field(None, description="Media pixel width")
    height: Optional[int] = Field(None, description="Media pixel height")
    order: int = Field(0, description="Display order index for carousel")


class MediaItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_type: str
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    order: int


class PostCreateRequest(BaseModel):
    post_type: str = Field("text", description="Type of post: text, image, video")
    title: Optional[str] = Field(None, max_length=255, description="Title for articles or text posts")
    content: Optional[str] = Field(None, description="Body content, markdown, or caption")
    visibility: str = Field("public", description="Visibility: public, followers_only, private")
    community_id: Optional[uuid.UUID] = Field(None, description="Community UUID if posting to a community")
    media: Optional[List[MediaItemCreate]] = Field(None, description="List of media items for image/video posts")


class PostUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    visibility: Optional[str] = None


class PostAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class PostCommunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    avatar_url: Optional[str] = None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author: PostAuthorResponse
    community: Optional[PostCommunityResponse] = None
    post_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    visibility: str
    media: List[MediaItemResponse] = []
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    save_count: int = 0
    created_at: datetime


class PaginatedPostsResponse(BaseModel):
    items: List[PostResponse]
    total: int
    limit: int
    offset: int


class MediaUploadResponse(BaseModel):
    url: str
    media_type: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None


class PostLikeResponse(BaseModel):
    post_id: uuid.UUID
    liked: bool
    like_count: int


class PostSaveResponse(BaseModel):
    post_id: uuid.UUID
    saved: bool
    save_count: int


class PostShareResponse(BaseModel):
    post_id: uuid.UUID
    share_count: int
    share_url: str


class PaginatedSavedPostsResponse(BaseModel):
    items: List[PostResponse]
    total: int
    limit: int
    offset: int


class ReactorUserResponse(BaseModel):
    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    reaction_type: str = "like"
    mutual_count: int = 0
    is_following: bool = False


class PostReactionsResponse(BaseModel):
    items: List[ReactorUserResponse]
    total: int
    counts: dict
    limit: int
    offset: int
