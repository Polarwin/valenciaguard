"""AI assistant endpoint (admin only) — HTMX chat."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..auth import csrf_protect, require_admin
from ..database import get_session
from ..models import Contract, Property, Tenant, User
from ..services import ai_service
from ..templates_config import templates

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _build_context(session: Session, question: str) -> str:
    """Inject property context when the question references a known address."""
    parts = []
    for prop in session.exec(select(Property)).all():
        # match on a distinctive part of the address or the id
        tokens = [t for t in prop.address.split() if len(t) > 3]
        if f"#{prop.id}" in question or any(t.lower() in question.lower() for t in tokens):
            parts.append(
                f"Property #{prop.id}: {prop.address}, {prop.city} {prop.postal_code}, "
                f"status={prop.status}"
            )
            contract = session.exec(
                select(Contract).where(Contract.property_id == prop.id)
            ).first()
            if contract:
                parts.append(
                    f"  Contract: type={contract.contract_type}, start={contract.start_date}, "
                    f"rent={contract.rent_amount}€, landlord_is_company={contract.landlord_is_company}, "
                    f"mandatory_end={contract.mandatory_end_date}, "
                    f"notice_deadline={contract.notice_deadline_date}, "
                    f"next_rent_update={contract.next_rent_update_date}, "
                    f"tacit_renewal_end={contract.tacit_renewal_end_date}"
                )
            tenant = session.exec(
                select(Tenant).where(Tenant.property_id == prop.id)
            ).first()
            if tenant:
                parts.append(f"  Tenant: {tenant.name}, rent={tenant.rent_amount}€")
    return "\n".join(parts)


@router.post("/ask", response_class=HTMLResponse)
def ask_ai(
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    question: str = Form(...),
):
    context = _build_context(session, question)
    answer = ai_service.ask(question, context)
    return templates.TemplateResponse(request, 
        "partials/ai_answer.html",
        {
            "request": request,
            "question": question,
            "answer": answer,
            "context_used": bool(context),
            "ai_available": ai_service.ai_available(),
        },
    )
