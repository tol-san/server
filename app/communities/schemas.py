import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommunityCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Community name")
    slug: Optional[str] = Field(None, min_length=2, max_length=100, description="Unique slug for URLs")
    description: Optional[str] = Field(None, max_length=1000, description="Community purpose and description")
    interest_id: Optional[uuid.UUID] = Field(None, description="Associated interest category UUID")
    cover_image_url: Optional[str] = Field(None, max_length=500, description="Cover banner image URL")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Community icon or avatar URL")
    is_private: bool = Field(False, description="Whether community requires approval to join")


class CommunityUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    interest_id: Optional[uuid.UUID] = None
    cover_image_url: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_private: Optional[bool] = None


class CommunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    interest_id: Optional[uuid.UUID] = None
    name: str
    slug: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    avatar_url: Optional[str] = None
    is_private: bool
    member_count: int
    post_count: int
    created_at: datetime


class CommunityDetailResponse(CommunityResponse):
    is_member: bool = False
    is_owner: bool = False
    membership_role: Optional[str] = None
    join_request_status: Optional[str] = None


class PaginatedCommunitiesResponse(BaseModel):
    items: List[CommunityResponse]
    total: int
    limit: int
    offset: int


class CommunityMemberItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    joined_at: datetime


class PaginatedMembersResponse(BaseModel):
    items: List[CommunityMemberItem]
    total: int
    limit: int
    offset: int


class JoinRequestItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str
    created_at: datetime


class PaginatedJoinRequestsResponse(BaseModel):
    items: List[JoinRequestItem]
    total: int
    limit: int
    offset: int


class JoinActionResponse(BaseModel):
    status: str
    message: str
    is_member: bool
