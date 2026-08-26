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


class SearchService:
    """Service handling multi-entity search with Meilisearch engine and PostgreSQL fallback."""

    def __init__(
        self,
        search_repo: SearchRepository = search_repository,
        meili: MeilisearchService = meilisearch_service,
    ):
        self.repo = search_repo
        self.meili = meili

    async def search_users(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedUserSearchResponse:
        current_uid = current_user.id if current_user else None

        # 1. Try Meilisearch if available
        if await self.meili.is_healthy():
            res = await self.meili.search(
                INDEX_USERS,
                query=query,
                limit=limit,
                offset=offset,
            )
            hits = res.get("hits", [])
            total = res.get("total", 0)
            if hits or total > 0:
                items = [
                    UserSearchResult(
                        id=uuid.UUID(h["id"]) if isinstance(h["id"], str) else h["id"],
                        username=h.get("username", ""),
                        display_name=h.get("display_name"),
                        avatar_url=h.get("avatar_url"),
                        bio=h.get("bio"),
                        follower_count=h.get("follower_count", 0),
                    )
                    for h in hits
                ]
                return PaginatedUserSearchResponse(
                    items=items, total=total, limit=limit, offset=offset
                )

        # 2. Fallback to SQL query
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
            )
            for u in users
        ]
        return PaginatedUserSearchResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def search_communities(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedCommunitySearchResponse:
        current_uid = current_user.id if current_user else None

        # 1. Try Meilisearch
        if await self.meili.is_healthy():
            res = await self.meili.search(
                INDEX_COMMUNITIES,
                query=query,
                limit=limit,
                offset=offset,
            )
            hits = res.get("hits", [])
            total = res.get("total", 0)
            if hits or total > 0:
                items = [
                    CommunitySearchResult(
                        id=uuid.UUID(h["id"]) if isinstance(h["id"], str) else h["id"],
                        name=h.get("name", ""),
                        slug=h.get("slug", ""),
                        description=h.get("description"),
                        avatar_url=h.get("avatar_url"),
                        cover_image_url=h.get("cover_image_url"),
                        is_private=h.get("is_private", False),
                        member_count=h.get("member_count", 0),
                        post_count=h.get("post_count", 0),
                    )
                    for h in hits
                ]
                return PaginatedCommunitySearchResponse(
                    items=items, total=total, limit=limit, offset=offset
                )

        # 2. SQL Fallback
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

    async def search_posts(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPostSearchResponse:
        current_uid = current_user.id if current_user else None

        # 1. Try Meilisearch
        if await self.meili.is_healthy():
            res = await self.meili.search(
                INDEX_POSTS,
                query=query,
                limit=limit,
                offset=offset,
            )
            hits = res.get("hits", [])
            total = res.get("total", 0)
            if hits or total > 0:
                items = [
                    PostSearchResult(
                        id=uuid.UUID(h["id"]) if isinstance(h["id"], str) else h["id"],
                        title=h.get("title"),
                        content=h.get("content"),
                        post_type=h.get("post_type", "text"),
                        visibility=h.get("visibility", "public"),
                        author_id=uuid.UUID(h["author_id"])
                        if h.get("author_id")
                        else None,
                        author_username=h.get("author_username"),
                        community_id=uuid.UUID(h["community_id"])
                        if h.get("community_id")
                        else None,
                        community_name=h.get("community_name"),
                        like_count=h.get("like_count", 0),
                        comment_count=h.get("comment_count", 0),
                    )
                    for h in hits
                ]
                return PaginatedPostSearchResponse(
                    items=items, total=total, limit=limit, offset=offset
                )

        # 2. SQL Fallback
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
            )
            hits = res.get("hits", [])
            total = res.get("total", 0)
            if hits or total > 0:
                items = [
                    InterestSearchResult(
                        id=uuid.UUID(h["id"]) if isinstance(h["id"], str) else h["id"],
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

    async def search_unified(
        self,
        db: AsyncSession,
        current_user: Optional[User],
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> UnifiedSearchResponse:
        """Unified multi-domain search across Users, Communities, Posts, and Interests."""
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

        return UnifiedSearchResponse(
            query=query,
            users=users_resp.items,
            communities=comm_resp.items,
            posts=posts_resp.items,
            interests=interests_resp.items,
            total_results=total_results,
        )

    async def sync_all_indexes(self, db: AsyncSession) -> SyncIndexResponse:
        """Extract all database records and index them into Meilisearch."""
        await self.meili.init_indexes()

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

        # 3. Sync Posts
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
                "community_id": str(p.community_id) if p.community_id else None,
                "community_name": p.community.name if p.community else None,
                "like_count": p.like_count,
                "comment_count": p.comment_count,
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
