"""Tenant create/update (one tenant per property), managed from property detail."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlmodel import Session, select

from ..audit import log_action
from ..auth import csrf_protect, redirect, require_admin
from ..database import get_session
from ..models import Property, Tenant, User

router = APIRouter(prefix="/properties/{property_id}/tenant", tags=["tenants"])


def _d(value: str) -> Optional[date]:
    return date.fromisoformat(value) if value else None


def _f(value: str) -> Optional[float]:
    return float(value) if value else None


@router.post("")
def save_tenant(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    name: str = Form(...),
    nie_dni: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    emergency_contact: str = Form(""),
    move_in_date: str = Form(""),
    contract_start: str = Form(""),
    contract_end: str = Form(""),
    rent_amount: float = Form(0.0),
    deposit_amount: float = Form(0.0),
    deposit_bank_guarantee: bool = Form(False),
    deposit_bank_guarantee_amount: str = Form(""),
    insurance_policy_number: str = Form(""),
    insurance_expiry: str = Form(""),
):
    if not session.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    tenant = session.exec(select(Tenant).where(Tenant.property_id == property_id)).first()
    action = "update" if tenant else "create"
    if not tenant:
        tenant = Tenant(property_id=property_id, name=name)
    tenant.name = name
    tenant.nie_dni = nie_dni
    tenant.phone = phone
    tenant.email = email
    tenant.emergency_contact = emergency_contact
    tenant.move_in_date = _d(move_in_date)
    tenant.contract_start = _d(contract_start)
    tenant.contract_end = _d(contract_end)
    tenant.rent_amount = rent_amount
    tenant.deposit_amount = deposit_amount
    tenant.deposit_bank_guarantee = deposit_bank_guarantee
    tenant.deposit_bank_guarantee_amount = _f(deposit_bank_guarantee_amount)
    tenant.insurance_policy_number = insurance_policy_number
    tenant.insurance_expiry = _d(insurance_expiry)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    log_action(session, user, action, "tenant", tenant.id, tenant.name)
    return redirect(f"/properties/{property_id}#tenant")
