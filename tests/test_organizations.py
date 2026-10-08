def test_create_organization(client, test_setup, auth_headers):
    user = test_setup["member_user"]
    headers = auth_headers(user)

    response = client.post(
        "/api/v1/organizations",
        json={"name": "Delta Technologies", "description": "Cutting edge AI systems"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Delta Technologies"
    assert "delta-technologies" in data["slug"]

    # Creator should be listed as admin in their new org
    members_resp = client.get(f"/api/v1/organizations/{data['id']}/members", headers=auth_headers(user, data["id"]))
    assert members_resp.status_code == 200
    members = members_resp.json()["data"]["items"]
    assert len(members) == 1
    assert members[0]["role"] == "ORGANIZATION_ADMIN"


def test_add_member_authorized(client, test_setup, auth_headers):
    admin = test_setup["admin_user"]
    org = test_setup["org_alpha"]
    beta_user = test_setup["beta_admin"]  # user exists, not in org_alpha

    headers = auth_headers(admin, org.id)
    response = client.post(
        f"/api/v1/organizations/{org.id}/members",
        json={"user_id": beta_user.id, "role": "TEAM_MEMBER"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["role"] == "TEAM_MEMBER"
    assert data["user_id"] == beta_user.id


def test_add_member_forbidden_for_regular_member(client, test_setup, auth_headers):
    member = test_setup["member_user"]
    org = test_setup["org_alpha"]
    beta_user = test_setup["beta_admin"]

    headers = auth_headers(member, org.id)
    response = client.post(
        f"/api/v1/organizations/{org.id}/members",
        json={"user_id": beta_user.id, "role": "TEAM_MEMBER"},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


def test_add_member_duplicate_conflict(client, test_setup, auth_headers):
    admin = test_setup["admin_user"]
    org = test_setup["org_alpha"]
    member = test_setup["member_user"]

    headers = auth_headers(admin, org.id)
    response = client.post(
        f"/api/v1/organizations/{org.id}/members",
        json={"user_id": member.id, "role": "TEAM_MEMBER"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_MEMBERSHIP"


def test_add_inactive_user_failure(client, test_setup, auth_headers):
    admin = test_setup["admin_user"]
    org = test_setup["org_alpha"]
    inactive_user = test_setup["inactive_user"]

    headers = auth_headers(admin, org.id)
    response = client.post(
        f"/api/v1/organizations/{org.id}/members",
        json={"user_id": inactive_user.id, "role": "TEAM_MEMBER"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "USER_INACTIVE"


def test_update_member_role(client, test_setup, auth_headers):
    admin = test_setup["admin_user"]
    org = test_setup["org_alpha"]
    member = test_setup["member_user"]

    headers = auth_headers(admin, org.id)
    response = client.patch(
        f"/api/v1/organizations/{org.id}/members/{member.id}/role",
        json={"role": "PROJECT_MANAGER"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "PROJECT_MANAGER"


def test_self_removal_forbidden(client, test_setup, auth_headers):
    admin = test_setup["admin_user"]
    org = test_setup["org_alpha"]

    headers = auth_headers(admin, org.id)
    response = client.delete(
        f"/api/v1/organizations/{org.id}/members/{admin.id}",
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SELF_REMOVAL_FORBIDDEN"
