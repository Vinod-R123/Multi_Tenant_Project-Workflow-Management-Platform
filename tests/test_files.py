import io


def test_upload_valid_files(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    headers = auth_headers(pm, org.id)

    # 1. Valid PDF file (with %PDF- magic bytes)
    pdf_content = b"%PDF-1.5 \x00\x01\x02 test pdf payload content"
    files = {"file": ("architecture_spec.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"project_id": str(project.id)}

    pdf_resp = client.post("/api/v1/files/upload", files=files, data=data, headers=headers)
    assert pdf_resp.status_code == 201
    file_data = pdf_resp.json()["data"]
    assert file_data["file_name"] == "architecture_spec.pdf"
    assert file_data["mime_type"] == "application/pdf"
    file_id = file_data["id"]

    # 2. Download uploaded file
    dl_resp = client.get(f"/api/v1/files/{file_id}/download", headers=headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == pdf_content


def test_upload_fake_extension_magic_bytes_mismatch(client, test_setup, auth_headers):
    """
    Client uploads a plain text string disguised as a .pdf or .png file.
    Backend must verify magic bytes and reject with INVALID_FILE_CONTENT.
    """
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    headers = auth_headers(pm, org.id)

    fake_pdf = b"This is just plain text, NOT a real PDF binary header!"
    files = {"file": ("malicious_payload.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    data = {"project_id": str(project.id)}

    response = client.post("/api/v1/files/upload", files=files, data=data, headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_CONTENT"


def test_upload_disallowed_extension(client, test_setup, auth_headers):
    pm = test_setup["pm_user"]
    org = test_setup["org_alpha"]
    project = test_setup["project_alpha"]
    headers = auth_headers(pm, org.id)

    exe_content = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {"file": ("script.exe", io.BytesIO(exe_content), "application/x-msdownload")}
    data = {"project_id": str(project.id)}

    response = client.post("/api/v1/files/upload", files=files, data=data, headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_EXTENSION"


def test_cross_tenant_file_download_denied(client, test_setup, auth_headers):
    pm_alpha = test_setup["pm_user"]
    org_alpha = test_setup["org_alpha"]
    org_beta = test_setup["org_beta"]
    project = test_setup["project_alpha"]

    # Alpha uploads file
    pdf_content = b"%PDF-1.4 valid test pdf"
    files = {"file": ("confidential.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"project_id": str(project.id)}
    up_resp = client.post("/api/v1/files/upload", files=files, data=data, headers=auth_headers(pm_alpha, org_alpha.id))
    file_id = up_resp.json()["data"]["id"]

    # Beta admin tries to download Alpha's file within Beta context -> 404/403
    beta_admin = test_setup["beta_admin"]
    bad_dl = client.get(f"/api/v1/files/{file_id}/download", headers=auth_headers(beta_admin, org_beta.id))
    assert bad_dl.status_code == 404
    assert bad_dl.json()["error"]["code"] == "FILE_NOT_FOUND"
