"""Database engine and session helpers."""
from sqlmodel import SQLModel, Session, create_engine

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


def get_session():
    with Session(engine) as session:
        yield session
