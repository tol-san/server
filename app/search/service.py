import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.meilisearch import (
    INDEX_COMMUNITIES,
    INDEX_INTERESTS,
    INDEX_POSTS,
    INDEX_USERS,
    MeilisearchService,
    meilisearch_service,
)
from app.search.repository import SearchRepository, search_repository
from app.search.schemas import (
    CommunitySearchResult,
    InterestSearchResult,
    PaginatedCommunitySearchResponse,
    PaginatedInterestSearchResponse,
    PaginatedPostSearchResponse,
    PaginatedUserSearchResponse,
    PostSearchResult,
    SyncIndexResponse,
    UnifiedSearchResponse,
    UserSearchResult,
)
from app.users.models import User

logger = logging.getLogger(__name__)

# Fields highlighted in search results (Meilisearch <em> tags)
_USER_HIGHLIGHT_ATTRS = ["username", "display_name", "bio"]
_COMMUNITY_HIGHLIGHT_ATTRS = ["name", "description"]
_POST_HIGHLIGHT_ATTRS = ["title", "content"]
_INTEREST_HIGHLIGHT_ATTRS = ["name", "description"]


def _parse_uuid(value: Any) -> uuid.UUID:
    return uuid.UUID(value) if isinstance(value, str) else value


class SearchService:
    """Service handling multi-entity search with Meilisearch engine and PostgreSQL fallback."""

    def __init__(
        self,
        search_repo: SearchRepository = search_repository,
        meili: MeilisearchService = meilisearch_service,
    ):
        self.repo = search_repo
        self.meili = meili

    # ─────────────────────────────────────────────────────────────────────────
    # Users
    # ─────────────────────────────────────────────────────────────────────────

    async def search_users(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedUserSearchResponse:
        current_uid = current_user.id if current_user else None
        following_ids: set[str] = set()
        if current_uid:
            following_ids = await self.repo.get_following_user_ids(db, current_uid)

        # 1. Try Meilisearch with highlighting
        if await self.meili.is_healthy():
            res = await self.meili.search(
                INDEX_USERS,
                query=query,
                limit=limit,
                offset=offset,
                attributes_to_highlight=_USER_HIGHLIGHT_ATTRS,
            )
            hits: List[Dict[str, Any]] = res.get("hits", [])
            total: int = res.get("total") or 0

            # Block-safety: filter out blocked users
            if current_uid and hits:
                blocked_ids = await self.repo.get_blocked_user_ids(db, current_uid)
                hits = [h for h in hits if str(h.get("id")) not in blocked_ids]

            if hits:
                items = [
                    UserSearchResult(
                        id=_parse_uuid(h["id"]),
                        username=h.get("username", ""),
                        display_name=h.get("display_name"),
                        avatar_url=h.get("avatar_url"),
                        bio=h.get("bio"),
                        follower_count=h.get("follower_count", 0),
                        is_following=(str(h.get("id")) in following_ids) if current_uid else None,
                    )
                    for h in hits
                ]
                return PaginatedUserSearchResponse(
                    items=items,
                    total=len(hits) if current_uid else total,
                    limit=limit,
                    offset=offset,
                )

        # 2. SQL fallback
        users, total = await self.repo.search_users(
            db,
            query=query,
            current_user_id=current_uid,
            limit=limit,
            offset=offset,
        )
        items = [
            UserSearchResult(
                id=u.id,
                username=u.username,
                display_name=u.profile.display_name if u.profile else u.username,
                avatar_url=u.profile.avatar_url if u.profile else None,
                bio=u.profile.bio if u.profile else None,
                follower_count=u.profile.follower_count if u.profile else 0,
                is_following=(str(u.id) in following_ids) if current_uid else None,
            )
            for u in users
        ]
        return PaginatedUserSearchResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Communities
    # ─────────────────────────────────────────────────────────────────────────

    async def search_communities(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedCommunitySearchResponse:
        current_uid = current_user.id if current_user else None

        # 1. Try Meilisearch as a candidate filter, then re-check authorization in SQL.
        #    This gives typo-tolerant FT ranking while keeping correctness (membership,
        #    privacy) enforced by the live database.
        if await self.meili.is_healthy():
            res = await self.meili.search(
                INDEX_COMMUNITIES,
                query=query,
                # Fetch a generous batch so SQL re-check doesn't under-return
                limit=limit * 3,
                offset=0,
                attributes_to_highlight=_COMMUNITY_HIGHLIGHT_ATTRS,
            )
            hits: List[Dict[str, Any]] = res.get("hits", [])
            if hits:
                candidate_ids = [_parse_uuid(h["id"]) for h in hits]
                highlight_map: Dict[str, Any] = {
                    str(h["id"]): h.get("_highlight", {}) for h in hits
                }
                communities = await self.repo.search_communities_by_ids(
                    db,
                    community_ids=candidate_ids,
                    current_user_id=current_uid,
                    limit=limit,
                    offset=offset,
                )
                # Preserve Meilisearch ranking order
                id_order = {str(cid): idx for idx, cid in enumerate(candidate_ids)}
                communities = sorted(
                    communities, key=lambda c: id_order.get(str(c.id), 9999)
                )
                items = [
                    CommunitySearchResult(
                        id=c.id,
                        name=c.name,
                        slug=c.slug,
                        description=c.description,
                        avatar_url=c.avatar_url,
                        cover_image_url=c.cover_image_url,
                        is_private=c.is_private,
                        member_count=c.member_count,
                        post_count=c.post_count,
                    )
                    for c in communities
                ]
                if items:
                    return PaginatedCommunitySearchResponse(
                        items=items,
                        total=res.get("total") or len(items),
                        limit=limit,
                        offset=offset,
                    )

        # 2. SQL fallback (always-correct, used when Meili is down or returns nothing)
        communities, total = await self.repo.search_communities(
            db,
            query=query,
            current_user_id=current_uid,
            limit=limit,
            offset=offset,
        )
        items = [
            CommunitySearchResult(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description,
                avatar_url=c.avatar_url,
                cover_image_url=c.cover_image_url,
                is_private=c.is_private,
                member_count=c.member_count,
                post_count=c.post_count,
            )
            for c in communities
        ]
        return PaginatedCommunitySearchResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Posts
    # ─────────────────────────────────────────────────────────────────────────

    async def search_posts(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostSearchResponse:
        current_uid = current_user.id if current_user else None

        # 1. Try Meilisearch as a candidate filter.
        #    Post visibility (follows, blocks, community membership) is enforced by SQL.
        if await self.meili.is_healthy():
            res = await self.meili.search(
                INDEX_POSTS,
                query=query,
                limit=limit * 3,
                offset=0,
                attributes_to_highlight=_POST_HIGHLIGHT_ATTRS,
                attributes_to_crop=["content"],
                crop_length=25,
            )
            hits: List[Dict[str, Any]] = res.get("hits", [])
            if hits:
                candidate_ids = [_parse_uuid(h["id"]) for h in hits]
                highlight_map: Dict[str, Any] = {
                    str(h["id"]): h.get("_highlight", {}) for h in hits
                }
                # Store Meilisearch-returned field values for enrichment
                meili_meta: Dict[str, Dict[str, Any]] = {str(h["id"]): h for h in hits}

                posts = await self.repo.search_posts_by_ids(
                    db,
                    post_ids=candidate_ids,
                    current_user_id=current_uid,
                    limit=limit,
                    offset=offset,
                )
                # Preserve Meilisearch ranking order
                id_order = {str(pid): idx for idx, pid in enumerate(candidate_ids)}
                posts = sorted(posts, key=lambda p: id_order.get(str(p.id), 9999))

                items = [
                    PostSearchResult(
                        id=p.id,
                        title=p.title,
                        content=p.content,
                        post_type=p.post_type,
                        visibility=p.visibility,
                        author_id=p.author_id,
                        author_username=p.author.username if p.author else None,
                        author_avatar_url=(
                            p.author.profile.avatar_url
                            if (p.author and p.author.profile)
                            else None
                        ),
                        community_id=p.community_id,
                        community_name=p.community.name if p.community else None,
                        like_count=p.like_count,
                        comment_count=p.comment_count,
                        thumbnail_url=meili_meta.get(str(p.id), {}).get("thumbnail_url"),
                        highlight=highlight_map.get(str(p.id)) or None,
                        created_at=p.created_at,
                    )
                    for p in posts
                ]
                if items:
                    return PaginatedPostSearchResponse(
                        items=items,
                        total=res.get("total") or len(items),
                        limit=limit,
                        offset=offset,
                    )

        # 2. SQL fallback
        posts, total = await self.repo.search_posts(
            db,
            query=query,
            current_user_id=current_uid,
            limit=limit,
            offset=offset,
        )
        items = [
            PostSearchResult(
                id=p.id,
                title=p.title,
                content=p.content,
                post_type=p.post_type,
                visibility=p.visibility,
                author_id=p.author_id,
                author_username=p.author.username if p.author else None,
                author_avatar_url=(
                    p.author.profile.avatar_url
                    if (p.author and p.author.profile)
                    else None
                ),
                community_id=p.community_id,
                community_name=p.community.name if p.community else None,
                like_count=p.like_count,
                comment_count=p.comment_count,
                created_at=p.created_at,
            )
            for p in posts
        ]
        return PaginatedPostSearchResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Interests
    # ─────────────────────────────────────────────────────────────────────────

    async def search_interests(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedInterestSearchResponse:
        # 1. Try Meilisearch
        if await self.meili.is_healthy():
            res = await self.meili.search(
                INDEX_INTERESTS,
                query=query,
                limit=limit,
                offset=offset,
                attributes_to_highlight=_INTEREST_HIGHLIGHT_ATTRS,
            )
            hits: List[Dict[str, Any]] = res.get("hits", [])
            total: int = res.get("total") or 0
            if hits or total > 0:
                items = [
                    InterestSearchResult(
                        id=_parse_uuid(h["id"]),
                        name=h.get("name", ""),
                        slug=h.get("slug", ""),
                        description=h.get("description"),
                        icon_url=h.get("icon_url"),
                    )
                    for h in hits
                ]
                return PaginatedInterestSearchResponse(
                    items=items, total=total, limit=limit, offset=offset
                )

        # 2. SQL Fallback
        interests, total = await self.repo.search_interests(
            db, query=query, limit=limit, offset=offset
        )
        items = [
            InterestSearchResult(
                id=i.id,
                name=i.name,
                slug=i.slug,
                description=i.description,
                icon_url=i.icon_url,
            )
            for i in interests
        ]
        return PaginatedInterestSearchResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Unified
    # ─────────────────────────────────────────────────────────────────────────

    async def search_unified(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> UnifiedSearchResponse:
        """Unified multi-domain search across Users, Communities, Posts, and Interests with Redis caching."""
        import hashlib
        from app.core.cache import cache_service

        q_hash = hashlib.md5(query.strip().lower().encode("utf-8")).hexdigest()
        cache_key = f"cache:search:unified:{q_hash}:{limit}:{offset}"
        if not current_user:
            cached = await cache_service.get(cache_key)
            if cached:
                return UnifiedSearchResponse.model_validate(cached)

        users_resp = await self.search_users(
            db, current_user, query, limit=limit, offset=offset
        )
        comm_resp = await self.search_communities(
            db, current_user, query, limit=limit, offset=offset
        )
        posts_resp = await self.search_posts(
            db, current_user, query, limit=limit, offset=offset
        )
        interests_resp = await self.search_interests(
            db, current_user, query, limit=limit, offset=offset
        )

        total_results = (
            users_resp.total
            + comm_resp.total
            + posts_resp.total
            + interests_resp.total
        )

        resp = UnifiedSearchResponse(
            query=query,
            users=users_resp.items,
            communities=comm_resp.items,
            posts=posts_resp.items,
            interests=interests_resp.items,
            total_results=total_results,
        )

        if not current_user:
            await cache_service.set(cache_key, resp.model_dump(mode="json"), ttl=120)

        return resp

    # ─────────────────────────────────────────────────────────────────────────
    # Admin: full index re-sync
    # ─────────────────────────────────────────────────────────────────────────

    async def sync_all_indexes(self, db: AsyncSession) -> SyncIndexResponse:
        """Extract all database records and index them into Meilisearch."""
        from sqlalchemy import or_, select
        from app.communities.models import Community
        from app.posts.models import Post

        await self.meili.init_indexes()

        private_community_ids = (
            await db.execute(select(Community.id).where(Community.is_private.is_(True)))
        ).scalars().all()
        nonpublic_post_ids = (
            await db.execute(
                select(Post.id).where(
                    or_(
                        Post.visibility != "public",
                        Post.community_id.in_(private_community_ids),
                    )
                )
            )
        ).scalars().all()
        await self.meili.delete_documents(INDEX_COMMUNITIES, list(private_community_ids))
        await self.meili.delete_documents(INDEX_POSTS, list(nonpublic_post_ids))

        # 1. Sync Users
        users = await self.repo.fetch_all_users_for_sync(db)
        user_docs = [
            {
                "id": str(u.id),
                "username": u.username,
                "display_name": u.profile.display_name if u.profile else u.username,
                "avatar_url": u.profile.avatar_url if u.profile else None,
                "bio": u.profile.bio if u.profile else None,
                "follower_count": u.profile.follower_count if u.profile else 0,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
        await self.meili.index_documents(INDEX_USERS, user_docs)

        # 2. Sync Communities
        communities = await self.repo.fetch_all_communities_for_sync(db)
        comm_docs = [
            {
                "id": str(c.id),
                "name": c.name,
                "slug": c.slug,
                "description": c.description,
                "avatar_url": c.avatar_url,
                "cover_image_url": c.cover_image_url,
                "is_private": c.is_private,
                "owner_id": str(c.owner_id),
                "member_count": c.member_count,
                "post_count": c.post_count,
                "interest_id": str(c.interest_id) if c.interest_id else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in communities
        ]
        await self.meili.index_documents(INDEX_COMMUNITIES, comm_docs)

        # 3. Sync Posts (with enriched thumbnail_url and author_avatar_url)
        posts = await self.repo.fetch_all_posts_for_sync(db)
        post_docs = [
            {
                "id": str(p.id),
                "title": p.title,
                "content": p.content,
                "post_type": p.post_type,
                "visibility": p.visibility,
                "author_id": str(p.author_id),
                "author_username": p.author.username if p.author else None,
                "author_avatar_url": (
                    p.author.profile.avatar_url
                    if (p.author and p.author.profile)
                    else None
                ),
                "community_id": str(p.community_id) if p.community_id else None,
                "community_name": p.community.name if p.community else None,
                "like_count": p.like_count,
                "comment_count": p.comment_count,
                # Raw s3:// thumbnail URL; resolved by client or post API on demand
                "thumbnail_url": (
                    p.media_items[0].thumbnail_url if p.media_items else None
                ),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ]
        await self.meili.index_documents(INDEX_POSTS, post_docs)

        # 4. Sync Interests
        interests = await self.repo.fetch_all_interests_for_sync(db)
        interest_docs = [
            {
                "id": str(i.id),
                "name": i.name,
                "slug": i.slug,
                "description": i.description,
                "icon_url": i.icon_url,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in interests
        ]
        await self.meili.index_documents(INDEX_INTERESTS, interest_docs)

        msg = (
            f"Successfully synced {len(user_docs)} users, {len(comm_docs)} communities, "
            f"{len(post_docs)} posts, and {len(interest_docs)} interests to Meilisearch."
        )
        logger.info(msg)
        return SyncIndexResponse(
            synced_users=len(user_docs),
            synced_communities=len(comm_docs),
            synced_posts=len(post_docs),
            synced_interests=len(interest_docs),
            message=msg,
        )


search_service = SearchService()
