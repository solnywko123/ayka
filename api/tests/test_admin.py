from conftest import make_valid_lead_payload


def _login(client, password: str):
    return client.post("/api/v1/admin/login", json={"username": "admin", "password": password})


def test_admin_leads_without_token_401(client):
    response = client.get("/api/v1/admin/leads")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "http_error"


def test_admin_login_wrong_password_401(client):
    response = _login(client, "wrong-password")
    assert response.status_code == 401


def test_admin_login_success_sets_cookie(client, admin_password):
    response = _login(client, admin_password)
    assert response.status_code == 200
    assert "ayka_admin_token" in response.cookies


def test_admin_can_list_leads_after_login(client, admin_password):
    client.post("/api/v1/leads", json=make_valid_lead_payload())
    _login(client, admin_password)

    response = client.get("/api/v1/admin/leads")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "new"


def test_admin_can_change_lead_status(client, admin_password):
    create = client.post("/api/v1/leads", json=make_valid_lead_payload())
    lead_id = create.json()["id"]
    _login(client, admin_password)

    response = client.patch(f"/api/v1/admin/leads/{lead_id}", json={"status": "contacted", "admin_note": "Called"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "contacted"
    assert body["admin_note"] == "Called"

    detail = client.get(f"/api/v1/admin/leads/{lead_id}")
    assert detail.json()["events"][-1]["to_status"] == "contacted"
    assert detail.json()["events"][-1]["from_status"] == "new"


def test_admin_export_csv(client, admin_password):
    client.post("/api/v1/leads", json=make_valid_lead_payload())
    _login(client, admin_password)

    response = client.get("/api/v1/admin/leads/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    text = response.content.decode("utf-8-sig")
    lines = text.strip().splitlines()
    assert lines[0].startswith("id,created_at,status")
    assert len(lines) == 2


def test_admin_stats(client, admin_password):
    client.post("/api/v1/leads", json=make_valid_lead_payload())
    _login(client, admin_password)

    response = client.get("/api/v1/admin/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["leads_today"] == 1
    assert body["by_status"]["new"] == 1


def test_admin_html_dashboard_redirects_when_unauthenticated(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert "/admin/login" in response.headers["location"]


def test_admin_html_login_flow(client, admin_password):
    response = client.post(
        "/admin/login", data={"username": "admin", "password": admin_password, "next": "/admin"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/admin"
    assert "ayka_admin_token" in response.cookies
