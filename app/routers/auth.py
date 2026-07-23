"""Login / logout routes."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..auth import csrf_protect, login_user, logout_user, redirect, verify_password
from ..database import get_session
from ..i18n import t
from ..models import User
from ..templates_config import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": ""})


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        return templates.TemplateResponse(request, 
            "login.html",
            {"request": request, "error": t("auth.login_error")},
            status_code=401,
        )
    login_user(request, user)
    target = "/dashboard" if user.role == "admin" else "/owner-portal"
    return redirect(target)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return redirect("/login")
