def test_dashboard_metrics_for_roles(client, test_setup, auth_headers):
    admin = test_setup["admin_user"]
    pm = test_setup["pm_user"]
    member = test_setup["member_user"]
    org = test_setup["org_alpha"]

    # 1. Org Admin Dashboard
    admin_resp = client.get("/api/v1/dashboard/stats", headers=auth_headers(admin, org.id))
    assert admin_resp.status_code == 200
    admin_data = admin_resp.json()["data"]
    assert admin_data["role"] == "ORGANIZATION_ADMIN"
    assert admin_data["admin_metrics"] is not None
    assert admin_data["admin_metrics"]["total_projects"] >= 1
    assert admin_data["admin_metrics"]["total_users"] >= 4

    # 2. Project Manager Dashboard
    pm_resp = client.get("/api/v1/dashboard/stats", headers=auth_headers(pm, org.id))
    assert pm_resp.status_code == 200
    pm_data = pm_resp.json()["data"]
    assert pm_data["role"] == "PROJECT_MANAGER"
    assert pm_data["pm_metrics"] is not None
    assert pm_data["pm_metrics"]["my_projects"] >= 1

    # 3. Team Member Dashboard
    member_resp = client.get("/api/v1/dashboard/stats", headers=auth_headers(member, org.id))
    assert member_resp.status_code == 200
    m_data = member_resp.json()["data"]
    assert m_data["role"] == "TEAM_MEMBER"
    assert m_data["member_metrics"] is not None
    assert "my_tasks" in m_data["member_metrics"]
