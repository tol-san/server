import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.reports.models import Report
from app.users.models import User


class ReportRepository:
    """Repository handling database operations for User Reports and Moderation."""

    async def create(
        self,
        db: AsyncSession,
        *,
        reporter_id: uuid.UUID,
        report_type: str,
        target_id: uuid.UUID,
        reason: str,
        description: Optional[str] = None,
        community_id: Optional[uuid.UUID] = None,
    ) -> Report:
        report = Report(
            reporter_id=reporter_id,
            report_type=report_type,
            target_id=target_id,
            community_id=community_id,
            reason=reason,
            description=description,
            status="PENDING",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    async def get_by_id(
        self, db: AsyncSession, report_id: uuid.UUID
    ) -> Optional[Report]:
        stmt = (
            select(Report)
            .where(Report.id == report_id)
            .options(
                selectinload(Report.reporter).selectinload(User.profile),
                selectinload(Report.reviewer),
                selectinload(Report.community),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        report_type: Optional[str] = None,
        community_id: Optional[uuid.UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[Sequence[Report], int]:
        filters = []
        if status:
            filters.append(Report.status == status.upper().strip())
        if report_type:
            filters.append(Report.report_type == report_type.lower().strip())
        if community_id:
            filters.append(Report.community_id == community_id)

        count_stmt = select(func.count(Report.id)).where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Report)
            .where(*filters)
            .options(
                selectinload(Report.reporter).selectinload(User.profile),
                selectinload(Report.reviewer),
                selectinload(Report.community),
            )
            .order_by(Report.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    async def update_status(
        self,
        db: AsyncSession,
        *,
        report: Report,
        status: str,
        resolution_action: Optional[str] = None,
        resolution_notes: Optional[str] = None,
        reviewed_by: Optional[uuid.UUID] = None,
    ) -> Report:
        report.status = status.upper().strip()
        report.resolution_action = resolution_action
        report.resolution_notes = resolution_notes
        report.reviewed_by = reviewed_by
        report.reviewed_at = datetime.now(timezone.utc)

        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report


report_repository = ReportRepository()
