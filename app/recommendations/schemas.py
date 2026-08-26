import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class RecommendedCommunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    is_private: bool
    member_count: int
    post_count: int
    interest_id: Optional[uuid.UUID] = None
    interest_name: Optional[str] = None
    is_matched_interest: bool = False


class PaginatedRecommendedCommunitiesResponse(BaseModel):
    items: List[RecommendedCommunityResponse]
    total: int
    limit: int
    offset: int


class RecommendedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    follower_count: int = 0
    mutual_interest_count: int = 0
    shared_interests: List[str] = []


class PaginatedRecommendedUsersResponse(BaseModel):
    items: List[RecommendedUserResponse]
    total: int
    limit: int
    offset: int
