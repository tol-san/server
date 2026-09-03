import pytest
from httpx import AsyncClient


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
    return {"id": user_id, "username": username, "token": token, "headers": headers}


@pytest.mark.asyncio
async def test_deactivate_account(async_client: AsyncClient):
    user = await create_user(async_client, "deact_user", "deact@example.com")

    # 1. Invalid password
    bad_resp = await async_client.post(
        "/api/v1/users/me/deactivate",
        headers=user["headers"],
        json={"password": "WrongPassword!"},
    )
    assert bad_resp.status_code == 422

    # 2. Correct password deactivates
    ok_resp = await async_client.post(
        "/api/v1/users/me/deactivate",
        headers=user["headers"],
        json={"password": "Password123!", "reason": "Taking a break"},
    )
    assert ok_resp.status_code == 200
    assert "deactivated" in ok_resp.json()["message"]

    # 3. Subsequent login is forbidden
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "deact@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_account_validation_and_success(async_client: AsyncClient):
    user = await create_user(async_client, "del_user", "del@example.com")

    # 1. Bad confirmation string
    bad_conf = await async_client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=user["headers"],
        json={"password": "Password123!", "confirmation": "NO"},
    )
    assert bad_conf.status_code == 422

    # 2. Wrong password
    bad_pwd = await async_client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=user["headers"],
        json={"password": "WrongPassword!", "confirmation": "DELETE"},
    )
    assert bad_pwd.status_code == 422

    # 3. Valid deletion
    ok_del = await async_client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=user["headers"],
        json={"password": "Password123!", "confirmation": "DELETE"},
    )
    assert ok_del.status_code == 200
    assert "deleted" in ok_del.json()["message"]

    # 4. Subsequent login fails because user no longer exists
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": "del@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_blocked_if_sole_owner_with_members(async_client: AsyncClient):
    owner = await create_user(async_client, "owner_user", "owner@example.com")
    member = await create_user(async_client, "member_user", "member@example.com")

    # Owner creates a community
    comm_resp = await async_client.post(
        "/api/v1/communities",
        headers=owner["headers"],
        json={
            "name": "Super Community",
            "slug": "super-community",
            "description": "An active community with members",
        },
    )
    assert comm_resp.status_code == 201
    comm_id = comm_resp.json()["id"]

    # Member joins community
    join_resp = await async_client.post(
        f"/api/v1/communities/{comm_id}/join",
        headers=member["headers"],
    )
    assert join_resp.status_code == 200


    # Owner attempts to delete account -> should be blocked with 409 Conflict
    del_resp = await async_client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=owner["headers"],
        json={"password": "Password123!", "confirmation": "DELETE"},
    )
    assert del_resp.status_code == 409
    assert "sole owner" in del_resp.json()["detail"].lower()
