import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.reports.schemas import (
    PaginatedReportsResponse,
    ReportCreateRequest,
    ReportResponse,
    ReportStatusUpdateRequest,
)
from app.reports.service import ReportService, report_service
from app.users.models import User

router = APIRouter(prefix="/reports", tags=["Reports & Moderation"])


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit report",
    description="Submit a report against a user, post, comment, community, or chat message.",
)
async def submit_report(
    payload: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ReportService = Depends(lambda: report_service),
) -> ReportResponse:
    return await service.submit_report(db, current_user, payload)


@router.get(
    "",
    response_model=PaginatedReportsResponse,
    status_code=status.HTTP_200_OK,
    summary="List reports",
    description="List filed reports with status, report_type, and community filters (Admins & Community Owners).",
)
async def list_reports(
    status: Optional[str] = Query(
        None, description="Filter by status: PENDING, REVIEWING, RESOLVED, REJECTED"
    ),
    report_type: Optional[str] = Query(
        None,
        description="Filter by type: user, post, comment, community, chat_message",
    ),
    community_id: Optional[uuid.UUID] = Query(
        None, description="Filter by community ID (mandatory for Community Owners)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ReportService = Depends(lambda: report_service),
) -> PaginatedReportsResponse:
    return await service.list_reports(
        db,
        current_user,
        status=status,
        report_type=report_type,
        community_id=community_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get report details",
    description="Retrieve details of a report by ID (Admin or Community Owner).",
)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ReportService = Depends(lambda: report_service),
) -> ReportResponse:
    return await service.get_report(db, report_id, current_user)


@router.patch(
    "/{report_id}/status",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Update report status & apply action",
    description="Transition report through moderation states (PENDING -> REVIEWING -> RESOLVED / REJECTED) and apply punitive actions.",
)
async def update_report_status(
    report_id: uuid.UUID,
    payload: ReportStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    service: ReportService = Depends(lambda: report_service),
) -> ReportResponse:
    return await service.update_report_status(db, report_id, current_user, payload)
