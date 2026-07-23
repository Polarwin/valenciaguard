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


# available in every template as {{ prefix }} — "" at root, "/valenciaguard"
# when mounted under a subpath. root_path is fixed per process (from env).
from .config import settings  # noqa: E402
from .i18n import lang_proxy, t  # noqa: E402

templates.env.globals["prefix"] = settings.root_path
templates.env.globals["t"] = t
templates.env.globals["lang"] = lang_proxy
