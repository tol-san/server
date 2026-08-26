import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.users.models import Profile, User


@pytest.fixture
async def authenticated_user(async_client: AsyncClient):
    payload = {
        "email": "interestsuser@example.com",
        "username": "interestsuser",
        "password": "Password123!",
        "display_name": "Interest Fan",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": payload["email"], "password": payload["password"]},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return {"id": user_id, "headers": headers}


@pytest.fixture
async def superuser(async_client: AsyncClient, db_session: AsyncSession):
    admin_user = User(
        email="admin@example.com",
        username="superadmin",
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    admin_profile = Profile(
        user_id=admin_user.id,
        display_name="Super Admin",
    )
    db_session.add(admin_profile)
    await db_session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@example.com", "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    return {"id": admin_user.id, "headers": headers}


@pytest.mark.asyncio
async def test_list_interests_catalog(async_client: AsyncClient):
    response = await async_client.get("/api/v1/interests")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_create_interest_as_superuser(async_client: AsyncClient, superuser: dict):
    new_interest_payload = {
        "name": "Robotics & Hardware",
        "description": "Drones, microcontrollers, circuits, and robots",
    }
    response = await async_client.post(
        "/api/v1/interests",
        headers=superuser["headers"],
        json=new_interest_payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Robotics & Hardware"
    assert data["slug"] == "robotics-hardware"
    assert data["description"] == new_interest_payload["description"]


@pytest.mark.asyncio
async def test_create_interest_as_normal_user_forbidden(async_client: AsyncClient, authenticated_user: dict):
    payload = {"name": "Unauthorized Category"}
    response = await async_client.post(
        "/api/v1/interests",
        headers=authenticated_user["headers"],
        json=payload,
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_user_interests_lifecycle(async_client: AsyncClient, authenticated_user: dict, superuser: dict):
    # 1. Create 2 test categories
    c1_resp = await async_client.post(
        "/api/v1/interests",
        headers=superuser["headers"],
        json={"name": "K-Pop & Beats", "slug": "kpop-beats"},
    )
    c1_id = c1_resp.json()["id"]

    c2_resp = await async_client.post(
        "/api/v1/interests",
        headers=superuser["headers"],
        json={"name": "Skateboarding", "slug": "skateboarding"},
    )
    c2_id = c2_resp.json()["id"]

    # 2. Check user's initial interests -> empty
    init_resp = await async_client.get("/api/v1/profiles/me/interests", headers=authenticated_user["headers"])
    assert init_resp.status_code == 200
    assert init_resp.json()["total"] == 0

    # 3. Assign 2 interests
    update_resp = await async_client.put(
        "/api/v1/profiles/me/interests",
        headers=authenticated_user["headers"],
        json={"interest_ids": [c1_id, c2_id]},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["total"] == 2
    slugs = [item["slug"] for item in data["items"]]
    assert "kpop-beats" in slugs
    assert "skateboarding" in slugs

    # 4. Verify GET /profiles/me/interests matches
    get_resp = await async_client.get("/api/v1/profiles/me/interests", headers=authenticated_user["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["total"] == 2

    # 5. Replace interests with single category
    replace_resp = await async_client.put(
        "/api/v1/profiles/me/interests",
        headers=authenticated_user["headers"],
        json={"interest_ids": [c1_id]},
    )
    assert replace_resp.status_code == 200
    assert replace_resp.json()["total"] == 1
    assert replace_resp.json()["items"][0]["id"] == c1_id


@pytest.mark.asyncio
async def test_update_user_interests_invalid_id(async_client: AsyncClient, authenticated_user: dict):
    fake_id = str(uuid.uuid4())
    response = await async_client.put(
        "/api/v1/profiles/me/interests",
        headers=authenticated_user["headers"],
        json={"interest_ids": [fake_id]},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_user_interests_unauthenticated(async_client: AsyncClient):
    get_resp = await async_client.get("/api/v1/profiles/me/interests")
    assert get_resp.status_code == 401

    put_resp = await async_client.put("/api/v1/profiles/me/interests", json={"interest_ids": []})
    assert put_resp.status_code == 401
