"""SQLModel data models plus pure date/money business-logic helpers."""
from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested directly)
# ---------------------------------------------------------------------------

def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year + years, month=2, day=28)


def add_months(d: date, months: int) -> date:
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    # clamp day to end of month
    if month == 12:
        next_first = date(year + 1, 1, 1)
    else:
        next_first = date(year, month + 1, 1)
    last_day = (next_first.toordinal() - 1)
    day = min(d.day, date.fromordinal(last_day).day)
    return date(year, month, day)


def compute_contract_dates(c: "Contract", today: Optional[date] = None) -> "Contract":
    """Auto-calculate LAU key dates on a Contract (mutates and returns it)."""
    today = today or date.today()
    years = 7 if c.landlord_is_company else 5
    c.mandatory_end_date = add_years(c.start_date, years)
    c.tacit_renewal_end_date = add_years(c.mandatory_end_date, 3)
    c.notice_deadline_date = add_months(c.mandatory_end_date, -4)
    if c.has_rent_update_clause:
        base = c.rent_update_date or add_years(c.start_date, 1)
        nxt = base
        while nxt < today:
            nxt = add_years(nxt, 1)
        c.next_rent_update_date = nxt
    else:
        c.next_rent_update_date = None
    return c


def calculate_rent_increase(current_rent: float, rate: float) -> tuple[float, float]:
    """Return (max_increase, new_rent) under the IRAV cap, rounded to cents."""
    max_increase = round(current_rent * rate, 2)
    return max_increase, round(current_rent + max_increase, 2)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: str = "owner"  # "admin" | "owner"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Owner(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = ""
    phone: str = ""
    wechat: str = ""
    notes: str = ""
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    properties: list["Property"] = Relationship(back_populates="owner")


class Property(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    address: str
    city: str = "Valencia"
    postal_code: str = ""
    owner_id: int = Field(foreign_key="owner.id", index=True)
    purchase_date: Optional[date] = None
    purchase_price: Optional[float] = None
    current_value_estimate: Optional[float] = None
    status: str = "vacant"  # occupied | vacant | pending_handover
    created_at: datetime = Field(default_factory=datetime.utcnow)

    owner: Optional[Owner] = Relationship(back_populates="properties")


class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", unique=True, index=True)
    name: str
    nie_dni: str = ""
    phone: str = ""
    email: str = ""
    emergency_contact: str = ""
    move_in_date: Optional[date] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    rent_amount: float = 0.0
    deposit_amount: float = 0.0
    deposit_bank_guarantee: bool = False
    deposit_bank_guarantee_amount: Optional[float] = None
    insurance_policy_number: str = ""
    insurance_expiry: Optional[date] = None


class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    contract_type: str = "residential"  # residential | seasonal
    start_date: date
    end_date: Optional[date] = None
    duration_months: int = 12
    rent_amount: float = 0.0
    deposit_amount: float = 0.0
    has_rent_update_clause: bool = False
    rent_update_date: Optional[date] = None
    last_rent_update_amount: Optional[float] = None
    contract_file_path: str = ""
    landlord_is_company: bool = False
    # auto-calculated on save (see compute_contract_dates)
    mandatory_end_date: Optional[date] = None
    notice_deadline_date: Optional[date] = None
    next_rent_update_date: Optional[date] = None
    tacit_renewal_end_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RentRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    month: date  # stored as first day of month
    amount_due: float
    amount_paid: float = 0.0
    paid_date: Optional[date] = None
    status: str = "pending"  # paid | pending | late
    late_days: int = 0
    notes: str = ""


class Issue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    reported_by: str = "tenant"  # tenant | owner | admin
    category: str = "other"  # plumbing | electrical | noise | structural | other
    urgency: str = "medium"  # low | medium | high | urgent
    description: str
    status: str = "open"  # open | in_progress | resolved | closed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    cost: Optional[float] = None
    vendor_name: str = ""
    ai_notes: str = ""  # JSON-ish AI triage summary


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    category: str = "other"  # contract | deposit_receipt | insurance | inspection | invoice | other
    filename: str  # original name
    file_path: str  # stored path (randomized name, outside web root)
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    extracted_text: str = ""
    key_dates_json: str = ""


class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(foreign_key="property.id", index=True)
    alert_type: str  # notice_deadline | mandatory_end | rent_update | insurance_expiry | rent_due | rent_late
    message: str = ""
    due_date: date
    status: str = "pending"  # pending | notified | dismissed
    notified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = None
    username: str = ""
    action: str  # create | update | delete
    entity: str
    entity_id: Optional[int] = None
    detail: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Settings(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str = ""


def get_setting(session, key: str, default: str = "") -> str:
    row = session.get(Settings, key)
    return row.value if row else default
