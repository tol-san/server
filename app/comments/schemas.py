import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommentAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Comment text content")
    parent_id: Optional[uuid.UUID] = Field(None, description="Parent comment UUID if creating a reply")


class CommentUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Updated comment text content")


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    author: CommentAuthorResponse
    content: str
    like_count: int = 0
    reply_count: int = 0
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime


class PaginatedCommentsResponse(BaseModel):
    items: List[CommentResponse]
    total: int
    limit: int
    offset: int
