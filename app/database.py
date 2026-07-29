"""Database engine and session helpers."""
from sqlmodel import SQLModel, Session, create_engine, select

from .config import settings

_url = settings.database_url
# the app uses a sync driver; transparently rewrite asyncpg URLs to psycopg2
if _url.startswith("postgresql+asyncpg://"):
    _url = _url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

connect_args = {}
if _url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    from . import models  # noqa: F401  (ensure models are registered)
    SQLModel.metadata.create_all(engine)
    _migrate_superuser()


def _migrate_superuser() -> None:
    """One-time role migration: if no superuser exists, promote the oldest
    admin (agency staff) to superuser. Idempotent."""
    from .models import User

    with Session(engine) as session:
        has_super = session.exec(
            select(User).where(User.role == "superuser")
        ).first()
        if has_super:
            return
        oldest_admin = session.exec(
            select(User).where(User.role == "admin").order_by(User.id)
        ).first()
        if oldest_admin:
            oldest_admin.role = "superuser"
            session.add(oldest_admin)
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session
