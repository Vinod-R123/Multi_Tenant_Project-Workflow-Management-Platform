def test_task_valid_workflow_progression(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    headers = auth_headers(pm, org.id)

    # 1. Create task (default status is TODO)
    create_resp = client.post(
        "/api/v1/tasks",
        json={"project_id": project.id, "title": "Workflow Test Task"},
        headers=headers,
    )
    task_id = create_resp.json()["data"]["id"]

    # 2. Transition TODO -> IN_PROGRESS
    r1 = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["data"]["status"] == "IN_PROGRESS"

    # 3. Transition IN_PROGRESS -> REVIEW
    r2 = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "REVIEW"}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "REVIEW"

    # 4. Transition REVIEW -> DONE
    r3 = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "DONE"}, headers=headers)
    assert r3.status_code == 200
    assert r3.json()["data"]["status"] == "DONE"


def test_task_invalid_workflow_transitions(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    headers = auth_headers(pm, org.id)

    # Create task (status TODO)
    create_resp = client.post(
        "/api/v1/tasks",
        json={"project_id": project.id, "title": "Invalid Transition Test"},
        headers=headers,
    )
    task_id = create_resp.json()["data"]["id"]

    # Invalid: TODO -> DONE directly without IN_PROGRESS / REVIEW
    bad_resp = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "DONE"}, headers=headers)
    assert bad_resp.status_code == 400
    assert bad_resp.json()["error"]["code"] == "INVALID_TASK_STATUS_TRANSITION"

    # Invalid: Move to IN_PROGRESS, then attempt invalid transition IN_PROGRESS -> BACKLOG
    client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    bad_resp2 = client.patch(f"/api/v1/tasks/{task_id}/status", json={"status": "BACKLOG"}, headers=headers)
    assert bad_resp2.status_code == 400
    assert bad_resp2.json()["error"]["code"] == "INVALID_TASK_STATUS_TRANSITION"
