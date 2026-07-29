"""ValenciaGuard application entrypoint: dashboard, calendar, settings."""
import logging
from datetime import date
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from .auth import ensure_csrf_token, csrf_protect, redirect, require_admin, require_user
from .config import settings
from .database import get_session, init_db
from .models import (
    Alert, AuditLog, Contract, Issue, Property, RentRecord, Settings, Tenant, User,
)
from .routers import ai, auth, contracts, documents, issues, owners, portal, properties, rent, tenants, users
from .i18n import SUPPORTED_LANGUAGES, language_from_cookies, set_language, t
from .services import alerts as alert_service
from .services import ai_service
from .templates_config import templates

logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ValenciaGuard", lifespan=lifespan,
              root_path=settings.root_path)


@app.middleware("http")
async def csrf_token_middleware(request: Request, call_next):
    # make sure every session has a CSRF token available for forms
    if request.method == "GET":
        ensure_csrf_token(request)
    return await call_next(request)


class LanguageMiddleware:
    """Pure-ASGI middleware: sets the i18n contextvar from the vg_lang cookie.

    Pure ASGI (not BaseHTTPMiddleware) so the contextvar reliably propagates
    into sync endpoints and template rendering.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            set_language(language_from_cookies(Request(scope).cookies))
        await self.app(scope, receive, send)


# must wrap the middleware above so request.session is available inside it.
# Unique cookie name + prefix-scoped path so the cookie does not collide with
# sibling apps sharing the same hostname behind the reverse proxy.
app.add_middleware(LanguageMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=False,
    session_cookie="vg_session",
    path=settings.root_path + "/" if settings.root_path else "/",
)


# Static files: a plain route instead of a StaticFiles Mount, because Mount +
# root_path breaks path resolution when the reverse proxy strips the prefix
# (requests arrive root-relative). A plain route matches both prefixed and
# unprefixed request paths.
STATIC_DIR = (BASE_DIR / "static").resolve()


@app.get("/static/{file_path:path}", include_in_schema=False)
def static_files(file_path: str):
    full = (STATIC_DIR / file_path).resolve()
    if not str(full).startswith(str(STATIC_DIR)) or not full.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(full)


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # served from root so the worker gets scope "/", which a /static/ mount
    # could not provide
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )

for r in (auth.router, properties.router, tenants.router, contracts.router,
          rent.router, issues.router, documents.router, owners.router,
          ai.router, portal.router, users.router):
    app.include_router(r)


@app.get("/", include_in_schema=False)
def root(user: User | None = Depends(require_user)):
    if user.role == "owner":
        return redirect("/owner-portal")
    return redirect("/dashboard")


@app.get("/set-language/{lang}", include_in_schema=False)
def set_language_route(lang: str, next: str = "/"):
    """Set the vg_lang cookie and bounce back. `next` must be a local path."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = "es"
    if not next.startswith("/") or next.startswith("//"):
        next = "/"
    # templates pass the raw (possibly prefix-carrying) browser path; strip
    # the deployment prefix so redirect() can re-add it exactly once
    if settings.root_path and next.startswith(settings.root_path + "/"):
        next = next[len(settings.root_path):]
    resp = redirect(next)
    resp.set_cookie(
        "vg_lang", lang,
        max_age=365 * 24 * 3600,
        path=settings.root_path + "/" if settings.root_path else "/",
        httponly=True,
    )
    return resp


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    # refresh alerts on dashboard load (also runnable via CLI/cron)
    alert_service.check_alerts(session)

    today = date.today()
    first_of_month = today.replace(day=1)
    first_of_year = today.replace(month=1, day=1)

    properties = session.exec(select(Property)).all()
    rent_records = session.exec(select(RentRecord)).all()
    overdue = [r for r in rent_records if r.status == "late"]
    collected_month = sum(
        r.amount_paid for r in rent_records
        if r.paid_date and r.paid_date >= first_of_month
    )
    collected_ytd = sum(
        r.amount_paid for r in rent_records
        if r.paid_date and r.paid_date >= first_of_year
    )
    upcoming_alerts = session.exec(
        select(Alert).where(Alert.status != "dismissed", Alert.due_date >= today)
        .order_by(Alert.due_date)
    ).all()
    open_issues = session.exec(
        select(Issue).where(Issue.status.in_(["open", "in_progress"]))
    ).all()
    prop_map = {p.id: p for p in properties}

    return templates.TemplateResponse(request, 
        "dashboard.html",
        {
            "request": request, "user": user,
            "property_count": len(properties),
            "occupied": sum(1 for p in properties if p.status == "occupied"),
            "overdue": overdue, "collected_month": collected_month,
            "collected_ytd": collected_ytd,
            "alerts": upcoming_alerts[:20], "open_issues": open_issues,
            "prop_map": prop_map, "today": today,
        },
    )


