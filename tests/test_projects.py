def test_create_project_authorized(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    headers = auth_headers(pm, org.id)

    response = client.post(
        "/api/v1/projects",
        json={"name": "New Alpha Project", "description": "Project Alpha description", "status": "PLANNING"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "New Alpha Project"
    assert data["status"] == "PLANNING"
    assert data["owner_id"] == pm.id


def test_create_project_forbidden_for_viewer(client, test_setup, auth_headers):
    viewer = test_setup["viewer_user"]
    org = test_setup["org_alpha"]
    headers = auth_headers(viewer, org.id)

    response = client.post(
        "/api/v1/projects",
        json={"name": "Viewer Project"},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


def test_project_valid_and_invalid_status_transitions(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    headers = auth_headers(pm, org.id)

    # 1. Create project in PLANNING
    create_resp = client.post(
        "/api/v1/projects",
        json={"name": "Transition Test Project", "status": "PLANNING"},
        headers=headers,
    )
    proj_id = create_resp.json()["data"]["id"]

    # 2. Invalid Transition: PLANNING -> COMPLETED directly
    bad_resp = client.put(
        f"/api/v1/projects/{proj_id}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert bad_resp.status_code == 400
    assert bad_resp.json()["error"]["code"] == "INVALID_PROJECT_STATUS_TRANSITION"

    # 3. Valid Transition: PLANNING -> ACTIVE
    ok_resp = client.put(
        f"/api/v1/projects/{proj_id}",
        json={"status": "ACTIVE"},
        headers=headers,
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["data"]["status"] == "ACTIVE"

    # 4. Valid Transition: ACTIVE -> COMPLETED
    ok_resp2 = client.put(
        f"/api/v1/projects/{proj_id}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert ok_resp2.status_code == 200
    assert ok_resp2.json()["data"]["status"] == "COMPLETED"


def test_add_project_member_requires_organization_membership(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    beta_user = test_setup["beta_admin"]  # Exists in DB, but not in org_alpha

    headers = auth_headers(pm, org.id)
    response = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"user_id": beta_user.id},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "USER_NOT_IN_ORGANIZATION"


def test_add_project_member_duplicate_conflict(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    member = test_setup["member_user"]  # Already added in fixture

    headers = auth_headers(pm, org.id)
    response = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"user_id": member.id},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_PROJECT_MEMBERSHIP"


def test_delete_project_permissions(client, test_setup, auth_headers):
    member = test_setup["member_user"]
    admin = test_setup["admin_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]

    # Member cannot delete project
    bad_resp = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(member, org.id))
    assert bad_resp.status_code == 403
    assert bad_resp.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # Admin can delete project
    ok_resp = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers(admin, org.id))
    assert ok_resp.status_code == 200
    assert ok_resp.json()["success"] is True
