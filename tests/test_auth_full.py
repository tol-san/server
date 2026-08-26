import pytest
from httpx import AsyncClient


@pytest.fixture
async def registered_user(async_client: AsyncClient):
    payload = {
        "email": "testauth@example.com",
        "username": "testauthuser",
        "password": "InitialPassword123!",
        "display_name": "Test Auth User",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return payload


@pytest.mark.asyncio
async def test_login_with_email_success(async_client: AsyncClient, registered_user: dict):
    payload = {
        "identifier": registered_user["email"],
        "password": registered_user["password"],
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["email"] == registered_user["email"]
    assert data["user"]["username"] == registered_user["username"]


@pytest.mark.asyncio
async def test_login_with_username_success(async_client: AsyncClient, registered_user: dict):
    payload = {
        "identifier": registered_user["username"],
        "password": registered_user["password"],
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, registered_user: dict):
    payload = {
        "identifier": registered_user["email"],
        "password": "WrongPassword123!",
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    payload = {
        "identifier": "nonexistent@example.com",
        "password": "SomePassword123!",
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_lifecycle(async_client: AsyncClient, registered_user: dict):
    # 1. Login
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": registered_user["email"], "password": registered_user["password"]},
    )
    tokens = login_resp.json()
    initial_refresh = tokens["refresh_token"]

    # 2. Refresh
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != initial_refresh

    # 3. Re-using old refresh token must fail (Token Rotation)
    stale_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert stale_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_token(async_client: AsyncClient, registered_user: dict):
    # 1. Login
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": registered_user["email"], "password": registered_user["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # 2. Logout
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Successfully logged out."

    # 3. Refresh with revoked token must fail
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_forgot_and_reset_password_workflow(async_client: AsyncClient, registered_user: dict):
    # 1. Request password reset
    forgot_resp = await async_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": registered_user["email"]},
    )
    assert forgot_resp.status_code == 200
    reset_token = forgot_resp.json()["reset_token"]
    assert reset_token is not None

    # 2. Reset password
    new_pwd = "BrandNewPassword456!"
    reset_resp = await async_client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": new_pwd},
    )
    assert reset_resp.status_code == 200

    # 3. Old password fails
    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": registered_user["email"], "password": registered_user["password"]},
    )
    assert old_login.status_code == 401

    # 4. New password succeeds
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": registered_user["email"], "password": new_pwd},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalid-token-value", "new_password": "NewPassword123!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_authenticated(async_client: AsyncClient, registered_user: dict):
    # 1. Login to get access token
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": registered_user["email"], "password": registered_user["password"]},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Change password
    new_pwd = "ChangedPassword789!"
    change_resp = await async_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": registered_user["password"],
            "new_password": new_pwd,
        },
    )
    assert change_resp.status_code == 200
    assert change_resp.json()["message"] == "Password changed successfully."

    # 3. Login with new password
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": registered_user["email"], "password": new_pwd},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(async_client: AsyncClient, registered_user: dict):
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"identifier": registered_user["email"], "password": registered_user["password"]},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    change_resp = await async_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "IncorrectCurrentPassword!",
            "new_password": "ChangedPassword789!",
        },
    )
    assert change_resp.status_code == 400
    assert change_resp.json()["error_code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_change_password_unauthenticated(async_client: AsyncClient):
    change_resp = await async_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "SomePassword123!",
            "new_password": "ChangedPassword789!",
        },
    )
    assert change_resp.status_code == 401
