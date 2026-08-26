import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.users.models import Profile, User


async def create_user(async_client: AsyncClient, username: str, email: str, display_name: str = None):
    payload = {
        "email": email,
        "username": username,
        "password": "Password123!",
        "display_name": display_name or f"User {username}",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return {"id": user_id, "username": username, "headers": headers}


async def create_admin_user(async_client: AsyncClient, db_session: AsyncSession, username: str, email: str):
    admin_user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    admin_profile = Profile(
        user_id=admin_user.id,
        display_name=f"Admin {username}",
    )
    db_session.add(admin_profile)
    await db_session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return {"id": admin_user.id, "username": username, "headers": headers}


@pytest.mark.asyncio
async def test_unified_search_across_all_entities(async_client: AsyncClient, db_session: AsyncSession):
    admin = await create_admin_user(async_client, db_session, "searchadmin", "searchadmin@example.com")
    creator = await create_user(async_client, "cyberpunk_dev", "cyberdev@example.com", "Cyber Specialist")
    viewer = await create_user(async_client, "searchview_user", "searchview@example.com")

    # 1. Create Interest with "Cyber"
    int_resp = await async_client.post(
        "/api/v1/interests",
        headers=admin["headers"],
        json={"name": "Cyber Security", "slug": "cyber-security", "description": "InfoSec and ethical hacking"},
    )
    assert int_resp.status_code == 201

    # 2. Create Community with "Cyber"
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=creator["headers"],
        json={"name": "Cyber Defense Network", "description": "Hub for cyber analysts"},
    )
    assert comm_resp.status_code == 201

    # 3. Create Post with "Cyber"
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=creator["headers"],
        json={"post_type": "text", "title": "Cyber Trends 2026", "content": "Exploring cyber threats and defenses"},
    )
    assert post_resp.status_code == 201

    # 4. Perform Unified Search for "cyber"
    search_resp = await async_client.get("/api/v1/search?q=cyber", headers=viewer["headers"])
    assert search_resp.status_code == 200
    data = search_resp.json()

    assert data["query"] == "cyber"
    assert len(data["users"]) >= 1
    assert any("cyberpunk" in u["username"] or "Cyber" in (u["display_name"] or "") for u in data["users"])

    assert len(data["communities"]) >= 1
    assert any("Cyber Defense" in c["name"] for c in data["communities"])

    assert len(data["posts"]) >= 1
    assert any("Cyber Trends" in p["title"] for p in data["posts"])

    assert len(data["interests"]) >= 1
    assert any("Cyber Security" in i["name"] for i in data["interests"])


@pytest.mark.asyncio
async def test_domain_specific_search_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    admin = await create_admin_user(async_client, db_session, "searchadmin2", "searchadmin2@example.com")
    user = await create_user(async_client, "matrix_neo", "neo@example.com", "Thomas Anderson")

    # 1. Search Users endpoint
    users_resp = await async_client.get("/api/v1/search/users?q=matrix", headers=user["headers"])
    assert users_resp.status_code == 200
    assert any(u["username"] == "matrix_neo" for u in users_resp.json()["items"])

    # 2. Search Communities endpoint
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=user["headers"],
        json={"name": "Matrix Operatives", "description": "Construct hacking"},
    )
    assert comm_resp.status_code == 201

    comm_search = await async_client.get("/api/v1/search/communities?q=Operatives", headers=user["headers"])
    assert comm_search.status_code == 200
    assert any(c["name"] == "Matrix Operatives" for c in comm_search.json()["items"])

    # 3. Search Posts endpoint
    post_resp = await async_client.post(
        "/api/v1/posts",
        headers=user["headers"],
        json={"post_type": "text", "title": "Red Pill or Blue Pill?", "content": "Wake up to reality"},
    )
    assert post_resp.status_code == 201

    post_search = await async_client.get("/api/v1/search/posts?q=Blue+Pill", headers=user["headers"])
    assert post_search.status_code == 200
    assert any("Blue Pill" in p["title"] for p in post_search.json()["items"])

    # 4. Search Interests endpoint
    await async_client.post(
        "/api/v1/interests",
        headers=admin["headers"],
        json={"name": "Virtual Reality Simulation", "slug": "vr-sim"},
    )
    int_search = await async_client.get("/api/v1/search/interests?q=Simulation", headers=user["headers"])
    assert int_search.status_code == 200
    assert any("Simulation" in i["name"] for i in int_search.json()["items"])


@pytest.mark.asyncio
async def test_search_type_filter_param(async_client: AsyncClient, db_session: AsyncSession):
    user = await create_user(async_client, "filteruser", "filteruser@example.com")

    # Search with ?type=users
    resp = await async_client.get("/api/v1/search?q=filteruser&type=users", headers=user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert any(u["username"] == "filteruser" for u in data["items"])

    # Search with invalid type
    bad_resp = await async_client.get("/api/v1/search?q=test&type=invalid_domain", headers=user["headers"])
    assert bad_resp.status_code == 400


@pytest.mark.asyncio
async def test_search_block_safety(async_client: AsyncClient):
    user1 = await create_user(async_client, "safetyuser1", "safety1@example.com")
    user2 = await create_user(async_client, "safetyuser2", "safety2@example.com")

    # User2 creates a post
    await async_client.post(
        "/api/v1/posts",
        headers=user2["headers"],
        json={"post_type": "text", "title": "Confidential Research Project", "content": "Top secret"},
    )

    # Before block: User1 can find User2's post
    before_resp = await async_client.get("/api/v1/search/posts?q=Confidential", headers=user1["headers"])
    assert before_resp.status_code == 200
    assert any("Confidential" in p["title"] for p in before_resp.json()["items"])

    # User1 blocks User2
    await async_client.post(f"/api/v1/users/{user2['id']}/block", headers=user1["headers"])

    # After block: User1 CANNOT find User2 in user search or post search
    after_post = await async_client.get("/api/v1/search/posts?q=Confidential", headers=user1["headers"])
    assert after_post.status_code == 200
    assert not any("Confidential" in p["title"] for p in after_post.json()["items"])

    after_user = await async_client.get("/api/v1/search/users?q=safetyuser2", headers=user1["headers"])
    assert after_user.status_code == 200
    assert not any(u["username"] == "safetyuser2" for u in after_user.json()["items"])


@pytest.mark.asyncio
async def test_admin_search_sync_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    regular_user = await create_user(async_client, "regsyncuser", "regsync@example.com")
    admin = await create_admin_user(async_client, db_session, "adminsyncuser", "adminsync@example.com")

    # Regular user attempting sync -> 403 Forbidden
    reg_resp = await async_client.post("/api/v1/search/sync", headers=regular_user["headers"])
    assert reg_resp.status_code == 403

    # Superuser attempting sync -> 200 OK
    admin_resp = await async_client.post("/api/v1/search/sync", headers=admin["headers"])
    assert admin_resp.status_code == 200
    data = admin_resp.json()
    assert "synced_users" in data
    assert "synced_communities" in data
    assert "synced_posts" in data
    assert "synced_interests" in data
