import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.communities.repository import community_repository
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.reports.models import Report
from app.reports.repository import ReportRepository, report_repository
from app.reports.schemas import (
    ALLOWED_REPORT_REASONS,
    ALLOWED_REPORT_STATUSES,
    ALLOWED_REPORT_TYPES,
    ALLOWED_RESOLUTION_ACTIONS,
    PaginatedReportsResponse,
    ReportCreateRequest,
    ReportResponse,
    ReportStatusUpdateRequest,
)
from app.users.models import User
from app.users.repository import user_repository


def map_report_to_response(r: Report) -> ReportResponse:
    return ReportResponse(
        id=r.id,
        reporter_id=r.reporter_id,
        reporter_username=r.reporter.username if r.reporter else None,
        report_type=r.report_type,
        target_id=r.target_id,
        community_id=r.community_id,
        reason=r.reason,
        description=r.description,
        status=r.status,
        resolution_action=r.resolution_action,
        resolution_notes=r.resolution_notes,
        reviewed_by=r.reviewed_by,
        reviewed_at=r.reviewed_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


class ReportService:
    """Service handling report submissions, status workflows, and moderation actions."""

    def __init__(
        self,
        repo: ReportRepository = report_repository,
        user_repo=user_repository,
        comm_repo=community_repository,
    ):
        self.repo = repo
        self.user_repo = user_repo
        self.comm_repo = comm_repo

    async def submit_report(
        self,
        db: AsyncSession,
        current_user: User,
        payload: ReportCreateRequest,
    ) -> ReportResponse:
        report_type = payload.report_type.lower().strip()
        if report_type not in ALLOWED_REPORT_TYPES:
            raise BadRequestException(
                f"Invalid report type '{payload.report_type}'. Allowed: {', '.join(ALLOWED_REPORT_TYPES)}"
            )

        reason = payload.reason.lower().strip()
        if reason not in ALLOWED_REPORT_REASONS:
            raise BadRequestException(
                f"Invalid reason '{payload.reason}'. Allowed: {', '.join(ALLOWED_REPORT_REASONS)}"
            )

        # Validate community_id if passed
        if payload.community_id:
            comm = await self.comm_repo.get_by_id(db, payload.community_id)
            if not comm:
                raise NotFoundException("The specified community does not exist.")

        report = await self.repo.create(
            db,
            reporter_id=current_user.id,
            report_type=report_type,
            target_id=payload.target_id,
            community_id=payload.community_id,
            reason=reason,
            description=payload.description,
        )

        loaded = await self.repo.get_by_id(db, report.id)
        return map_report_to_response(loaded or report)

    async def get_report(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        current_user: User,
    ) -> ReportResponse:
        report = await self.repo.get_by_id(db, report_id)
        if not report:
            raise NotFoundException("Report not found.")

        # Permissions: Superuser OR Community Owner if report has community_id
        is_admin = current_user.is_superuser
        is_comm_owner = (
            report.community is not None
            and report.community.owner_id == current_user.id
        )

        if not (is_admin or is_comm_owner):
            raise ForbiddenException(
                "You do not have permission to view this report."
            )

        return map_report_to_response(report)

    async def list_reports(
        self,
        db: AsyncSession,
        current_user: User,
        status: Optional[str] = None,
        report_type: Optional[str] = None,
        community_id: Optional[uuid.UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedReportsResponse:
        is_admin = current_user.is_superuser

        if not is_admin:
            # If not admin, must be a community owner querying their own community
            if not community_id:
                raise ForbiddenException(
                    "Administrator privileges required to view platform-wide reports."
                )
            comm = await self.comm_repo.get_by_id(db, community_id)
            if not comm or comm.owner_id != current_user.id:
                raise ForbiddenException(
                    "You can only view reports for communities you own."
                )

        reports, total = await self.repo.list_reports(
            db,
            status=status,
            report_type=report_type,
            community_id=community_id,
            limit=limit,
            offset=offset,
        )
        items = [map_report_to_response(r) for r in reports]
        return PaginatedReportsResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def update_report_status(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        current_user: User,
        payload: ReportStatusUpdateRequest,
    ) -> ReportResponse:
        report = await self.repo.get_by_id(db, report_id)
        if not report:
            raise NotFoundException("Report not found.")

        new_status = payload.status.upper().strip()
        if new_status not in ALLOWED_REPORT_STATUSES:
            raise BadRequestException(
                f"Invalid status '{payload.status}'. Allowed: {', '.join(ALLOWED_REPORT_STATUSES)}"
            )

        action = (
            payload.resolution_action.lower().strip()
            if payload.resolution_action
            else "none"
        )
        if action not in ALLOWED_RESOLUTION_ACTIONS:
            raise BadRequestException(
                f"Invalid resolution action '{payload.resolution_action}'. Allowed: {', '.join(ALLOWED_RESOLUTION_ACTIONS)}"
            )

        is_admin = current_user.is_superuser
        is_comm_owner = (
            report.community is not None
            and report.community.owner_id == current_user.id
        )

        if not (is_admin or is_comm_owner):
            raise ForbiddenException(
                "You do not have permission to moderate this report."
            )

        # Community owners cannot suspend users globally
        if action == "user_suspended" and not is_admin:
            raise ForbiddenException(
                "Only platform administrators can suspend user accounts."
            )

        # Apply action if resolved
        if new_status == "RESOLVED":
            if action == "user_suspended" and is_admin:
                target_user = await self.user_repo.get_by_id(db, report.target_id)
                if target_user:
                    target_user.is_active = False
                    db.add(target_user)
                    await db.commit()

        updated_report = await self.repo.update_status(
            db,
            report=report,
            status=new_status,
            resolution_action=action,
            resolution_notes=payload.resolution_notes,
            reviewed_by=current_user.id,
        )

        return map_report_to_response(updated_report)


report_service = ReportService()
