"""Unit and integration tests for Meilisearch integration and service."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core import (
    INDEX_COMMUNITIES,
    INDEX_CONFIGURATIONS,
    INDEX_INTERESTS,
    INDEX_POSTS,
    INDEX_USERS,
    MeilisearchService,
    close_meilisearch,
    get_meilisearch_client,
    init_meilisearch_indexes,
    meilisearch_service,
    settings,
)
from meilisearch_python_sdk.errors import MeilisearchCommunicationError


@pytest.mark.asyncio
async def test_meilisearch_client_singleton():
    """Test that get_meilisearch_client returns a singleton instance and close_meilisearch clears it."""
    client1 = get_meilisearch_client()
    client2 = get_meilisearch_client()
    assert client1 is client2

    await close_meilisearch()
    # After close, getting client returns a new instance
    client3 = get_meilisearch_client()
    assert client3 is not None
    await close_meilisearch()


def test_index_configurations():
    """Test that all required indexes and schemas are predefined."""
    assert INDEX_USERS in INDEX_CONFIGURATIONS
    assert INDEX_COMMUNITIES in INDEX_CONFIGURATIONS
    assert INDEX_POSTS in INDEX_CONFIGURATIONS
    assert INDEX_INTERESTS in INDEX_CONFIGURATIONS

    users_cfg = INDEX_CONFIGURATIONS[INDEX_USERS]
    assert "username" in users_cfg["searchable_attributes"]
    assert "id" in users_cfg["filterable_attributes"]

    posts_cfg = INDEX_CONFIGURATIONS[INDEX_POSTS]
    assert "title" in posts_cfg["searchable_attributes"]
    assert "content" in posts_cfg["searchable_attributes"]
    assert "created_at" in posts_cfg["sortable_attributes"]


@pytest.mark.asyncio
async def test_meilisearch_health_check_success():
    """Test health check when Meilisearch is available."""
    mock_client = MagicMock()
    mock_health = MagicMock()
    mock_health.status = "available"
    mock_client.health = AsyncMock(return_value=mock_health)

    service = MeilisearchService(client_factory=lambda: mock_client)
    assert await service.is_healthy() is True


@pytest.mark.asyncio
async def test_meilisearch_health_check_failure():
    """Test health check when Meilisearch is unreachable."""
    mock_client = MagicMock()
    mock_client.health = AsyncMock(side_effect=Exception("Connection refused"))

    service = MeilisearchService(client_factory=lambda: mock_client)
    assert await service.is_healthy() is False


@pytest.mark.asyncio
async def test_init_indexes():
    """Test index initialization creates all configured indexes with attributes."""
    mock_client = MagicMock()
    mock_index = MagicMock()
    mock_index.update_searchable_attributes = AsyncMock()
    mock_index.update_filterable_attributes = AsyncMock()
    mock_index.update_sortable_attributes = AsyncMock()

    mock_client.get_or_create_index = AsyncMock(return_value=mock_index)

    service = MeilisearchService(client_factory=lambda: mock_client)
    await service.init_indexes()

    assert mock_client.get_or_create_index.call_count == len(INDEX_CONFIGURATIONS)
    assert mock_index.update_searchable_attributes.call_count == len(INDEX_CONFIGURATIONS)


@pytest.mark.asyncio
async def test_index_and_delete_documents():
    """Test indexing and deleting documents via MeilisearchService."""
    mock_client = MagicMock()
    mock_index = MagicMock()
    mock_index.add_documents = AsyncMock()
    mock_index.delete_documents = AsyncMock()
    mock_index.delete_document = AsyncMock()

    mock_client.index = MagicMock(return_value=mock_index)

    service = MeilisearchService(client_factory=lambda: mock_client)

    # Test indexing
    test_docs = [{"id": "user_1", "username": "alex", "display_name": "Alex"}]
    res = await service.index_documents(INDEX_USERS, test_docs)
    assert res is True
    mock_index.add_documents.assert_awaited_once_with(test_docs, primary_key="id")

    # Test delete single
    res = await service.delete_document(INDEX_USERS, "user_1")
    assert res is True
    mock_index.delete_document.assert_awaited_once_with("user_1")

    # Test delete multiple
    res = await service.delete_documents(INDEX_USERS, ["user_1", "user_2"])
    assert res is True
    mock_index.delete_documents.assert_awaited_once_with(["user_1", "user_2"])


@pytest.mark.asyncio
async def test_search_documents():
    """Test search method returns structured output."""
    mock_client = MagicMock()
    mock_index = MagicMock()
    mock_search_res = MagicMock()
    mock_search_res.hits = [{"id": "post_1", "title": "Cool Tech Post"}]
    mock_search_res.estimated_total_hits = 1
    mock_index.search = AsyncMock(return_value=mock_search_res)

    mock_client.index = MagicMock(return_value=mock_index)

    service = MeilisearchService(client_factory=lambda: mock_client)
    result = await service.search(INDEX_POSTS, query="Cool", limit=10, offset=0)

    assert result["hits"] == [{"id": "post_1", "title": "Cool Tech Post"}]
    assert result["total"] == 1
    assert result["limit"] == 10
    assert result["query"] == "Cool"


@pytest.mark.asyncio
async def test_search_fallback_on_error():
    """Test search gracefully catches errors and returns an empty list without raising."""
    mock_client = MagicMock()
    mock_index = MagicMock()
    mock_index.search = AsyncMock(side_effect=Exception("Meilisearch server down"))
    mock_client.index = MagicMock(return_value=mock_index)

    service = MeilisearchService(client_factory=lambda: mock_client)
    result = await service.search(INDEX_POSTS, query="Cool")

    assert result["hits"] == []
    assert result["total"] == 0
    assert "error" in result


@pytest.mark.asyncio
async def test_convenience_helpers():
    """Test user, post, community, and interest helper methods."""
    mock_client = MagicMock()
    mock_index = MagicMock()
    mock_index.add_documents = AsyncMock()
    mock_index.delete_document = AsyncMock()
    mock_client.index = MagicMock(return_value=mock_index)

    service = MeilisearchService(client_factory=lambda: mock_client)

    await service.index_user({"id": "1", "username": "test"})
    await service.delete_user("1")
    await service.index_community({"id": "2", "name": "coding"})
    await service.delete_community("2")
    await service.index_post({"id": "3", "title": "hello"})
    await service.delete_post("3")
    await service.index_interest({"id": "4", "name": "gaming"})
    await service.delete_interest("4")

    assert mock_index.add_documents.call_count == 4
    assert mock_index.delete_document.call_count == 4
