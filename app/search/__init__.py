"""Search module providing multi-domain search engine with Meilisearch and SQL fallback."""

from app.search.repository import SearchRepository, search_repository
from app.search.router import router as search_router
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
from app.search.service import SearchService, search_service

__all__ = [
    "SearchRepository",
    "search_repository",
    "SearchService",
    "search_service",
    "search_router",
    "UserSearchResult",
    "CommunitySearchResult",
    "PostSearchResult",
    "InterestSearchResult",
    "UnifiedSearchResponse",
    "PaginatedUserSearchResponse",
    "PaginatedCommunitySearchResponse",
    "PaginatedPostSearchResponse",
    "PaginatedInterestSearchResponse",
    "SyncIndexResponse",
]
