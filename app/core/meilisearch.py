"""Meilisearch client, service, and indexing management module."""

import logging
from typing import Any, Dict, List, Optional, Union
from meilisearch_python_sdk import AsyncClient
from meilisearch_python_sdk.errors import (
    MeilisearchApiError,
    MeilisearchCommunicationError,
    MeilisearchError,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global singleton client instance
meilisearch_client: Optional[AsyncClient] = None

# Predefined index names
INDEX_USERS = "users"
INDEX_COMMUNITIES = "communities"
INDEX_POSTS = "posts"
INDEX_INTERESTS = "interests"

# Index settings and schemas
INDEX_CONFIGURATIONS: Dict[str, Dict[str, Any]] = {
    INDEX_USERS: {
        "primary_key": "id",
        "searchable_attributes": ["username", "display_name", "bio"],
        "filterable_attributes": ["id", "is_active"],
        "sortable_attributes": ["created_at"],
    },
    INDEX_COMMUNITIES: {
        "primary_key": "id",
        "searchable_attributes": ["name", "description"],
        "filterable_attributes": ["id", "is_private", "owner_id"],
        "sortable_attributes": ["created_at", "member_count"],
    },
    INDEX_POSTS: {
        "primary_key": "id",
        "searchable_attributes": ["title", "content"],
        "filterable_attributes": [
            "id",
            "user_id",
            "community_id",
            "post_type",
            "visibility",
        ],
        "sortable_attributes": ["created_at", "likes_count", "comments_count"],
    },
    INDEX_INTERESTS: {
        "primary_key": "id",
        "searchable_attributes": ["name", "description"],
        "filterable_attributes": ["id", "slug"],
        "sortable_attributes": ["created_at"],
    },
}


def get_meilisearch_client() -> AsyncClient:
    """Get or initialize the global AsyncClient for Meilisearch."""
    global meilisearch_client
    if meilisearch_client is None:
        meilisearch_client = AsyncClient(
            url=settings.MEILISEARCH_URL,
            api_key=settings.MEILISEARCH_MASTER_KEY,
            custom_headers={"User-Agent": f"GenZ-Media-API/{settings.VERSION}"},
        )
    return meilisearch_client


async def close_meilisearch() -> None:
    """Gracefully close the Meilisearch async client."""
    global meilisearch_client
    if meilisearch_client is not None:
        try:
            await meilisearch_client.aclose()
        except Exception as exc:
            logger.warning("Error closing Meilisearch client: %s", exc)
        finally:
            meilisearch_client = None


class MeilisearchService:
    """Service wrapper for interacting with Meilisearch indexes and documents."""

    def __init__(self, client_factory=get_meilisearch_client):
        self._get_client = client_factory

    @property
    def client(self) -> AsyncClient:
        return self._get_client()

    async def is_healthy(self) -> bool:
        """Check if Meilisearch instance is reachable and healthy."""
        try:
            health = await self.client.health()
            return getattr(health, "status", "") == "available"
        except (MeilisearchCommunicationError, MeilisearchApiError, Exception) as exc:
            logger.debug("Meilisearch healthcheck failed: %s", exc)
            return False

    async def init_indexes(self) -> None:
        """Initialize required indexes and configure searchable, filterable, and sortable attributes."""
        try:
            for index_name, config in INDEX_CONFIGURATIONS.items():
                primary_key = config.get("primary_key", "id")
                index = await self.client.get_or_create_index(
                    uid=index_name, primary_key=primary_key
                )

                if "searchable_attributes" in config:
                    await index.update_searchable_attributes(
                        config["searchable_attributes"]
                    )
                if "filterable_attributes" in config:
                    await index.update_filterable_attributes(
                        config["filterable_attributes"]
                    )
                if "sortable_attributes" in config:
                    await index.update_sortable_attributes(config["sortable_attributes"])

            logger.info("Meilisearch indexes initialized successfully.")
        except (MeilisearchCommunicationError, MeilisearchApiError, Exception) as exc:
            logger.warning("Failed to initialize Meilisearch indexes: %s", exc)

    async def index_documents(
        self,
        index_name: str,
        documents: List[Dict[str, Any]],
        primary_key: Optional[str] = "id",
    ) -> bool:
        """Add or replace documents in the specified index."""
        if not documents:
            return True
        try:
            index = self.client.index(index_name)
            await index.add_documents(documents, primary_key=primary_key)
            return True
        except (MeilisearchCommunicationError, MeilisearchApiError, Exception) as exc:
            logger.warning(
                "Failed to index documents in Meilisearch (%s): %s", index_name, exc
            )
            return False

    async def delete_documents(
        self, index_name: str, document_ids: List[Union[str, int]]
    ) -> bool:
        """Delete documents from index by list of IDs."""
        if not document_ids:
            return True
        try:
            index = self.client.index(index_name)
            str_ids = [str(doc_id) for doc_id in document_ids]
            await index.delete_documents(str_ids)
            return True
        except (MeilisearchCommunicationError, MeilisearchApiError, Exception) as exc:
            logger.warning(
                "Failed to delete documents from Meilisearch (%s): %s", index_name, exc
            )
            return False

    async def delete_document(
        self, index_name: str, document_id: Union[str, int]
    ) -> bool:
        """Delete a single document from index."""
        try:
            index = self.client.index(index_name)
            await index.delete_document(str(document_id))
            return True
        except (MeilisearchCommunicationError, MeilisearchApiError, Exception) as exc:
            logger.warning(
                "Failed to delete document %s from Meilisearch (%s): %s",
                document_id,
                index_name,
                exc,
            )
            return False

    async def search(
        self,
        index_name: str,
        query: str,
        limit: int = 20,
        offset: int = 0,
        filter: Optional[Union[str, List[str]]] = None,
        sort: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search within a specific index with pagination and filters."""
        try:
            index = self.client.index(index_name)
            response = await index.search(
                query=query,
                limit=limit,
                offset=offset,
                filter=filter,
                sort=sort,
            )
            return {
                "hits": getattr(response, "hits", []),
                "total": getattr(response, "estimated_total_hits", 0)
                or getattr(response, "total_hits", 0),
                "limit": limit,
                "offset": offset,
                "query": query,
            }
        except (MeilisearchCommunicationError, MeilisearchApiError, Exception) as exc:
            logger.warning("Meilisearch search error on %s: %s", index_name, exc)
            return {
                "hits": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "query": query,
                "error": str(exc),
            }

    # Entity helper methods
    async def index_user(self, user_dict: Dict[str, Any]) -> bool:
        return await self.index_documents(INDEX_USERS, [user_dict])

    async def delete_user(self, user_id: Union[str, int]) -> bool:
        return await self.delete_document(INDEX_USERS, user_id)

    async def index_community(self, community_dict: Dict[str, Any]) -> bool:
        return await self.index_documents(INDEX_COMMUNITIES, [community_dict])

    async def delete_community(self, community_id: Union[str, int]) -> bool:
        return await self.delete_document(INDEX_COMMUNITIES, community_id)

    async def index_post(self, post_dict: Dict[str, Any]) -> bool:
        return await self.index_documents(INDEX_POSTS, [post_dict])

    async def delete_post(self, post_id: Union[str, int]) -> bool:
        return await self.delete_document(INDEX_POSTS, post_id)

    async def index_interest(self, interest_dict: Dict[str, Any]) -> bool:
        return await self.index_documents(INDEX_INTERESTS, [interest_dict])

    async def delete_interest(self, interest_id: Union[str, int]) -> bool:
        return await self.delete_document(INDEX_INTERESTS, interest_id)


# Global service instance
meilisearch_service = MeilisearchService()


async def init_meilisearch_indexes() -> None:
    """Helper shortcut to initialize all indexes."""
    await meilisearch_service.init_indexes()
