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


def test_delete_last_admin_rejected(admin_client, client):
    # create a second admin, delete the original with it (allowed), then the
    # remaining admin cannot be removed (it is the last one — and oneself)
    assert _add_user(admin_client, "admin2", role="admin").status_code == 303
    with Session(engine) as s:
        admin1 = s.exec(select(User).where(User.username == "admin")).first()
        admin2 = s.exec(select(User).where(User.username == "admin2")).first()
        admin1_id, admin2_id = admin1.id, admin2.id

    assert _login(client, "admin2", "password123").status_code == 303
    csrf = get_csrf(client, "/users")
    # deleting the other admin while two exist is allowed
    resp = client.post(f"/users/{admin1_id}/delete", data={"csrf_token": csrf},
                       follow_redirects=False)
    assert resp.status_code == 303
    # now admin2 is the last admin: deleting it must fail (self + last admin)
    csrf = get_csrf(client, "/users")
    resp = client.post(f"/users/{admin2_id}/delete", data={"csrf_token": csrf},
                       follow_redirects=False)
    assert resp.status_code == 400
    # restore the original admin user for other tests
    with Session(engine) as s:
        from app.auth import hash_password
        s.add(User(id=admin1_id, username="admin",
                   password_hash=hash_password("admin123"), role="admin"))
        s.commit()


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
