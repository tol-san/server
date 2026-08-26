import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InterestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    icon_url: Optional[str] = None
    description: Optional[str] = None


class InterestCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Name of the interest category")
    slug: Optional[str] = Field(None, min_length=2, max_length=50, description="URL-friendly slug (auto-generated if omitted)")
    icon_url: Optional[str] = Field(None, max_length=500, description="Icon or badge URL")
    description: Optional[str] = Field(None, max_length=255, description="Short description of the interest category")


class UserInterestsUpdateRequest(BaseModel):
    interest_ids: List[uuid.UUID] = Field(
        ...,
        max_length=20,
        description="List of selected interest UUIDs (max 20)",
    )


class UserInterestsResponse(BaseModel):
    items: List[InterestResponse]
    total: int
