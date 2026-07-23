"""Contract CRUD with auto-calculated LAU key dates + PDF parse endpoint."""
import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..audit import log_action
from ..auth import csrf_protect, redirect, require_admin
from ..database import get_session
from ..i18n import t as _t
from ..models import Contract, Property, User, compute_contract_dates
from ..services import ai_service, document_parser
from ..templates_config import templates

router = APIRouter(prefix="/properties/{property_id}/contracts", tags=["contracts"])


def _d(value: str) -> Optional[date]:
    return date.fromisoformat(value) if value else None


@router.post("")
def create_contract(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    contract_type: str = Form("residential"),
    start_date: str = Form(...),
    end_date: str = Form(""),
    duration_months: int = Form(12),
    rent_amount: float = Form(0.0),
    deposit_amount: float = Form(0.0),
    has_rent_update_clause: bool = Form(False),
    rent_update_date: str = Form(""),
    last_rent_update_amount: str = Form(""),
    landlord_is_company: bool = Form(False),
):
    if not session.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    contract = Contract(
        property_id=property_id,
        contract_type=contract_type,
        start_date=date.fromisoformat(start_date),
        end_date=_d(end_date),
        duration_months=duration_months,
        rent_amount=rent_amount,
        deposit_amount=deposit_amount,
        has_rent_update_clause=has_rent_update_clause,
        rent_update_date=_d(rent_update_date),
        last_rent_update_amount=float(last_rent_update_amount) if last_rent_update_amount else None,
        landlord_is_company=landlord_is_company,
    )
    compute_contract_dates(contract)
    session.add(contract)
    session.commit()
    session.refresh(contract)
    log_action(session, user, "create", "contract", contract.id,
               f"property {property_id}, start {contract.start_date}")
    return redirect(f"/properties/{property_id}#contract")


@router.post("/{contract_id}/delete")
def delete_contract(
    property_id: int,
    contract_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    contract = session.get(Contract, contract_id)
    if not contract or contract.property_id != property_id:
        raise HTTPException(404, "Contract not found")
    session.delete(contract)
    session.commit()
    log_action(session, user, "delete", "contract", contract_id)
    return redirect(f"/properties/{property_id}#contract")


@router.post("/parse", response_class=HTMLResponse)
async def parse_contract_upload(
    property_id: int,
    request: Request,
    file: UploadFile,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    """HTMX endpoint: extract key fields from an uploaded contract PDF (AI + mock)."""
    data = await file.read()
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext != "pdf" or document_parser.sniff_is_executable(data):
        return templates.TemplateResponse(request, 
            "partials/contract_parse.html",
            {"request": request, "result": None, "error": _t("contract.parse_error")},
        )
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        text = document_parser.extract_text(tmp.name, "pdf")
    result = ai_service.parse_contract_text(text) if text else dict(ai_service._MOCK_PARSE, source="mock")
    return templates.TemplateResponse(request, 
        "partials/contract_parse.html",
        {"request": request, "result": result, "result_json": json.dumps(result, indent=1), "error": ""},
    )
