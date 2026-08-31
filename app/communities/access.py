"""Central authorization policy for reading communities and member lists."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communities.models import Community, CommunityMembership
from app.core.exceptions import NotFoundException
from app.users.models import User


def community_access_filters(
    viewer_id: Optional[uuid.UUID], *, is_superuser: bool = False
) -> list:
    if is_superuser:
        return []
    if viewer_id is None:
        return [Community.is_private.is_(False)]
    joined = select(CommunityMembership.community_id).where(
        CommunityMembership.user_id == viewer_id
    )
    return [or_(Community.is_private.is_(False), Community.id.in_(joined))]


async def require_community_view(
    db: AsyncSession, community: Community, viewer: Optional[User]
) -> None:
    filters = community_access_filters(
        viewer.id if viewer else None,
        is_superuser=bool(viewer and viewer.is_superuser),
    )
    if not filters:
        return
    stmt = select(Community.id).where(Community.id == community.id, *filters)
    if (await db.execute(stmt)).scalar_one_or_none() is None:
        raise NotFoundException("Community not found.")
