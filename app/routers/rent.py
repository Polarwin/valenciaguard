"""Rent records, HTMX mark-paid, and the IRAV rent-increase calculator."""
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from ..audit import log_action
from ..auth import csrf_protect, redirect, require_admin
from ..config import settings
from ..database import get_session
from ..models import Property, RentRecord, User, calculate_rent_increase
from ..services.alerts import RENT_DUE_DAY
from ..templates_config import templates

router = APIRouter(tags=["rent"])


@router.post("/properties/{property_id}/rent")
def add_rent_record(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    month: str = Form(...),  # "YYYY-MM"
    amount_due: float = Form(...),
    notes: str = Form(""),
):
    if not session.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    year, mon = (int(part) for part in month.split("-"))
    record = RentRecord(
        property_id=property_id,
        month=date(year, mon, 1),
        amount_due=amount_due,
        notes=notes,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    log_action(session, user, "create", "rent_record", record.id, f"{month} {amount_due}€")
    return redirect(f"/properties/{property_id}#rent")


@router.post("/rent/{record_id}/pay", response_class=HTMLResponse)
def mark_rent_paid(
    record_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    amount_paid: float = Form(...),
    paid_date: str = Form(...),
):
    record = session.get(RentRecord, record_id)
    if not record:
        raise HTTPException(404, "Rent record not found")
    record.amount_paid = amount_paid
    record.paid_date = date.fromisoformat(paid_date)
    due = date(record.month.year, record.month.month, RENT_DUE_DAY)
    record.late_days = max(0, (record.paid_date - due).days)
    record.status = "paid"
    session.add(record)
    session.commit()
    session.refresh(record)
    log_action(session, user, "update", "rent_record", record.id, "marked paid")
    # HTMX: return just the updated row
    return templates.TemplateResponse(request, 
        "partials/rent_row.html",
        {"request": request, "r": record, "today": date.today().isoformat()},
    )


_LETTER_TEMPLATE = """\
{city}, a {today}

Estimado/a {tenant_name}:

Por la presente le comunicamos que, de conformidad con la cláusula de \
actualización de renta del contrato de arrendamiento de la vivienda sita en \
{address}, y conforme al Índice de Referencia de Arrendamientos de Vivienda \
(IRAV) vigente para {year} ({rate_pct} %), la renta mensual se actualizará de la \
siguiente manera:

    Renta actual:        {current_rent:.2f} €
    Incremento máximo:   {increase:.2f} € ({rate_pct} %)
    Nueva renta mensual: {new_rent:.2f} €

La nueva renta será exigible a partir del próximo período de mensualidad \
siguiente a la presente notificación, efectuada con la debida antelación.

Atentamente,
La Administración de la Propiedad
"""


@router.get("/rent/calculator", response_class=HTMLResponse)
def rent_calculator_form(
    request: Request,
    user: User = Depends(require_admin),
):
    return templates.TemplateResponse(request, 
        "rent_calculator.html",
        {"request": request, "user": user, "result": None, "letter": "",
         "rate": settings.irav_rate},
    )


@router.post("/rent/calculator", response_class=HTMLResponse)
def rent_calculator(
    request: Request,
    user: User = Depends(require_admin),
    _csrf: None = Depends(csrf_protect),
    current_rent: float = Form(...),
    tenant_name: str = Form(""),
    address: str = Form(""),
):
    increase, new_rent = calculate_rent_increase(current_rent, settings.irav_rate)
    letter = _LETTER_TEMPLATE.format(
        city="Valencia",
        today=date.today().strftime("%d/%m/%Y"),
        tenant_name=tenant_name or "____________",
        address=address or "____________",
        year=date.today().year,
        rate_pct=f"{settings.irav_rate * 100:.2f}",
        current_rent=current_rent,
        increase=increase,
        new_rent=new_rent,
    )
    return templates.TemplateResponse(request, 
        "rent_calculator.html",
        {
            "request": request, "user": user,
            "result": {"increase": increase, "new_rent": new_rent},
            "letter": letter, "rate": settings.irav_rate,
        },
    )
