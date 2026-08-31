"""Prevent duplicate open reports.

Revision ID: 0012_report_integrity
Revises: 0011_live_reliability
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_report_integrity"
down_revision: Union[str, None] = "0011_live_reliability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE reports
        SET status = 'REJECTED',
            resolution_action = 'dismissed',
            resolution_notes = 'Closed automatically while enforcing duplicate-report integrity.'
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY reporter_id, report_type, target_id
                           ORDER BY created_at ASC, id ASC
                       ) AS duplicate_number
                FROM reports
                WHERE status IN ('PENDING', 'REVIEWING')
            ) duplicates
            WHERE duplicate_number > 1
        )
        """
    )
    op.create_index(
        "uq_reports_open_reporter_target",
        "reports",
        ["reporter_id", "report_type", "target_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'REVIEWING')"),
    )


def downgrade() -> None:
    op.drop_index("uq_reports_open_reporter_target", table_name="reports")
