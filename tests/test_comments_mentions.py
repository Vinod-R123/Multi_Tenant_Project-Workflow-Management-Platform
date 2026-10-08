def test_comment_creation_and_mentions(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    member = test_setup["member_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]

    # 1. Create task
    task_resp = client.post("/api/v1/tasks", json={"project_id": project.id, "title": "Mention Test Task"}, headers=auth_headers(pm, org.id))
    task_id = task_resp.json()["data"]["id"]

    # 2. Add comment mentioning alpha_member
    comment_resp = client.post(
        "/api/v1/comments",
        json={"task_id": task_id, "content": "Hey @alpha_member, please review this implementation!"},
        headers=auth_headers(pm, org.id),
    )
    assert comment_resp.status_code == 201
    comment_data = comment_resp.json()["data"]
    assert "Hey @alpha_member" in comment_data["content"]

    # 3. Check notifications for alpha_member
    notif_resp = client.get("/api/v1/notifications", headers=auth_headers(member, org.id))
    assert notif_resp.status_code == 200
    notifs = notif_resp.json()["data"]["items"]
    assert any(n["event_type"] == "USER_MENTIONED" for n in notifs)


def test_comment_update_permissions(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    member = test_setup["member_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]

    # 1. PM creates a comment
    comment_resp = client.post(
        "/api/v1/comments",
        json={"project_id": project.id, "content": "PM original comment"},
        headers=auth_headers(pm, org.id),
    )
    comment_id = comment_resp.json()["data"]["id"]

    # 2. Member attempts to edit PM's comment -> 403 Forbidden
    bad_edit = client.put(
        f"/api/v1/comments/{comment_id}",
        json={"content": "Malicious edit"},
        headers=auth_headers(member, org.id),
    )
    assert bad_edit.status_code == 403
    assert bad_edit.json()["error"]["code"] == "UNAUTHORIZED_COMMENT_MODIFICATION"

    # 3. PM edits their own comment -> 200 OK
    ok_edit = client.put(
        f"/api/v1/comments/{comment_id}",
        json={"content": "PM updated comment"},
        headers=auth_headers(pm, org.id),
    )
    assert ok_edit.status_code == 200
    assert ok_edit.json()["data"]["content"] == "PM updated comment"
