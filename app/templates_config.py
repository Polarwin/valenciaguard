"""Shared Jinja2 templates instance."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def fmt_date(value) -> str:
    return value.strftime("%Y-%m-%d") if value else "—"


def fmt_money(value) -> str:
    return f"{value:,.2f} €" if value is not None else "—"


templates.env.filters["date"] = fmt_date
templates.env.filters["money"] = fmt_money
