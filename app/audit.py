"""Simple audit log helper — written on create/update/delete actions."""
from typing import Optional

from sqlmodel import Session

from .models import AuditLog, User


def log_action(
    session: Session,
    user: Optional[User],
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    detail: str = "",
) -> None:
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail,
    )
    session.add(entry)
    session.commit()
