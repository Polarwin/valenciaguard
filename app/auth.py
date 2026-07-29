"""Session auth, password hashing (pbkdf2), role guards and CSRF protection."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from .config import settings
from .database import get_session
from .models import User

_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iterations, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def login_user(request: Request, user: User) -> None:
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    request.session["csrf_token"] = secrets.token_hex(16)


def logout_user(request: Request) -> None:
    request.session.clear()


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        request.session["csrf_token"] = token
    return token


async def csrf_protect(request: Request) -> None:
    """Dependency for POST form handlers: validates the csrf_token form field."""
    form = await request.form()
    sent = form.get("csrf_token", "")
    expected = request.session.get("csrf_token", "")
    if not sent or not expected or not hmac.compare_digest(str(sent), str(expected)):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


# ---------------------------------------------------------------------------
# User guards
# ---------------------------------------------------------------------------

def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = session.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


def _redirect(location: str) -> HTTPException:
    return HTTPException(status_code=303,
                         headers={"Location": settings.root_path + location})


def redirect(location: str) -> RedirectResponse:
    """303 redirect that prepends the deployment root_path (if any)."""
    return RedirectResponse(settings.root_path + location, status_code=303)


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise _redirect("/login")
    return user


def require_admin(user: Optional[User] = Depends(get_current_user)) -> User:
    """Staff area guard: admins and superusers (superuser inherits staff UI)."""
    if not user:
        raise _redirect("/login")
    if user.role not in ("admin", "superuser"):
        raise _redirect("/owner-portal" if user.role == "owner" else "/login")
    return user


def require_superuser(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise _redirect("/login")
    if user.role != "superuser":
        raise _redirect("/owner-portal" if user.role == "owner" else "/dashboard")
    return user


def require_owner(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> tuple[User, "object"]:
    """Require an owner user and return (user, owner) with strict scoping."""
    from .models import Owner

    if not user:
        raise _redirect("/login")
    if user.role != "owner":
        raise _redirect("/dashboard")
    owner = session.exec(select(Owner).where(Owner.user_id == user.id)).first()
    if not owner:
        raise HTTPException(status_code=403, detail="No owner profile linked")
    return user, owner
