import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.users.models import Profile, User


async def create_user(async_client: AsyncClient, username: str, email: str):
    payload = {
        "email": email,
        "username": username,
        "password": "Password123!",
        "display_name": f"User {username}",
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
async def test_community_recommendations(async_client: AsyncClient, db_session: AsyncSession):
    admin = await create_admin_user(async_client, db_session, "recadmin", "recadmin@example.com")
    viewer = await create_user(async_client, "recviewer", "recviewer@example.com")
    other = await create_user(async_client, "recother", "recother@example.com")

    # 1. Create Interests
    int_gaming_resp = await async_client.post(
        "/api/v1/interests",
        headers=admin["headers"],
        json={"name": "Competitive Gaming", "slug": "competitive-gaming"},
    )
    assert int_gaming_resp.status_code == 201
    gaming_id = int_gaming_resp.json()["id"]

    int_photo_resp = await async_client.post(
        "/api/v1/interests",
        headers=admin["headers"],
        json={"name": "Outdoor Photography", "slug": "outdoor-photography"},
    )
    assert int_photo_resp.status_code == 201
    photo_id = int_photo_resp.json()["id"]

    # 2. Viewer selects Gaming interest
    await async_client.put(
        "/api/v1/profiles/me/interests",
        headers=viewer["headers"],
        json={"interest_ids": [gaming_id]},
    )

    # 3. Create 3 communities
    # Comm A: Gaming interest (not joined)
    comm_a = await async_client.post(
        "/api/v1/communities",
        headers=other["headers"],
        json={"name": "Esports Hub", "interest_id": gaming_id},
    )
    comm_a_id = comm_a.json()["id"]

    # Comm B: Photography interest (not joined)
    comm_b = await async_client.post(
        "/api/v1/communities",
        headers=other["headers"],
        json={"name": "Landscape Snaps", "interest_id": photo_id},
    )
    comm_b_id = comm_b.json()["id"]

    # Comm C: Gaming interest (joined by viewer)
    comm_c = await async_client.post(
        "/api/v1/communities",
        headers=other["headers"],
        json={"name": "Already Joined Clan", "interest_id": gaming_id},
    )
    comm_c_id = comm_c.json()["id"]
    await async_client.post(f"/api/v1/communities/{comm_c_id}/join", headers=viewer["headers"])

    # 4. Request Community Recommendations
    rec_resp = await async_client.get(
        "/api/v1/recommendations/communities",
        headers=viewer["headers"],
    )
    assert rec_resp.status_code == 200
    data = rec_resp.json()
    rec_ids = [c["id"] for c in data["items"]]

    # Comm A should be recommended, Comm C (already joined) should NOT be recommended
    assert comm_a_id in rec_ids
    assert comm_b_id in rec_ids
    assert comm_c_id not in rec_ids

    # Comm A should be flagged as matched interest
    comm_a_item = next(c for c in data["items"] if c["id"] == comm_a_id)
    assert comm_a_item["is_matched_interest"] is True
    assert comm_a_item["interest_name"] == "Competitive Gaming"


@pytest.mark.asyncio
async def test_user_recommendations_by_interest(async_client: AsyncClient, db_session: AsyncSession):
    admin = await create_admin_user(async_client, db_session, "recuadmin", "recuadmin@example.com")
    u_main = await create_user(async_client, "recumain", "recumain@example.com")
    u_two_match = await create_user(async_client, "recutwomatch", "recutwomatch@example.com")
    u_one_match = await create_user(async_client, "recuonematch", "recuonematch@example.com")
    u_zero_match = await create_user(async_client, "recuzeromatch", "recuzeromatch@example.com")
    u_followed = await create_user(async_client, "recufollowed", "recufollowed@example.com")
    u_blocked = await create_user(async_client, "recublocked", "recublocked@example.com")

    # 1. Create 3 Interests
    int1 = (await async_client.post(
        "/api/v1/interests",
        headers=admin["headers"],
        json={"name": "Software Engineering", "slug": "software-engineering"},
    )).json()["id"]

    int2 = (await async_client.post(
        "/api/v1/interests",
        headers=admin["headers"],
        json={"name": "Electronic Music", "slug": "electronic-music"},
    )).json()["id"]

    int3 = (await async_client.post(
        "/api/v1/interests",
        headers=admin["headers"],
        json={"name": "Culinary Arts", "slug": "culinary-arts"},
    )).json()["id"]

    # 2. Assign interests:
    # u_main: int1, int2
    await async_client.put("/api/v1/profiles/me/interests", headers=u_main["headers"], json={"interest_ids": [int1, int2]})

    # u_two_match: int1, int2
    await async_client.put("/api/v1/profiles/me/interests", headers=u_two_match["headers"], json={"interest_ids": [int1, int2]})

    # u_one_match: int1
    await async_client.put("/api/v1/profiles/me/interests", headers=u_one_match["headers"], json={"interest_ids": [int1]})

    # u_zero_match: int3
    await async_client.put("/api/v1/profiles/me/interests", headers=u_zero_match["headers"], json={"interest_ids": [int3]})

    # u_followed: int1, int2
    await async_client.put("/api/v1/profiles/me/interests", headers=u_followed["headers"], json={"interest_ids": [int1, int2]})
    # u_main follows u_followed
    await async_client.post(f"/api/v1/users/{u_followed['id']}/follow", headers=u_main["headers"])

    # u_blocked: int1, int2
    await async_client.put("/api/v1/profiles/me/interests", headers=u_blocked["headers"], json={"interest_ids": [int1, int2]})
    # u_main blocks u_blocked
    await async_client.post(f"/api/v1/users/{u_blocked['id']}/block", headers=u_main["headers"])

    # 3. Query Recommended Users
    rec_resp = await async_client.get("/api/v1/recommendations/users", headers=u_main["headers"])
    assert rec_resp.status_code == 200
    data = rec_resp.json()
    user_ids = [u["id"] for u in data["items"]]

    # u_two_match and u_one_match should be present
    assert u_two_match["id"] in user_ids
    assert u_one_match["id"] in user_ids

    # u_main (self), u_followed (already followed), and u_blocked (blocked) must NOT be recommended
    assert u_main["id"] not in user_ids
    assert u_followed["id"] not in user_ids
    assert u_blocked["id"] not in user_ids

    # Check mutual interest counts and ordering
    two_match_item = next(u for u in data["items"] if u["id"] == u_two_match["id"])
    one_match_item = next(u for u in data["items"] if u["id"] == u_one_match["id"])

    assert two_match_item["mutual_interest_count"] == 2
    assert len(two_match_item["shared_interests"]) == 2
    assert one_match_item["mutual_interest_count"] == 1

    # u_two_match should be ranked higher than u_one_match
    idx_two = user_ids.index(u_two_match["id"])
    idx_one = user_ids.index(u_one_match["id"])
    assert idx_two < idx_one
