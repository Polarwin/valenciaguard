"""User management: add/reset/delete, safeguards, guards, CSRF."""
from sqlmodel import Session, select

from app.auth import verify_password
from app.database import engine
from app.models import Owner, User
from tests.conftest import _login, get_csrf


def _add_user(client, username, role="owner", password="password123", owner_id="", csrf=None):
    return client.post("/users", data={
        "username": username, "role": role, "password": password,
        "owner_id": owner_id, "csrf_token": csrf or get_csrf(client, "/users"),
    }, follow_redirects=False)


def test_list_users(admin_client):
    resp = admin_client.get("/users")
    assert resp.status_code == 200
    assert "admin" in resp.text
    assert "Usuarios" in resp.text


def test_add_user(admin_client):
    resp = _add_user(admin_client, "user_add_1")
    assert resp.status_code == 303
    assert "user_add_1" in admin_client.get("/users").text


def test_duplicate_username_rejected(admin_client):
    resp = _add_user(admin_client, "admin")  # already exists
    assert resp.status_code == 400
    assert "ya existe" in resp.text


def test_short_password_rejected(admin_client):
    resp = _add_user(admin_client, "user_short_pw", password="short")
    assert resp.status_code == 400
    assert "8" in resp.text


def test_delete_self_rejected(admin_client):
    with Session(engine) as s:
        admin_id = s.exec(select(User).where(User.username == "admin")).first().id
    resp = admin_client.post(f"/users/{admin_id}/delete",
                             data={"csrf_token": get_csrf(admin_client, "/users")},
                             follow_redirects=False)
    assert resp.status_code == 400


def test_admin_promoted_to_superuser_by_migration(admin_client):
    # conftest runs init_db() after seeding: the oldest admin is promoted
    with Session(engine) as s:
        assert s.exec(select(User).where(User.username == "admin")).first().role == "superuser"
        assert s.exec(select(User).where(User.username == "staff1")).first().role == "admin"


def test_employee_cannot_create_employee(staff_client):
    resp = _add_user(staff_client, "emp_forbidden", role="admin")
    assert resp.status_code == 400
    with Session(engine) as s:
        assert not s.exec(select(User).where(User.username == "emp_forbidden")).first()


def test_employee_cannot_reset_or_delete_staff(staff_client):
    with Session(engine) as s:
        admin_id = s.exec(select(User).where(User.username == "admin")).first().id
    resp = staff_client.post(f"/users/{admin_id}/reset", data={
        "password": "brandnewpass99", "csrf_token": get_csrf(staff_client, "/users"),
    }, follow_redirects=False)
    assert resp.status_code == 403
    resp = staff_client.post(f"/users/{admin_id}/delete",
                             data={"csrf_token": get_csrf(staff_client, "/users")},
                             follow_redirects=False)
    assert resp.status_code == 403


def test_employee_manages_owner_accounts(staff_client):
    assert _add_user(staff_client, "owner_by_staff", role="owner").status_code == 303
    with Session(engine) as s:
        uid = s.exec(select(User).where(User.username == "owner_by_staff")).first().id
    resp = staff_client.post(f"/users/{uid}/reset", data={
        "password": "brandnewpass99", "csrf_token": get_csrf(staff_client, "/users"),
    }, follow_redirects=False)
    assert resp.status_code == 200
    resp = staff_client.post(f"/users/{uid}/delete",
                             data={"csrf_token": get_csrf(staff_client, "/users")},
                             follow_redirects=False)
    assert resp.status_code == 303


def test_superuser_manages_employees(admin_client):
    assert _add_user(admin_client, "emp_by_super", role="admin").status_code == 303
    with Session(engine) as s:
        uid = s.exec(select(User).where(User.username == "emp_by_super")).first().id
    resp = admin_client.post(f"/users/{uid}/delete",
                             data={"csrf_token": get_csrf(admin_client, "/users")},
                             follow_redirects=False)
    assert resp.status_code == 303


def test_reset_password(admin_client):
    _add_user(admin_client, "user_reset_1")
    with Session(engine) as s:
        uid = s.exec(select(User).where(User.username == "user_reset_1")).first().id
    resp = admin_client.post(f"/users/{uid}/reset", data={
        "password": "brandnewpass99", "csrf_token": get_csrf(admin_client, "/users"),
    })
    assert resp.status_code == 200
    assert "brandnewpass99" in resp.text  # shown once to the admin
    with Session(engine) as s:
        u = s.get(User, uid)
        assert verify_password("brandnewpass99", u.password_hash)
        assert not verify_password("password123", u.password_hash)


def test_owner_unlinked_on_delete(admin_client):
    with Session(engine) as s:
        owner = Owner(name="测试三", email="san@example.com")
        s.add(owner)
        s.commit()
        s.refresh(owner)
        oid = owner.id
    assert _add_user(admin_client, "user_owner_link", role="owner",
                     owner_id=str(oid)).status_code == 303
    with Session(engine) as s:
        assert s.get(Owner, oid).user_id is not None
        uid = s.exec(select(User).where(User.username == "user_owner_link")).first().id
    resp = admin_client.post(f"/users/{uid}/delete",
                             data={"csrf_token": get_csrf(admin_client, "/users")},
                             follow_redirects=False)
    assert resp.status_code == 303
    with Session(engine) as s:
        assert s.get(Owner, oid).user_id is None


def test_non_admin_blocked(owner_client):
    resp = owner_client.get("/users", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/owner-portal"
    resp = owner_client.post("/users", data={
        "username": "hack", "password": "password123",
    }, follow_redirects=False)
    assert resp.status_code in (303, 403)


def test_csrf_enforced(admin_client):
    resp = admin_client.post("/users", data={
        "username": "user_nocsrf", "role": "owner", "password": "password123",
    }, follow_redirects=False)
    assert resp.status_code == 403
