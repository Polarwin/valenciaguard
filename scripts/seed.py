"""Seed the database with demo data.

Usage:  .venv/bin/python -m scripts.seed
Credentials created:  admin / admin123   (superuser — agency boss)
                      owner1 / owner123  (owner portal, Chinese UI)
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.auth import hash_password
from app.database import engine, init_db
from app.models import (
    Contract, Issue, Owner, Property, RentRecord, Settings, Tenant, User,
    compute_contract_dates,
)


def main() -> None:
    init_db()
    with Session(engine) as session:
        if session.exec(select(User)).first():
            print("Database already seeded (users exist). Aborting.")
            return

        admin = User(username="admin", password_hash=hash_password("admin123"), role="superuser")
        owner_user = User(username="owner1", password_hash=hash_password("owner123"), role="owner")
        session.add_all([admin, owner_user])
        session.commit()
        session.refresh(owner_user)

        owner = Owner(
            name="王建军", email="wang@example.com", phone="+86 138 0000 0000",
            wechat="wangjianjun_es", user_id=owner_user.id,
            notes="Vive en Shanghái; prefiere comunicación en chino.",
        )
        session.add(owner)
        session.commit()
        session.refresh(owner)

        prop1 = Property(
            address="Calle Colón 18, 3ºA", city="Valencia", postal_code="46004",
            owner_id=owner.id, purchase_date=date(2019, 6, 1),
            purchase_price=210000, current_value_estimate=265000, status="occupied",
        )
        prop2 = Property(
            address="Avenida del Puerto 74, 1ºB", city="Valencia", postal_code="46023",
            owner_id=owner.id, purchase_date=date(2021, 3, 15),
            purchase_price=180000, current_value_estimate=215000, status="vacant",
        )
        session.add_all([prop1, prop2])
        session.commit()
        session.refresh(prop1)

        tenant = Tenant(
            property_id=prop1.id, name="María García López", nie_dni="X1234567A",
            phone="+34 600 111 222", email="maria.garcia@example.com",
            emergency_contact="Carlos García +34 600 333 444",
            move_in_date=date(2024, 3, 1), contract_start=date(2024, 3, 1),
            contract_end=date(2025, 2, 28), rent_amount=850.0, deposit_amount=850.0,
            deposit_bank_guarantee=True, deposit_bank_guarantee_amount=850.0,
            insurance_policy_number="HOG-2024-99871", insurance_expiry=date(2026, 3, 1),
        )
        session.add(tenant)

        contract = Contract(
            property_id=prop1.id, contract_type="residential",
            start_date=date(2024, 3, 1), end_date=date(2025, 2, 28),
            duration_months=12, rent_amount=850.0, deposit_amount=850.0,
            has_rent_update_clause=True, rent_update_date=date(2025, 3, 1),
            landlord_is_company=False,
        )
        compute_contract_dates(contract)
        session.add(contract)

        today = date.today()
        for i, (year, month, status) in enumerate(
            [
                *((today.year, m, "paid") for m in range(1, today.month)),
                (today.year, today.month, "pending"),
            ]
        ):
            paid = status == "paid"
            session.add(RentRecord(
                property_id=prop1.id, month=date(year, month, 1),
                amount_due=850.0, amount_paid=850.0 if paid else 0.0,
                paid_date=date(year, month, 4) if paid else None,
                status=status,
            ))

        session.add(Issue(
            property_id=prop1.id, reported_by="tenant", category="plumbing",
            urgency="medium", description="El grifo de la cocina gotea constantemente.",
            status="open",
        ))

        for key, value in (
            ("company_name", "ValenciaGuard Gestión"),
            ("notify_email", "admin@valenciaguard.es"),
            ("cost_threshold", "200"),
            ("irav_rate", "0.0214"),
        ):
            session.add(Settings(key=key, value=value))

        session.commit()
        print("Seed complete.")
        print("  admin  / admin123   (superusuario — panel de administración)")
        print("  owner1 / owner123   (portal del propietario, 中文)")


if __name__ == "__main__":
    main()
