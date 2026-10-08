def test_task_dependency_workflow_gating(client, test_setup, auth_headers):
    """
    Task B depends on Task A.
    Task B cannot move to IN_PROGRESS until Task A is DONE.
    """
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    headers = auth_headers(pm, org.id)

    # 1. Create Task A and Task B
    resp_a = client.post("/api/v1/tasks", json={"project_id": project.id, "title": "Task A (Database Migration)"}, headers=headers)
    task_a_id = resp_a.json()["data"]["id"]

    resp_b = client.post("/api/v1/tasks", json={"project_id": project.id, "title": "Task B (Backend API Deployment)"}, headers=headers)
    task_b_id = resp_b.json()["data"]["id"]

    # 2. Add dependency: Task B depends on Task A
    dep_resp = client.post(
        f"/api/v1/tasks/{task_b_id}/dependencies",
        json={"depends_on_task_id": task_a_id},
        headers=headers,
    )
    assert dep_resp.status_code == 201

    # 3. Attempt to move Task B to IN_PROGRESS while Task A is still in TODO
    gated_resp = client.patch(
        f"/api/v1/tasks/{task_b_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert gated_resp.status_code == 400
    assert gated_resp.json()["error"]["code"] == "UNRESOLVED_DEPENDENCY"

    # 4. Advance Task A: TODO -> IN_PROGRESS -> REVIEW -> DONE
    client.patch(f"/api/v1/tasks/{task_a_id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    client.patch(f"/api/v1/tasks/{task_a_id}/status", json={"status": "REVIEW"}, headers=headers)
    done_a = client.patch(f"/api/v1/tasks/{task_a_id}/status", json={"status": "DONE"}, headers=headers)
    assert done_a.status_code == 200

    # 5. Now Task B can successfully move to IN_PROGRESS
    success_b = client.patch(
        f"/api/v1/tasks/{task_b_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert success_b.status_code == 200
    assert success_b.json()["data"]["status"] == "IN_PROGRESS"


def test_circular_dependency_detection_direct_and_multihop(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    headers = auth_headers(pm, org.id)

    # 1. Create Tasks T1, T2, T3
    t1_id = client.post("/api/v1/tasks", json={"project_id": project.id, "title": "T1"}, headers=headers).json()["data"]["id"]
    t2_id = client.post("/api/v1/tasks", json={"project_id": project.id, "title": "T2"}, headers=headers).json()["data"]["id"]
    t3_id = client.post("/api/v1/tasks", json={"project_id": project.id, "title": "T3"}, headers=headers).json()["data"]["id"]

    # 2. Self-dependency rejection: T1 depends on T1
    self_dep = client.post(f"/api/v1/tasks/{t1_id}/dependencies", json={"depends_on_task_id": t1_id}, headers=headers)
    assert self_dep.status_code == 400
    assert self_dep.json()["error"]["code"] == "SELF_DEPENDENCY_FORBIDDEN"

    # 3. T2 depends on T1
    client.post(f"/api/v1/tasks/{t2_id}/dependencies", json={"depends_on_task_id": t1_id}, headers=headers)

    # Direct Cycle: Attempt T1 depends on T2
    direct_cycle = client.post(f"/api/v1/tasks/{t1_id}/dependencies", json={"depends_on_task_id": t2_id}, headers=headers)
    assert direct_cycle.status_code == 400
    assert direct_cycle.json()["error"]["code"] == "CIRCULAR_DEPENDENCY_DETECTED"

    # 4. Multi-hop: T3 depends on T2 (Chain: T3 -> T2 -> T1)
    client.post(f"/api/v1/tasks/{t3_id}/dependencies", json={"depends_on_task_id": t2_id}, headers=headers)

    # Multi-hop Cycle: Attempt T1 depends on T3
    multihop_cycle = client.post(f"/api/v1/tasks/{t1_id}/dependencies", json={"depends_on_task_id": t3_id}, headers=headers)
    assert multihop_cycle.status_code == 400
    assert multihop_cycle.json()["error"]["code"] == "CIRCULAR_DEPENDENCY_DETECTED"
