def test_tenant_isolation_cross_organization_project_access(client, test_setup, auth_headers):
    """
    Alpha member tries to access Beta project directly via GET /api/v1/projects/{beta_project_id}
    """
    alpha_user = test_setup["member_user"]
    beta_project = test_setup["project_beta"]
    beta_org = test_setup["org_beta"]

    # Passing Beta Org ID with Alpha User credentials
    headers = auth_headers(alpha_user, beta_org.id)
    response = client.get(f"/api/v1/projects/{beta_project.id}", headers=headers)
    
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


def test_tenant_isolation_project_id_tampering(client, test_setup, auth_headers):
    """
    Alpha admin tries to fetch Beta project ID within Alpha organization context
    """
    alpha_admin = test_setup["admin_user"]
    alpha_org = test_setup["org_alpha"]
    beta_project = test_setup["project_beta"]

    headers = auth_headers(alpha_admin, alpha_org.id)
    response = client.get(f"/api/v1/projects/{beta_project.id}", headers=headers)

    # Must return 404 because project belongs to Beta org, not Alpha org
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_tenant_isolation_members_list(client, test_setup, auth_headers):
    """
    Alpha member cannot list Beta org members
    """
    alpha_user = test_setup["member_user"]
    beta_org = test_setup["org_beta"]

    headers = auth_headers(alpha_user, beta_org.id)
    response = client.get(f"/api/v1/organizations/{beta_org.id}/members", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


def test_tenant_isolation_tasks_query(client, test_setup, auth_headers):
    """
    Alpha member cannot query tasks of Beta org
    """
    alpha_user = test_setup["member_user"]
    beta_org = test_setup["org_beta"]

    headers = auth_headers(alpha_user, beta_org.id)
    response = client.get("/api/v1/tasks", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


def test_tenant_isolation_dashboard(client, test_setup, auth_headers):
    """
    Alpha admin cannot view Beta dashboard
    """
    alpha_admin = test_setup["admin_user"]
    beta_org = test_setup["org_beta"]

    headers = auth_headers(alpha_admin, beta_org.id)
    response = client.get("/api/v1/dashboard/stats", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"
