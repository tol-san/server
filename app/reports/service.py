import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.communities.repository import community_repository
from app.communities.access import require_community_view
from app.comments.repository import comment_repository
from app.chats.repository import chat_repository
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
from app.posts.access import require_post_view
from app.posts.repository import post_repository


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

    async def _resolve_target(
        self,
        db: AsyncSession,
        report_type: str,
        target_id: uuid.UUID,
        viewer: Optional[User] = None,
    ) -> tuple[Optional[uuid.UUID], Optional[uuid.UUID]]:
        """Return (derived community ID, responsible user ID) after access checks."""
        if report_type == "user":
            user = await self.user_repo.get_by_id(db, target_id)
            if not user:
                raise NotFoundException("Reported user not found.")
            return None, user.id

        if report_type == "community":
            community = await self.comm_repo.get_by_id(db, target_id)
            if not community:
                raise NotFoundException("Reported community not found.")
            await require_community_view(db, community, viewer)
            return community.id, community.owner_id

        if report_type == "post":
            post = await post_repository.get_by_id(db, target_id)
            if not post:
                raise NotFoundException("Reported post not found.")
            if viewer:
                await require_post_view(db, post, viewer)
            return post.community_id, post.author_id

        if report_type == "comment":
            comment = await comment_repository.get_by_id(db, target_id)
            if not comment:
                raise NotFoundException("Reported comment not found.")
            if viewer:
                await require_post_view(db, comment.post, viewer)
            return comment.post.community_id, comment.user_id

        message = await chat_repository.get_by_id(db, target_id)
        if not message:
            raise NotFoundException("Reported chat message not found.")
        if viewer and not viewer.is_superuser:
            membership = await self.comm_repo.get_membership(
                db, message.community_id, viewer.id
            )
            if not membership:
                raise NotFoundException("Reported chat message not found.")
        return message.community_id, message.sender_id

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

        derived_community_id, target_user_id = await self._resolve_target(
            db, report_type, payload.target_id, current_user
        )
        if payload.community_id and payload.community_id != derived_community_id:
            raise BadRequestException(
                "community_id does not match the reported resource."
            )
        if target_user_id == current_user.id:
            raise BadRequestException("You cannot report your own resource.")
        if await self.repo.get_open_report(
            db,
            reporter_id=current_user.id,
            report_type=report_type,
            target_id=payload.target_id,
        ):
            raise BadRequestException("You already have an open report for this resource.")

        try:
            report = await self.repo.create(
                db,
                reporter_id=current_user.id,
                report_type=report_type,
                target_id=payload.target_id,
                community_id=derived_community_id,
                reason=reason,
                description=payload.description,
            )
        except ValueError as exc:
            raise BadRequestException(str(exc)) from exc

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

        transitions = {
            "PENDING": {"REVIEWING", "RESOLVED", "REJECTED"},
            "REVIEWING": {"RESOLVED", "REJECTED"},
            "RESOLVED": set(),
            "REJECTED": set(),
        }
        if new_status != report.status and new_status not in transitions[report.status]:
            raise BadRequestException(
                f"Cannot transition report from {report.status} to {new_status}."
            )
        if new_status not in {"RESOLVED", "REJECTED"} and action != "none":
            raise BadRequestException(
                "A resolution action can only be set when closing a report."
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

        if action == "user_suspended":
            if new_status != "RESOLVED" or not is_admin:
                raise ForbiddenException(
                    "Only platform administrators can suspend users while resolving a report."
                )
            _, target_user_id = await self._resolve_target(
                db, report.report_type, report.target_id
            )
            target_user = await self.user_repo.get_by_id(db, target_user_id)
            if not target_user:
                raise NotFoundException("The responsible user no longer exists.")
            target_user.is_active = False
            target_user.token_version += 1
            db.add(target_user)

        updated_report = await self.repo.update_status(
            db,
            report=report,
            status=new_status,
            resolution_action=action,
            resolution_notes=payload.resolution_notes,
            reviewed_by=current_user.id,
        )

        await db.commit()
        await db.refresh(updated_report)

        return map_report_to_response(updated_report)


report_service = ReportService()
