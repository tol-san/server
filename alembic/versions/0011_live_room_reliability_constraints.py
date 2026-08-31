"""Add live room/session idempotency constraints.

Revision ID: 0011_live_reliability
Revises: 0010_user_token_version
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_live_reliability"
down_revision: Union[str, None] = "0010_user_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing installations may contain duplicates from before these invariants
    # were enforced. Keep the earliest provider event and close all but the most
    # recently started active session per room before adding the constraints.
    op.execute(
        """
        DELETE FROM provider_events AS duplicate
        USING provider_events AS canonical
        WHERE duplicate.provider = canonical.provider
          AND duplicate.provider_event_id = canonical.provider_event_id
          AND (
              duplicate.received_at > canonical.received_at
              OR (
                  duplicate.received_at = canonical.received_at
                  AND duplicate.id > canonical.id
              )
          )
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY room_id
                       ORDER BY started_at DESC, id DESC
                   ) AS active_rank
            FROM live_sessions
            WHERE ended_at IS NULL
        )
        UPDATE live_sessions AS session
        SET ended_at = GREATEST(session.started_at, CURRENT_TIMESTAMP),
            duration_seconds = GREATEST(
                0,
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - session.started_at))::integer
            )
        FROM ranked
        WHERE session.id = ranked.id
          AND ranked.active_rank > 1
        """
    )
    op.create_unique_constraint(
        "uq_provider_event_identity",
        "provider_events",
        ["provider", "provider_event_id"],
    )
    op.create_index(
        "uq_live_sessions_one_active_per_room",
        "live_sessions",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_live_sessions_one_active_per_room", table_name="live_sessions"
    )
    op.drop_constraint(
        "uq_provider_event_identity", "provider_events", type_="unique"
    )
