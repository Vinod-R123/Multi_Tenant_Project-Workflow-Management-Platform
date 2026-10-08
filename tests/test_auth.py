def test_register_user_success(client):
    payload = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "Password123!",
        "full_name": "New User"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "newuser@example.com"
    assert data["data"]["username"] == "newuser"


def test_register_duplicate_email(client, test_setup):
    payload = {
        "email": "admin@alpha.com",
        "username": "different_uname",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_duplicate_username(client, test_setup):
    payload = {
        "email": "diff@example.com",
        "username": "alpha_admin",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "USERNAME_ALREADY_EXISTS"


def test_login_success(client, test_setup):
    payload = {
        "username_or_email": "alpha_admin",
        "password": "Password@123",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


def test_login_invalid_password(client, test_setup):
    payload = {
        "username_or_email": "alpha_admin",
        "password": "WrongPassword!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_inactive_user(client, test_setup):
    payload = {
        "username_or_email": "alpha_inactive",
        "password": "Password@123",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "USER_INACTIVE"


def test_token_refresh_and_rotation(client, test_setup):
    # 1. Login
    login_resp = client.post("/api/v1/auth/login", json={
        "username_or_email": "alpha_admin",
        "password": "Password@123",
    })
    refresh_token = login_resp.json()["data"]["refresh_token"]

    # 2. Refresh token
    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()["data"]
    new_refresh_token = new_data["refresh_token"]
    assert new_refresh_token != refresh_token

    # 3. Old refresh token should now be revoked (rotation)
    reused_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reused_resp.status_code == 401
    assert reused_resp.json()["error"]["code"] == "TOKEN_REVOKED"


def test_get_me_profile(client, test_setup, auth_headers):
    user = test_setup["admin_user"]
    org = test_setup["org_alpha"]
    headers = auth_headers(user, org.id)

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == user.username
    assert len(data["organizations"]) >= 1
    assert data["organizations"][0]["organization_name"] == org.name


def test_change_password(client, test_setup, auth_headers):
    user = test_setup["member_user"]
    headers = auth_headers(user)

    # Wrong old password
    bad_resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongOldPassword", "new_password": "NewSecretPassword123!"},
        headers=headers,
    )
    assert bad_resp.status_code == 401
    assert bad_resp.json()["error"]["code"] == "INVALID_CURRENT_PASSWORD"

    # Correct old password
    ok_resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Password@123", "new_password": "NewSecretPassword123!"},
        headers=headers,
    )
    assert ok_resp.status_code == 200

    # Login with new password
    new_login = client.post("/api/v1/auth/login", json={
        "username_or_email": user.username,
        "password": "NewSecretPassword123!"
    })
    assert new_login.status_code == 200
