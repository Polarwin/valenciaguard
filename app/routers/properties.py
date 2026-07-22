"""Admin property CRUD + detail page."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from ..audit import log_action
from ..auth import csrf_protect, require_admin
from ..database import get_session
from ..models import Contract, Document, Issue, Owner, Property, RentRecord, Tenant, User
from ..templates_config import templates

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_class=HTMLResponse)
def list_properties(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    properties = session.exec(select(Property).order_by(Property.id)).all()
    owners = {o.id: o for o in session.exec(select(Owner)).all()}
    return templates.TemplateResponse(request, 
        "properties/list.html",
        {"request": request, "user": user, "properties": properties, "owners": owners},
    )


@router.get("/new", response_class=HTMLResponse)
def new_property_form(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    owners = session.exec(select(Owner).order_by(Owner.name)).all()
    return templates.TemplateResponse(request, 
        "properties/form.html",
        {"request": request, "user": user, "prop": None, "owners": owners},
    )


def _parse_date(value: str) -> Optional[date]:
    return date.fromisoformat(value) if value else None


def _parse_float(value: str) -> Optional[float]:
    return float(value) if value else None


@router.post("")
def create_property(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    address: str = Form(...),
    city: str = Form("Valencia"),
    postal_code: str = Form(""),
    owner_id: int = Form(...),
    purchase_date: str = Form(""),
    purchase_price: str = Form(""),
    current_value_estimate: str = Form(""),
    status: str = Form("vacant"),
):
    prop = Property(
        address=address,
        city=city or "Valencia",
        postal_code=postal_code,
        owner_id=owner_id,
        purchase_date=_parse_date(purchase_date),
        purchase_price=_parse_float(purchase_price),
        current_value_estimate=_parse_float(current_value_estimate),
        status=status,
    )
    session.add(prop)
    session.commit()
    session.refresh(prop)
    log_action(session, user, "create", "property", prop.id, prop.address)
    return RedirectResponse(f"/properties/{prop.id}", status_code=303)


@router.get("/{property_id}", response_class=HTMLResponse)
def property_detail(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    owner = session.get(Owner, prop.owner_id)
    tenant = session.exec(select(Tenant).where(Tenant.property_id == property_id)).first()
    contracts = session.exec(
        select(Contract).where(Contract.property_id == property_id).order_by(Contract.start_date.desc())
    ).all()
    rent_records = session.exec(
        select(RentRecord).where(RentRecord.property_id == property_id).order_by(RentRecord.month.desc())
    ).all()
    issues = session.exec(
        select(Issue).where(Issue.property_id == property_id).order_by(Issue.created_at.desc())
    ).all()
    documents = session.exec(
        select(Document).where(Document.property_id == property_id).order_by(Document.upload_date.desc())
    ).all()
    return templates.TemplateResponse(request, 
        "properties/detail.html",
        {
            "request": request, "user": user, "prop": prop, "owner": owner,
            "tenant": tenant, "contracts": contracts, "rent_records": rent_records,
            "issues": issues, "documents": documents, "today": date.today(),
        },
    )


@router.get("/{property_id}/edit", response_class=HTMLResponse)
def edit_property_form(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    owners = session.exec(select(Owner).order_by(Owner.name)).all()
    return templates.TemplateResponse(request, 
        "properties/form.html",
        {"request": request, "user": user, "prop": prop, "owners": owners},
    )


@router.post("/{property_id}/edit")
def update_property(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    address: str = Form(...),
    city: str = Form("Valencia"),
    postal_code: str = Form(""),
    owner_id: int = Form(...),
    purchase_date: str = Form(""),
    purchase_price: str = Form(""),
    current_value_estimate: str = Form(""),
    status: str = Form("vacant"),
):
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    prop.address = address
    prop.city = city or "Valencia"
    prop.postal_code = postal_code
    prop.owner_id = owner_id
    prop.purchase_date = _parse_date(purchase_date)
    prop.purchase_price = _parse_float(purchase_price)
    prop.current_value_estimate = _parse_float(current_value_estimate)
    prop.status = status
    session.add(prop)
    session.commit()
    log_action(session, user, "update", "property", prop.id, prop.address)
    return RedirectResponse(f"/properties/{prop.id}", status_code=303)


@router.post("/{property_id}/delete")
def delete_property(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    session.delete(prop)
    session.commit()
    log_action(session, user, "delete", "property", property_id, prop.address)
    return RedirectResponse("/properties", status_code=303)
