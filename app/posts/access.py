"""Central authorization policy for reading posts and post-derived resources."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communities.models import Community, CommunityMembership
from app.core.exceptions import NotFoundException
from app.posts.models import Post
from app.users.models import Block, Follow, User


def post_access_filters(
    viewer_id: Optional[uuid.UUID],
    *,
    is_superuser: bool = False,
) -> list:
    """Return SQL predicates implementing the canonical post read policy."""
    if is_superuser:
        return []

    public_communities = select(Community.id).where(Community.is_private.is_(False))

    if viewer_id is None:
        return [
            Post.visibility == "public",
            or_(
                Post.community_id.is_(None),
                Post.community_id.in_(public_communities),
            ),
        ]

    following = select(Follow.following_id).where(Follow.follower_id == viewer_id)
    joined_communities = select(CommunityMembership.community_id).where(
        CommunityMembership.user_id == viewer_id
    )
    blocked_by_viewer = select(Block.blocked_id).where(Block.blocker_id == viewer_id)
    viewers_blockers = select(Block.blocker_id).where(Block.blocked_id == viewer_id)

    return [
        Post.author_id.not_in(blocked_by_viewer),
        Post.author_id.not_in(viewers_blockers),
        or_(
            Post.community_id.is_(None),
            Post.community_id.in_(public_communities),
            Post.community_id.in_(joined_communities),
        ),
        or_(
            Post.visibility == "public",
            (Post.visibility == "followers_only")
            & or_(Post.author_id.in_(following), Post.author_id == viewer_id),
            (Post.visibility == "private") & (Post.author_id == viewer_id),
        ),
    ]


async def require_post_view(
    db: AsyncSession,
    post: Post,
    viewer: Optional[User],
) -> None:
    """Hide a post's existence unless the viewer satisfies the read policy."""
    filters = post_access_filters(
        viewer.id if viewer else None,
        is_superuser=bool(viewer and viewer.is_superuser),
    )
    if not filters:
        return
    stmt = select(Post.id).where(Post.id == post.id, *filters)
    if (await db.execute(stmt)).scalar_one_or_none() is None:
        raise NotFoundException("Post not found.")
