def test_create_task_and_list_with_filters(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    member = test_setup["member_user"]
    headers = auth_headers(pm, org.id)

    # 1. Create task
    task_payload = {
        "project_id": project.id,
        "title": "Build Authentication Flow",
        "description": "Implement JWT endpoints with token rotation",
        "assignee_id": member.id,
        "priority": "HIGH",
        "estimated_hours": 12.5,
    }
    create_resp = client.post("/api/v1/tasks", json=task_payload, headers=headers)
    assert create_resp.status_code == 201
    data = create_resp.json()["data"]
    assert data["title"] == "Build Authentication Flow"
    assert data["status"] == "TODO"
    assert data["assignee_id"] == member.id
    task_id = data["id"]

    # 2. Query tasks with filtering by priority and status
    list_resp = client.get(f"/api/v1/tasks?priority=HIGH&status=TODO", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["id"] == task_id

    # 3. Query with search filter
    search_resp = client.get(f"/api/v1/tasks?search=Authentication", headers=headers)
    assert search_resp.status_code == 200
    assert len(search_resp.json()["data"]["items"]) >= 1


def test_task_assignment_rules(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    viewer = test_setup["viewer_user"]
    beta_user = test_setup["beta_admin"]
    headers = auth_headers(pm, org.id)

    # Create base task
    task_resp = client.post(
        "/api/v1/tasks",
        json={"project_id": project.id, "title": "Base Task for Assignment"},
        headers=headers,
    )
    task_id = task_resp.json()["data"]["id"]

    # Rule 1: Assign to Viewer must fail
    viewer_assign_resp = client.patch(
        f"/api/v1/tasks/{task_id}/assign",
        json={"assignee_id": viewer.id},
        headers=headers,
    )
    assert viewer_assign_resp.status_code == 400
    assert viewer_assign_resp.json()["error"]["code"] == "VIEWER_ASSIGNMENT_FORBIDDEN"

    # Rule 2: Assign to user outside organization must fail
    cross_org_assign_resp = client.patch(
        f"/api/v1/tasks/{task_id}/assign",
        json={"assignee_id": beta_user.id},
        headers=headers,
    )
    assert cross_org_assign_resp.status_code == 400
    assert cross_org_assign_resp.json()["error"]["code"] == "INVALID_ASSIGNEE_ORGANIZATION"

    # Rule 3: Regular team member cannot assign task (only PM or Org Admin)
    member = test_setup["member_user"]
    member_headers = auth_headers(member, org.id)
    forbidden_assign = client.patch(
        f"/api/v1/tasks/{task_id}/assign",
        json={"assignee_id": member.id},
        headers=member_headers,
    )
    assert forbidden_assign.status_code == 403
    assert forbidden_assign.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


def test_viewer_cannot_create_task(client, test_setup, auth_headers):
    viewer = test_setup["viewer_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]

    headers = auth_headers(viewer, org.id)
    response = client.post(
        "/api/v1/tasks",
        json={"project_id": project.id, "title": "Viewer Task Attempt"},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"
