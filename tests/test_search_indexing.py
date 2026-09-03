"""Tests verifying write-path Meilisearch indexing hooks.

These tests work against the SQL fallback (since the CI / test environment runs
Meilisearch optionally), but they also verify the API contract so that when
Meilisearch IS running, results are consistent with what the search endpoint returns.

The strategy:
- Create entities (users, posts, communities) through the API.
- Immediately query the search endpoint.
- Assert the entity appears (SQL fallback always works even if Meili is down).
- Where possible, assert the enriched fields (thumbnail_url, author_avatar_url)
  exist in the response when the post has media.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.users.models import Profile, User


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _register_and_login(
    async_client: AsyncClient, username: str, email: str
) -> dict:
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "Password123!",
            "display_name": f"Display {username}",
        },
    )
    assert reg.status_code == 201, reg.text
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "Password123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"id": reg.json()["id"], "username": username, "headers": {"Authorization": f"Bearer {token}"}}


async def _make_admin(
    async_client: AsyncClient, db: AsyncSession, username: str, email: str
) -> dict:
    admin_user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        is_superuser=True,
    )
    db.add(admin_user)
    await db.flush()
    db.add(Profile(user_id=admin_user.id, display_name=f"Admin {username}"))
    await db.commit()

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "AdminPass123!"},
    )
    assert login.status_code == 200, login.text
    return {
        "id": str(admin_user.id),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test: user indexed on registration
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_indexed_on_registration(async_client: AsyncClient):
    """Registering a new user makes them immediately findable via search."""
    rand = uuid.uuid4().hex[:8]
    username = f"indexed_user_{rand}"
    user = await _register_and_login(
        async_client, username, f"{username}@example.com"
    )

    resp = await async_client.get(
        f"/api/v1/search/users?q={username}",
        headers=user["headers"],
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert any(u["username"] == username for u in items), (
        f"Registered user '{username}' not found in search results: {items}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: post indexed on creation, includes enriched fields
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_indexed_on_creation(async_client: AsyncClient):
    """Creating a public text post makes it searchable; response includes author_username."""
    rand = uuid.uuid4().hex[:8]
    user = await _register_and_login(
        async_client, f"postidx_{rand}", f"postidx_{rand}@example.com"
    )
    keyword = f"MeiliKeyword{rand}"

    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json={
            "post_type": "text",
            "title": f"Meilisearch Integration {keyword}",
            "content": "Testing real-time indexing pipeline",
            "visibility": "public",
        },
    )
    assert post_resp.status_code == 201, post_resp.text
    post_id = post_resp.json()["id"]

    search_resp = await async_client.get(
        f"/api/v1/search/posts?q={keyword}",
        headers=user["headers"],
    )
    assert search_resp.status_code == 200, search_resp.text
    items = search_resp.json()["items"]
    assert any(p["id"] == post_id for p in items), (
        f"Post '{post_id}' not found in search results: {items}"
    )
    # Verify the author_username enrichment from the new schema
    matched = next(p for p in items if p["id"] == post_id)
    assert matched["author_username"] == user["username"]
    # thumbnail_url should be absent for a text post
    assert matched.get("thumbnail_url") is None


# ─────────────────────────────────────────────────────────────────────────────
# Test: post removed from search on deletion
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_removed_on_delete(async_client: AsyncClient):
    """Deleting a post removes it from search results."""
    rand = uuid.uuid4().hex[:8]
    user = await _register_and_login(
        async_client, f"delpostidx_{rand}", f"delpostidx_{rand}@example.com"
    )
    keyword = f"DeleteKeyword{rand}"

    create = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json={
            "post_type": "text",
            "title": keyword,
            "content": "Will be deleted",
            "visibility": "public",
        },
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    # Verify it's searchable before deletion
    before = await async_client.get(
        f"/api/v1/search/posts?q={keyword}", headers=user["headers"]
    )
    assert before.status_code == 200
    assert any(p["id"] == post_id for p in before.json()["items"])

    # Delete
    del_resp = await async_client.delete(
        f"/api/v1/posts/{post_id}", headers=user["headers"]
    )
    assert del_resp.status_code == 200, del_resp.text

    # Verify it no longer appears (SQL fallback will also not return it)
    after = await async_client.get(
        f"/api/v1/search/posts?q={keyword}", headers=user["headers"]
    )
    assert after.status_code == 200
    assert not any(p["id"] == post_id for p in after.json()["items"]), (
        f"Deleted post '{post_id}' still appeared in search: {after.json()['items']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: private community posts excluded from search
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_private_community_posts_excluded(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Posts in a community that becomes private are hidden from post search for non-members."""
    rand = uuid.uuid4().hex[:8]
    owner = await _register_and_login(
        async_client, f"privowner_{rand}", f"privowner_{rand}@example.com"
    )
    viewer = await _register_and_login(
        async_client, f"privviewer_{rand}", f"privviewer_{rand}@example.com"
    )
    keyword = f"PrivateContent{rand}"

    # Create a public community and post
    comm = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={"name": f"PrivComm {rand}", "description": "Will go private"},
    )
    assert comm.status_code == 201, comm.text
    comm_id = comm.json()["id"]

    post = await async_client.post(
        "/api/v1/posts",
        headers=owner["headers"],
        json={
            "post_type": "text",
            "title": keyword,
            "content": "Sensitive community content",
            "visibility": "public",
            "community_id": comm_id,
        },
    )
    assert post.status_code == 201, post.text
    post_id = post.json()["id"]

    # Post is findable before community is private
    before = await async_client.get(
        f"/api/v1/search/posts?q={keyword}", headers=viewer["headers"]
    )
    assert before.status_code == 200
    assert any(p["id"] == post_id for p in before.json()["items"])

    # Make community private
    patch = await async_client.patch(
        f"/api/v1/communities/{comm_id}",
        headers=owner["headers"],
        json={"is_private": True},
    )
    assert patch.status_code == 200, patch.text

    # Non-member viewer can no longer find the post
    after = await async_client.get(
        f"/api/v1/search/posts?q={keyword}", headers=viewer["headers"]
    )
    assert after.status_code == 200
    assert not any(p["id"] == post_id for p in after.json()["items"]), (
        f"Post from now-private community '{comm_id}' still visible in search"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: community indexed on creation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_community_indexed_on_creation(async_client: AsyncClient):
    """A newly created public community appears in community search."""
    rand = uuid.uuid4().hex[:8]
    user = await _register_and_login(
        async_client, f"commidx_{rand}", f"commidx_{rand}@example.com"
    )
    comm_name = f"MeiliTestComm {rand}"

    create = await async_client.post(
        "/api/v1/communities",
        headers=user["headers"],
        json={"name": comm_name, "description": "Integration test community"},
    )
    assert create.status_code == 201, create.text
    comm_id = create.json()["id"]

    search = await async_client.get(
        f"/api/v1/search/communities?q={rand}",
        headers=user["headers"],
    )
    assert search.status_code == 200, search.text
    items = search.json()["items"]
    assert any(c["id"] == comm_id for c in items), (
        f"Community '{comm_id}' not found in search: {items}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: enriched unified search response schema
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unified_search_enriched_post_fields(async_client: AsyncClient):
    """Unified search returns the enriched PostSearchResult schema (author_username present)."""
    rand = uuid.uuid4().hex[:8]
    user = await _register_and_login(
        async_client, f"enriched_{rand}", f"enriched_{rand}@example.com"
    )
    keyword = f"EnrichedPost{rand}"

    await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json={
            "post_type": "text",
            "title": keyword,
            "content": "Test enriched unified search fields",
            "visibility": "public",
        },
    )

    resp = await async_client.get(
        f"/api/v1/search?q={keyword}",
        headers=user["headers"],
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "posts" in data
    if data["posts"]:
        post = data["posts"][0]
        assert "author_username" in post
        assert "author_avatar_url" in post  # field exists (may be null)
        assert "thumbnail_url" in post       # field exists (null for text)
        assert "highlight" in post           # field exists (may be null or dict)
