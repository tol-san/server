import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

ALLOWED_REPORT_TYPES = {"user", "post", "comment", "community", "chat_message"}
ALLOWED_REPORT_REASONS = {
    "spam",
    "harassment",
    "inappropriate_content",
    "hate_speech",
    "violence",
    "copyright",
    "other",
}
ALLOWED_REPORT_STATUSES = {"PENDING", "REVIEWING", "RESOLVED", "REJECTED"}
ALLOWED_RESOLUTION_ACTIONS = {
    "none",
    "user_suspended",
    "dismissed",
}


class ReportCreateRequest(BaseModel):
    report_type: str = Field(
        ...,
        description="Type of entity reported: user, post, comment, community, chat_message",
    )
    target_id: uuid.UUID = Field(
        ..., description="The ID of the reported entity"
    )
    community_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional community ID if the report is scoped to a community",
    )
    reason: str = Field(
        ...,
        description="Reason: spam, harassment, inappropriate_content, hate_speech, violence, copyright, other",
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Optional extra details"
    )


class ReportStatusUpdateRequest(BaseModel):
    status: str = Field(
        ..., description="New status: PENDING, REVIEWING, RESOLVED, REJECTED"
    )
    resolution_action: Optional[str] = Field(
        "none",
        description="Action applied: none, user_suspended, dismissed",
    )
    resolution_notes: Optional[str] = Field(
        None, max_length=1000, description="Moderator resolution notes"
    )


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reporter_id: uuid.UUID
    reporter_username: Optional[str] = None
    report_type: str
    target_id: uuid.UUID
    community_id: Optional[uuid.UUID] = None
    reason: str
    description: Optional[str] = None
    status: str
    resolution_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PaginatedReportsResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    limit: int
    offset: int
