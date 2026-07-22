"""Auth, role guards, and strict owner scoping in the portal."""
from tests.conftest import _login


def test_root_redirects_to_login_when_anonymous(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    resp2 = client.get("/dashboard", follow_redirects=False)
    assert resp2.status_code == 303
    assert resp2.headers["location"] == "/login"


def test_login_page_200(client):
    assert client.get("/login").status_code == 200


def test_wrong_password_rejected(client):
    resp = _login(client, "admin", "wrong")
    assert resp.status_code == 401


def test_admin_dashboard_200(admin_client):
    resp = admin_client.get("/dashboard")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text


def test_owner_cannot_access_admin_pages(owner_client):
    resp = owner_client.get("/properties", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/owner-portal"
    resp = owner_client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303


def test_owner_portal_lists_only_own_properties(owner_client):
    resp = owner_client.get("/owner-portal")
    assert resp.status_code == 200
    assert "Calle Colón" in resp.text
    assert "Ruzafa" not in resp.text  # belongs to owner2


def test_owner_cannot_view_others_property_detail(owner_client):
    # property 2 belongs to owner2
    resp = owner_client.get("/owner-portal/properties/2")
    assert resp.status_code == 404


def test_owner_can_view_own_property_detail(owner_client):
    resp = owner_client.get("/owner-portal/properties/1")
    assert resp.status_code == 200
    assert "Calle Colón" in resp.text


def test_owner_cannot_download_others_document(owner_client):
    # even a guessed document id from another property must 404
    resp = owner_client.get("/owner-portal/documents/999/download")
    assert resp.status_code == 404


def test_portal_is_read_only(owner_client):
    # no POST routes exist in the portal; attempting one hits a 404/405, never 200
    resp = owner_client.post("/owner-portal", follow_redirects=False)
    assert resp.status_code in (404, 405)
