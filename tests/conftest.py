"""Test fixtures: temp DB, temp upload dir, logged-in clients."""
import os
import tempfile
from datetime import date
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="valenciaguard-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["SECRET_KEY"] = "test-secret"
os.environ["KIMI_API_KEY"] = ""
os.environ["ROOT_PATH"] = ""  # .env may set a prefix for deployment; tests run at root
# ensure a stray .env cannot override the test database
os.environ["SMTP_HOST"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import hash_password
from app.database import engine, init_db
from app.main import app
from app.models import Owner, Property, Tenant, User


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    with Session(engine) as session:
        admin = User(username="admin", password_hash=hash_password("admin123"), role="admin")
        staff = User(username="staff1", password_hash=hash_password("staff123"), role="admin")
        owner_user = User(username="owner1", password_hash=hash_password("owner123"), role="owner")
        other_user = User(username="owner2", password_hash=hash_password("owner123"), role="owner")
        session.add_all([admin, staff, owner_user, other_user])
        session.commit()
        session.refresh(owner_user)
        session.refresh(other_user)

        owner = Owner(name="王建军", email="wang@example.com", user_id=owner_user.id)
        other = Owner(name="李梅", email="li@example.com", user_id=other_user.id)
        session.add_all([owner, other])
        session.commit()
        session.refresh(owner)
        session.refresh(other)

        session.add(Property(address="Calle Colón 18, 3ºA", owner_id=owner.id, status="occupied"))
        session.add(Property(address="Calle Ruzafa 5, 2ºB", owner_id=other.id, status="occupied"))
        session.commit()
    # second init_db run triggers the superuser migration: the oldest admin
    # ("admin") is promoted, "staff1" stays a plain employee
    init_db()
    yield


@pytest.fixture()
def client():
    return TestClient(app, base_url="http://testserver")


def _login(client: TestClient, username: str, password: str):
    # GET /login first to obtain a session + csrf token
    resp = client.get("/login")
    assert resp.status_code == 200
    token = client.cookies.get("session")
    # extract csrf token from the rendered form
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', resp.text)
    csrf = m.group(1)
    resp = client.post("/login", data={
        "username": username, "password": password, "csrf_token": csrf,
    }, follow_redirects=False)
    return resp


@pytest.fixture()
def admin_client(client):
    """Logged in as the superuser (seeded admin, promoted by the migration)."""
    resp = _login(client, "admin", "admin123")
    assert resp.status_code == 303
    return client


@pytest.fixture()
def staff_client(client):
    """Logged in as a plain employee (admin role, not superuser)."""
    resp = _login(client, "staff1", "staff123")
    assert resp.status_code == 303
    return client


@pytest.fixture()
def owner_client(client):
    resp = _login(client, "owner1", "owner123")
    assert resp.status_code == 303
    return client


@pytest.fixture()
def other_owner_client(client):
    resp = _login(client, "owner2", "owner123")
    assert resp.status_code == 303
    return client


def get_csrf(client: TestClient, url: str = "/properties/new") -> str:
    import re
    resp = client.get(url)
    m = re.search(r'name="csrf_token" value="([^"]+)"', resp.text)
    return m.group(1)
