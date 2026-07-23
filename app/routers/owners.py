"""Owner management: owners + linked portal user accounts."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..audit import log_action
from ..auth import csrf_protect, hash_password, redirect, require_admin
from ..database import get_session
from ..models import Owner, User
from ..templates_config import templates

router = APIRouter(prefix="/owners", tags=["owners"])


@router.get("", response_class=HTMLResponse)
def list_owners(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    owners = session.exec(select(Owner).order_by(Owner.name)).all()
    users = {u.id: u for u in session.exec(select(User)).all()}
    return templates.TemplateResponse(request, 
        "owners/list.html",
        {"request": request, "user": user, "owners": owners, "users": users},
    )


@router.get("/new", response_class=HTMLResponse)
def new_owner_form(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(request, 
        "owners/form.html", {"request": request, "user": user, "owner": None}
    )


@router.post("")
def create_owner(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    wechat: str = Form(""),
    notes: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
):
    owner = Owner(name=name, email=email, phone=phone, wechat=wechat, notes=notes)
    if username and password:
        if session.exec(select(User).where(User.username == username)).first():
            raise HTTPException(400, "Username already exists")
        portal_user = User(
            username=username, password_hash=hash_password(password), role="owner"
        )
        session.add(portal_user)
        session.commit()
        session.refresh(portal_user)
        owner.user_id = portal_user.id
    session.add(owner)
    session.commit()
    session.refresh(owner)
    log_action(session, user, "create", "owner", owner.id, owner.name)
    return redirect("/owners")


@router.post("/{owner_id}/edit")
def update_owner(
    owner_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    wechat: str = Form(""),
    notes: str = Form(""),
):
    owner = session.get(Owner, owner_id)
    if not owner:
        raise HTTPException(404, "Owner not found")
    owner.name = name
    owner.email = email
    owner.phone = phone
    owner.wechat = wechat
    owner.notes = notes
    session.add(owner)
    session.commit()
    log_action(session, user, "update", "owner", owner.id, owner.name)
    return redirect("/owners")
