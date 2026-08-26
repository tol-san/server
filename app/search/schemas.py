import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class UserSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    follower_count: int = 0


class CommunitySearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_private: bool = False
    member_count: int = 0
    post_count: int = 0


class PostSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: Optional[str] = None
    content: Optional[str] = None
    post_type: str
    visibility: str
    author_id: Optional[uuid.UUID] = None
    author_username: Optional[str] = None
    community_id: Optional[uuid.UUID] = None
    community_name: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    created_at: Optional[datetime] = None


class InterestSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None


class UnifiedSearchResponse(BaseModel):
    query: str
    users: List[UserSearchResult] = []
    communities: List[CommunitySearchResult] = []
    posts: List[PostSearchResult] = []
    interests: List[InterestSearchResult] = []
    total_results: int = 0


class PaginatedUserSearchResponse(BaseModel):
    items: List[UserSearchResult]
    total: int
    limit: int
    offset: int


class PaginatedCommunitySearchResponse(BaseModel):
    items: List[CommunitySearchResult]
    total: int
    limit: int
    offset: int


class PaginatedPostSearchResponse(BaseModel):
    items: List[PostSearchResult]
    total: int
    limit: int
    offset: int


class PaginatedInterestSearchResponse(BaseModel):
    items: List[InterestSearchResult]
    total: int
    limit: int
    offset: int


class SyncIndexResponse(BaseModel):
    synced_users: int
    synced_communities: int
    synced_posts: int
    synced_interests: int
    message: str
