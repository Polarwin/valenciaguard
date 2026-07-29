"""Admin user management: list, add, reset password, delete (with safeguards)."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..audit import log_action
from ..auth import csrf_protect, hash_password, redirect, require_admin
from ..database import get_session
from ..i18n import t as _t
from ..models import Owner, User
from ..templates_config import templates

router = APIRouter(prefix="/users", tags=["users"])

MIN_PASSWORD_LEN = 8


@router.get("", response_class=HTMLResponse)
def list_users(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    users = session.exec(select(User).order_by(User.id)).all()
    owners = session.exec(select(Owner)).all()
    owner_by_user = {o.user_id: o for o in owners if o.user_id}
    unlinked_owners = [o for o in owners if not o.user_id]
    return templates.TemplateResponse(request,
        "users/list.html",
        {
            "request": request, "user": user, "users": users,
            "owner_by_user": owner_by_user, "unlinked_owners": unlinked_owners,
        },
    )


@router.post("")
def create_user(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    username: str = Form(...),
    role: str = Form("owner"),
    password: str = Form(...),
    owner_id: str = Form(""),
):
    username = username.strip()
    owners = session.exec(select(Owner)).all()
    owner_by_user = {o.user_id: o for o in owners if o.user_id}
    unlinked_owners = [o for o in owners if not o.user_id]

    def fail(message: str) -> HTMLResponse:
        users = session.exec(select(User).order_by(User.id)).all()
        return templates.TemplateResponse(request,
            "users/list.html",
            {
                "request": request, "user": user, "users": users,
                "owner_by_user": owner_by_user, "unlinked_owners": unlinked_owners,
                "error": message,
            },
            status_code=400,
        )

    if not username:
        return fail(_t("users.err_username_empty"))
    if session.exec(select(User).where(User.username == username)).first():
        return fail(_t("users.err_username_taken", username=username))
    if len(password) < MIN_PASSWORD_LEN:
        return fail(_t("users.err_password_short"))
    if role not in ("admin", "owner"):
        return fail(_t("users.err_role_invalid"))
    if role == "admin" and user.role != "superuser":
        # only the superuser (agency boss) creates employee accounts
        return fail(_t("users.err_forbidden"))

    link_owner = None
    if role == "owner" and owner_id:
        link_owner = session.get(Owner, int(owner_id))
        if not link_owner:
            return fail(_t("users.err_owner_not_found"))
        if link_owner.user_id:
            return fail(_t("users.err_owner_linked"))

    new_user = User(username=username, password_hash=hash_password(password), role=role)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    if link_owner is not None:
        link_owner.user_id = new_user.id
        session.add(link_owner)
        session.commit()
    log_action(session, user, "create", "user", new_user.id,
               f"{username} ({role})")
    return redirect("/users")


@router.post("/{user_id}/reset", response_class=HTMLResponse)
def reset_password(
    user_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    password: str = Form(...),
):
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(404, _t("users.err_not_found"))
    if target.role in ("admin", "superuser") and user.role != "superuser":
        raise HTTPException(403, _t("users.err_forbidden"))
    if len(password) < MIN_PASSWORD_LEN:
        raise HTTPException(400, _t("users.err_password_short"))
    target.password_hash = hash_password(password)
    session.add(target)
    session.commit()
    log_action(session, user, "update", "user", target.id, "password reset")
    # show the new password once so the admin can pass it to the user
    return templates.TemplateResponse(request,
        "users/password.html",
        {"request": request, "user": user, "target": target, "password": password},
    )


@router.post("/{user_id}/delete")
def delete_user(
    user_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(404, _t("users.err_not_found"))
    if target.id == user.id:
        raise HTTPException(400, _t("users.err_delete_self"))
    if target.role in ("admin", "superuser") and user.role != "superuser":
        raise HTTPException(403, _t("users.err_forbidden"))
    # invariant: the last superuser can never be removed — only superusers may
    # delete staff accounts, and nobody can delete themselves
    # unlink any owner profile pointing at this user
    owner = session.exec(select(Owner).where(Owner.user_id == target.id)).first()
    if owner:
        owner.user_id = None
        session.add(owner)
    target_id, target_username = target.id, target.username
    session.delete(target)
    session.commit()
    log_action(session, user, "delete", "user", target_id, target_username)
    return redirect("/users")