@app.get("/calendar", response_class=HTMLResponse)
def calendar(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    events: list[dict] = []
    prop_map = {p.id: p for p in session.exec(select(Property)).all()}

    for c in session.exec(select(Contract)).all():
        addr = prop_map.get(c.property_id).address if prop_map.get(c.property_id) else "?"
        for label, d in (
            (t("cal.contract_end"), c.mandatory_end_date),
            (t("cal.notice_deadline"), c.notice_deadline_date),
            (t("cal.rent_update"), c.next_rent_update_date),
            (t("cal.tacit_end"), c.tacit_renewal_end_date),
        ):
            if d:
                events.append({"date": d, "label": label, "detail": addr,
                               "url": f"/properties/{c.property_id}"})
    for ten in session.exec(select(Tenant)).all():
        if ten.insurance_expiry:
            addr = prop_map.get(ten.property_id).address if prop_map.get(ten.property_id) else "?"
            events.append({"date": ten.insurance_expiry, "label": t("cal.insurance_expiry"),
                           "detail": f"{addr} — {ten.insurance_policy_number}",
                           "url": f"/properties/{ten.property_id}"})
    for r in session.exec(select(RentRecord).where(RentRecord.status != "paid")).all():
        addr = prop_map.get(r.property_id).address if prop_map.get(r.property_id) else "?"
        due = date(r.month.year, r.month.month, alert_service.RENT_DUE_DAY)
        events.append({"date": due, "label": t("cal.rent_due"),
                       "detail": f"{addr} — {r.amount_due:.2f} €",
                       "url": f"/properties/{r.property_id}"})
    events.sort(key=lambda e: e["date"])
    return templates.TemplateResponse(request, 
        "calendar.html",
        {"request": request, "user": user, "events": events, "today": date.today()},
    )


@app.get("/ai-assistant", response_class=HTMLResponse)
def ai_assistant_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(request, 
        "ai_chat.html",
        {"request": request, "user": user, "ai_available": ai_service.ai_available()},
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    rows = {s.key: s.value for s in session.exec(select(Settings)).all()}
    audit = session.exec(
        select(AuditLog).order_by(AuditLog.timestamp.desc())
    ).all()[:50]
    return templates.TemplateResponse(request, 
        "settings.html",
        {
            "request": request, "user": user,
            "company_name": rows.get("company_name", "ValenciaGuard Gestión"),
            "notify_email": rows.get("notify_email", ""),
            "cost_threshold": rows.get("cost_threshold", str(settings.cost_threshold)),
            "irav_rate": rows.get("irav_rate", str(settings.irav_rate)),
            "audit": audit,
        },
    )


@app.post("/settings")
def save_settings(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    company_name: str = Form(""),
    notify_email: str = Form(""),
    cost_threshold: float = Form(200.0),
    irav_rate: float = Form(0.0214),
):
    for key, value in (
        ("company_name", company_name),
        ("notify_email", notify_email),
        ("cost_threshold", str(cost_threshold)),
        ("irav_rate", str(irav_rate)),
    ):
        row = session.get(Settings, key)
        if row:
            row.value = value
        else:
            row = Settings(key=key, value=value)
        session.add(row)
    session.commit()
    return redirect("/settings")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
