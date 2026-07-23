"""Owner portal — read-only, Chinese UI, strictly scoped to the owner's properties."""
import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlmodel import Session, select

from ..auth import require_owner
from ..database import get_session
from ..models import Contract, Document, Issue, Owner, Property, RentRecord, User
from ..services import reports
from ..templates_config import templates

router = APIRouter(prefix="/owner-portal", tags=["portal"])



def _scoped_property(session: Session, owner: Owner, property_id: int) -> Property:
    prop = session.get(Property, property_id)
    if not prop or prop.owner_id != owner.id:
        raise HTTPException(404, "Not found")
    return prop


@router.get("", response_class=HTMLResponse)
def portal_dashboard(
    request: Request,
    auth: tuple[User, Owner] = Depends(require_owner),
    session: Session = Depends(get_session),
):
    user, owner = auth
    properties = session.exec(
        select(Property).where(Property.owner_id == owner.id)
    ).all()
    prop_ids = [p.id for p in properties]
    total_rent = 0.0
    occupied = 0
    for p in properties:
        if p.status == "occupied":
            occupied += 1
        tenant_rent = session.exec(
            select(RentRecord).where(
                RentRecord.property_id == p.id,
                RentRecord.month == date.today().replace(day=1),
            )
        ).first()
        if tenant_rent:
            total_rent += tenant_rent.amount_due
    pending_issues = 0
    if prop_ids:
        pending_issues = len(session.exec(
            select(Issue).where(Issue.property_id.in_(prop_ids), Issue.status.in_(["open", "in_progress"]))
        ).all())
    occupancy = round(100 * occupied / len(properties)) if properties else 0
    return templates.TemplateResponse(request, 
        "portal/dashboard.html",
        {
            "request": request, "user": user, "owner": owner,
            "properties": properties, "total_rent": total_rent,
            "occupancy": occupancy, "pending_issues": pending_issues,
        },
    )


@router.get("/properties/{property_id}", response_class=HTMLResponse)
def portal_property_detail(
    property_id: int,
    request: Request,
    auth: tuple[User, Owner] = Depends(require_owner),
    session: Session = Depends(get_session),
):
    user, owner = auth
    prop = _scoped_property(session, owner, property_id)
    rent_records = session.exec(
        select(RentRecord).where(RentRecord.property_id == property_id)
        .order_by(RentRecord.month.desc())
    ).all()
    issues = session.exec(
        select(Issue).where(Issue.property_id == property_id)
        .order_by(Issue.created_at.desc())
    ).all()
    documents = session.exec(
        select(Document).where(Document.property_id == property_id)
        .order_by(Document.upload_date.desc())
    ).all()
    contract = session.exec(
        select(Contract).where(Contract.property_id == property_id)
        .order_by(Contract.start_date.desc())
    ).first()
    countdown = None
    if contract and contract.notice_deadline_date:
        countdown = (contract.notice_deadline_date - date.today()).days
    return templates.TemplateResponse(request, 
        "portal/property.html",
        {
            "request": request, "user": user, "owner": owner, "prop": prop,
            "rent_records": rent_records, "issues": issues, "documents": documents,
            "contract": contract, "countdown": countdown,
            "today": date.today(),
        },
    )


@router.get("/properties/{property_id}/report")
def portal_monthly_report(
    property_id: int,
    auth: tuple[User, Owner] = Depends(require_owner),
    session: Session = Depends(get_session),
    year: int | None = None,
    month: int | None = None,
):
    _user, owner = auth
    prop = _scoped_property(session, owner, property_id)
    today = date.today()
    pdf_bytes = reports.generate_monthly_report(
        session, prop, year or today.year, month or today.month
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=report_{prop.id}.pdf"},
    )


@router.get("/documents/{document_id}/download")
def portal_document_download(
    document_id: int,
    auth: tuple[User, Owner] = Depends(require_owner),
    session: Session = Depends(get_session),
):
    _user, owner = auth
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Not found")
    _scoped_property(session, owner, doc.property_id)  # strict scoping
    if not os.path.exists(doc.file_path):
        raise HTTPException(404, "File missing on disk")
    return FileResponse(doc.file_path, filename=doc.filename)
