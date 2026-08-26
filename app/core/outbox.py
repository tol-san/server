"""
Transactional Outbox — publish domain events atomically with database writes.

Usage inside a service method:
    async with db.begin():
        db.add(business_entity)
        await outbox.publish(db, event_type="chat.message.created", payload={...})
    # single COMMIT — both business row + outbox row land together
"""
from __future__ import annotations

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# ORM Models
# ─────────────────────────────────────────────────────────────────────────────

class OutboxEvent(Base):
    """Transactional outbox — events written in the same DB transaction as the business row."""
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def get_payload(self) -> Dict[str, Any]:
        return json.loads(self.payload)


class DeadLetterEvent(Base):
    """Events that exhausted all retries — stored for manual inspection/replay."""
    __tablename__ = "dead_letter_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_event_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(60), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worker: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )


# ─────────────────────────────────────────────────────────────────────────────
# Publisher helper
# ─────────────────────────────────────────────────────────────────────────────

async def publish(
    db: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: Dict[str, Any],
) -> OutboxEvent:
    """
    Write an OutboxEvent row within the *current* open transaction.
    Call this inside a `async with db.begin():` block to achieve atomicity.
    """
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=json.dumps(payload, default=str),
    )
    db.add(event)
    return event
