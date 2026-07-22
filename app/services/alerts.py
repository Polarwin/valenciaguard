"""Alert generation and rent reminders.

Run standalone:  python -m app.services.alerts
Also called on admin dashboard load.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlmodel import Session, select

from ..config import settings
from ..database import get_session, init_db
from ..models import Alert, Contract, Owner, Property, RentRecord, Tenant
from .notifications import send_email

logger = logging.getLogger("valenciaguard.alerts")

ALERT_WINDOW_DAYS = 180      # create alerts for deadlines within 6 months
NOTIFY_WINDOW_DAYS = 30      # email-notify for alerts due within 30 days
RENT_DUE_DAY = 5             # rent is due on the 5th of each month

_ALERT_LABELS = {
    "notice_deadline": "Contract 4-month notice deadline",
    "mandatory_end": "Contract mandatory end (LAU)",
    "rent_update": "Annual rent update date",
    "insurance_expiry": "Tenant insurance expiry",
    "rent_due": "Rent due soon",
    "rent_late": "Rent overdue",
}


def _upsert_alert(session: Session, property_id: int, alert_type: str,
                  due: date, message: str, today: date) -> Alert | None:
    if due < today - timedelta(days=1) or due > today + timedelta(days=ALERT_WINDOW_DAYS):
        return None
    existing = session.exec(
        select(Alert).where(
            Alert.property_id == property_id,
            Alert.alert_type == alert_type,
            Alert.due_date == due,
        )
    ).first()
    if existing:
        return existing
    alert = Alert(
        property_id=property_id,
        alert_type=alert_type,
        message=message,
        due_date=due,
    )
    session.add(alert)
    return alert


def check_alerts(session: Session, today: date | None = None) -> list[Alert]:
    """Scan contracts, insurance and rent records; create & notify alerts."""
    today = today or date.today()

    for contract in session.exec(select(Contract)).all():
        prop = session.get(Property, contract.property_id)
        addr = prop.address if prop else f"property #{contract.property_id}"
        for alert_type, due in (
            ("notice_deadline", contract.notice_deadline_date),
            ("mandatory_end", contract.mandatory_end_date),
            ("rent_update", contract.next_rent_update_date),
        ):
            if due:
                _upsert_alert(session, contract.property_id, alert_type, due,
                              f"{_ALERT_LABELS[alert_type]} for {addr}", today)

    for tenant in session.exec(select(Tenant)).all():
        if tenant.insurance_expiry:
            prop = session.get(Property, tenant.property_id)
            addr = prop.address if prop else f"property #{tenant.property_id}"
            _upsert_alert(session, tenant.property_id, "insurance_expiry",
                          tenant.insurance_expiry,
                          f"Insurance expires for {addr} (policy {tenant.insurance_policy_number})",
                          today)

    # rent reminders: 3 days before due -> email tenant; 1 day after -> admin alert
    for rec in session.exec(
        select(RentRecord).where(RentRecord.status != "paid")
    ).all():
        due = date(rec.month.year, rec.month.month, RENT_DUE_DAY)
        prop = session.get(Property, rec.property_id)
        addr = prop.address if prop else f"property #{rec.property_id}"
        if today == due - timedelta(days=3):
            tenant = session.exec(
                select(Tenant).where(Tenant.property_id == rec.property_id)
            ).first()
            if tenant and tenant.email:
                send_email(
                    tenant.email,
                    f"Recordatorio de alquiler — {rec.month:%B %Y}",
                    f"Estimado/a {tenant.name}: le recordamos que el alquiler de "
                    f"{rec.amount_due:.2f} € vence el día {due.isoformat()}. Gracias.",
                )
        if today >= due + timedelta(days=1):
            late_days = (today - due).days
            if rec.status != "late":
                rec.status = "late"
                rec.late_days = late_days
                session.add(rec)
            _upsert_alert(session, rec.property_id, "rent_late", due,
                          f"Rent for {addr} ({rec.month:%Y-%m}) is {late_days} day(s) late",
                          today)
        else:
            _upsert_alert(session, rec.property_id, "rent_due", due,
                          f"Rent for {addr} ({rec.month:%Y-%m}) due on {due.isoformat()}",
                          today)

    session.commit()

    # notify: email admin + mark notified for anything due within 30 days
    notified_alerts: list[Alert] = []
    for alert in session.exec(
        select(Alert).where(Alert.status == "pending", Alert.notified == False)  # noqa: E712
    ).all():
        if alert.due_date <= today + timedelta(days=NOTIFY_WINDOW_DAYS):
            send_email(
                settings.notify_email,
                f"[ValenciaGuard] {alert.alert_type} — {alert.due_date.isoformat()}",
                alert.message,
            )
            alert.notified = True
            alert.status = "notified"
            session.add(alert)
            notified_alerts.append(alert)
    session.commit()
    return notified_alerts


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()
    session_gen = get_session()
    session = next(session_gen)
    try:
        alerts = check_alerts(session)
        print(f"Alert check complete. {len(alerts)} new notification(s) sent.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
