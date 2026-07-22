"""CSRF protection on POST forms."""
from tests.conftest import get_csrf


def test_post_without_csrf_rejected(admin_client):
    resp = admin_client.post("/properties", data={
        "address": "Calle Falsa 1", "owner_id": "1",
    }, follow_redirects=False)
    assert resp.status_code == 403


def test_post_with_wrong_csrf_rejected(admin_client):
    resp = admin_client.post("/properties", data={
        "address": "Calle Falsa 1", "owner_id": "1", "csrf_token": "bogus",
    }, follow_redirects=False)
    assert resp.status_code == 403


def test_post_with_valid_csrf_accepted(admin_client):
    csrf = get_csrf(admin_client)
    resp = admin_client.post("/properties", data={
        "address": "Calle de la Paz 9", "owner_id": "1", "csrf_token": csrf,
        "city": "Valencia", "postal_code": "46001",
    }, follow_redirects=False)
    assert resp.status_code == 303


def test_login_requires_csrf(client):
    resp = client.post("/login", data={
        "username": "admin", "password": "admin123",
    }, follow_redirects=False)
    assert resp.status_code == 403
