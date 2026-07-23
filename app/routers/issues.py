"""Issue tracking with AI triage and owner notifications."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlmodel import Session

from ..audit import log_action
from ..auth import csrf_protect, redirect, require_admin
from ..database import get_session
from ..models import Issue, Owner, Property, User, get_setting
from ..services import ai_service
from ..services.notifications import send_email
from ..config import settings

router = APIRouter(prefix="/properties/{property_id}/issues", tags=["issues"])


@router.post("")
def create_issue(
    property_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    reported_by: str = Form("tenant"),
    category: str = Form("other"),
    description: str = Form(...),
    cost: str = Form(""),
):
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    cost_val = float(cost) if cost else None
    threshold = float(get_setting(session, "cost_threshold", str(settings.cost_threshold)))

    triage = ai_service.triage_issue(description, category, cost_val, threshold)
    issue = Issue(
        property_id=property_id,
        reported_by=reported_by,
        category=category,
        urgency=triage["urgency"],
        description=description,
        cost=cost_val,
        ai_notes=json.dumps(triage, ensure_ascii=False),
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    log_action(session, user, "create", "issue", issue.id, f"{category}/{issue.urgency}")

    # Owner notification for high/urgent or above-threshold costs (in Chinese)
    if issue.urgency in ("high", "urgent") or (cost_val or 0) > threshold:
        owner = session.get(Owner, prop.owner_id)
        if owner:
            body = (
                f"尊敬的{owner.name}：\n\n"
                f"您在 {prop.address} 的房产报告了一项新维修问题。\n"
                f"类别：{issue.category}　紧急程度：{issue.urgency}\n"
                f"问题描述：{issue.description}\n"
                f"预估费用：{cost_val if cost_val is not None else '待报价'} 欧元\n\n"
                f"AI建议（{triage.get('source', 'mock')}）："
                f"责任方判断 — {triage.get('liability', 'unclear')}；"
                f"建议服务商 — {', '.join(triage.get('vendors', []))}；"
                f"{'需要您预先批准（超过 %d 欧元阈值）。' % threshold if triage.get('needs_owner_approval') else '可在阈值内直接处理。'}\n\n"
                f"— ValenciaGuard 物业管理"
            )
            send_email(owner.email, f"【ValenciaGuard】房产维修通知 — {prop.address}", body)
    return redirect(f"/properties/{property_id}#issues")


@router.post("/{issue_id}/status")
def update_issue_status(
    property_id: int,
    issue_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    status: str = Form(...),
    cost: str = Form(""),
    vendor_name: str = Form(""),
):
    issue = session.get(Issue, issue_id)
    if not issue or issue.property_id != property_id:
        raise HTTPException(404, "Issue not found")
    issue.status = status
    if cost:
        issue.cost = float(cost)
    issue.vendor_name = vendor_name
    if status == "resolved" and not issue.resolved_at:
        issue.resolved_at = datetime.utcnow()
    session.add(issue)
    session.commit()
    log_action(session, user, "update", "issue", issue.id, f"status={status}")
    return redirect(f"/properties/{property_id}#issues")
