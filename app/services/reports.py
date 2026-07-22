"""Monthly owner report PDF generation (Chinese) using fpdf2.

A CJK TTF font is required for proper Chinese rendering; set CJK_FONT_PATH.
If the font is missing the PDF is still generated with a warning and
non-Latin characters replaced, so the route never 500s.
"""
from __future__ import annotations

import logging
import os
from datetime import date

from fpdf import FPDF
from sqlmodel import Session, select

from ..config import settings
from ..models import Issue, Property, RentRecord

logger = logging.getLogger("valenciaguard.reports")


def _first_of_month(year: int, month: int) -> date:
    return date(year, month, 1)


def generate_monthly_report(
    session: Session, prop: Property, year: int, month: int
) -> bytes:
    """Build the monthly report PDF for one property. Returns PDF bytes."""
    first = _first_of_month(year, month)
    records = session.exec(
        select(RentRecord).where(
            RentRecord.property_id == prop.id, RentRecord.month == first
        )
    ).all()
    issues = session.exec(
        select(Issue).where(Issue.property_id == prop.id)
    ).all()
    resolved_this_month = [
        i for i in issues
        if i.resolved_at and i.resolved_at.year == year and i.resolved_at.month == month
    ]
    expenses = sum(i.cost or 0 for i in resolved_this_month)
    income = sum(r.amount_paid for r in records)

    pdf = FPDF()
    pdf.add_page()
    use_cjk = False
    if settings.cjk_font_path and os.path.exists(settings.cjk_font_path):
        pdf.add_font("cjk", "", settings.cjk_font_path)
        pdf.set_font("cjk", size=14)
        use_cjk = True
    else:
        pdf.set_font("helvetica", size=14)
        logger.warning("CJK font not found (CJK_FONT_PATH=%r); report will use fallback text",
                       settings.cjk_font_path)

    def w(text: str) -> str:
        if use_cjk:
            return text
        return text.encode("latin-1", "replace").decode("latin-1")

    if not use_cjk:
        pdf.cell(0, 8, w("WARNING: CJK font not configured - Chinese text may be unreadable."), new_x="LMARGIN", new_y="NEXT")

    pdf.cell(0, 10, w(f"ValenciaGuard 月度报告 — {year}年{month}月"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font_size(11)
    pdf.cell(0, 8, w(f"房产: {prop.address}, {prop.city} {prop.postal_code}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, w(f"状态: {prop.status}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.cell(0, 8, w("一、收入"), new_x="LMARGIN", new_y="NEXT")
    if records:
        for r in records:
            pdf.cell(0, 7, w(f"  租金 {r.month:%Y-%m}: 应收 {r.amount_due:.2f} € / 实收 {r.amount_paid:.2f} € / 状态 {r.status}"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 7, w("  本月无租金记录。"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, w(f"  收入合计: {income:.2f} €"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.cell(0, 8, w("二、支出（本月已解决的维修）"), new_x="LMARGIN", new_y="NEXT")
    if resolved_this_month:
        for i in resolved_this_month:
            pdf.cell(0, 7, w(f"  [{i.category}] {i.description[:60]} — {i.cost or 0:.2f} €"), new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 7, w("  本月无维修支出。"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, w(f"  支出合计: {expenses:.2f} €"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.cell(0, 8, w("三、净收益"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, w(f"  {income - expenses:.2f} €"), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
