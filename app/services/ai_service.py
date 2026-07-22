"""Kimi API (OpenAI-compatible) integration with mock fallbacks.

Every public function works without an API key: it returns a sensible canned
response so the app is fully usable offline / in development.
"""
from __future__ import annotations

import json
import logging

import httpx

from ..config import settings

logger = logging.getLogger("valenciaguard.ai")


def ai_available() -> bool:
    return bool(settings.kimi_api_key)


def _chat(system: str, user: str) -> str | None:
    """Call the Kimi chat completions endpoint. Returns None on any failure."""
    if not settings.kimi_api_key:
        return None
    try:
        resp = httpx.post(
            f"{settings.kimi_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.kimi_api_key}"},
            json={
                "model": settings.kimi_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.3,
            },
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("Kimi API call failed, falling back to mock")
        return None


# ---------------------------------------------------------------------------
# Issue triage
# ---------------------------------------------------------------------------

_VENDOR_MAP = {
    "plumbing": ["fontanero (plumber)", "empresa de pocería (drainage)"],
    "electrical": ["electricista autorizado", "servicio técnico eléctrico"],
    "noise": ["mediador vecinal", "técnico acústico"],
    "structural": ["aparejador / arquitecto técnico", "empresa de reformas"],
    "other": ["manitas (handyman)", "empresa multiservicios"],
}


def triage_issue(description: str, category: str, cost: float | None = None,
                 threshold: float = 200.0) -> dict:
    """Suggest urgency, vendors, a Spanish tenant reply and liability.

    Returns a dict with keys: urgency, vendors, draft_response_es, liability,
    needs_owner_approval, source ("kimi" | "mock").
    """
    system = (
        "You are a property-management assistant for rentals in Valencia, Spain, "
        "under the LAU (Ley de Arrendamientos Urbanos). Respond with strict JSON: "
        '{"urgency": "low|medium|high|urgent", "vendors": ["..."], '
        '"draft_response_es": "...", "liability": "landlord|tenant|unclear", '
        '"needs_owner_approval": true|false}'
    )
    user = f"Category: {category}\nDescription: {description}\nEstimated cost: {cost}"
    raw = _chat(system, user)
    if raw:
        try:
            data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            data["source"] = "kimi"
            data.setdefault("vendors", _VENDOR_MAP.get(category, _VENDOR_MAP["other"]))
            return data
        except (ValueError, KeyError):
            pass
    # ---- mock fallback ----
    urgent_words = ("fuga", "inundación", "agua", "gas", "eléctric", "sin luz", "rotura")
    urgency = "high" if any(w in description.lower() for w in urgent_words) else "medium"
    major = category in ("structural",) or (cost is not None and cost > threshold)
    needs_approval = major or (cost is not None and cost > threshold)
    liability = "landlord" if category in ("plumbing", "electrical", "structural") else "unclear"
    return {
        "urgency": urgency,
        "vendors": _VENDOR_MAP.get(category, _VENDOR_MAP["other"]),
        "draft_response_es": (
            "Estimado inquilino: hemos registrado su incidencia y la estamos "
            "gestionando. Un técnico se pondrá en contacto con usted en breve. "
            "Gracias por su aviso. — Gestión de la propiedad"
        ),
        "liability": liability,
        "needs_owner_approval": bool(needs_approval),
        "source": "mock",
    }


# ---------------------------------------------------------------------------
# Free-form assistant
# ---------------------------------------------------------------------------

_MOCK_ANSWER = """\
Respuesta de ejemplo (modo sin API Kimi):

- Actualización de renta 2026: con la cláusula de actualización, el IRAV aplicable \
es 2,14 %. Ejemplo: renta de 850 € → subida máxima 18,19 € → nueva renta 868,19 €. \
Notifique al inquilino por escrito al menos 30 días antes de la fecha de actualización.
- Plazos LAU: contrato con arrendador persona física → duración mínima 5 años \
(7 si es persona jurídica); preaviso de no renovación: 4 meses (arrendador) / \
2 meses (inquilino) antes del vencimiento; prórroga tácita: hasta 3 años más.
- Incidencias: conservación y reparaciones estructurales corresponden al arrendador \
(art. 21 LAU); pequeñas reparaciones por desgaste al inquilino (art. 21.4).

Configure KIMI_API_KEY para respuestas reales con contexto de la propiedad."""


def ask(question: str, context: str = "") -> str:
    system = (
        "You are ValenciaGuard, an assistant for a property management company in "
        "Valencia, Spain. You protect Chinese owners' interests under Spanish rental "
        "law (LAU). Answer concisely and practically. When drafting letters, write "
        "them in Spanish; when summarizing for owners, you may use Chinese."
    )
    user = question if not context else f"Property context:\n{context}\n\nQuestion: {question}"
    answer = _chat(system, user)
    return answer if answer else _MOCK_ANSWER


def translate_quote_to_chinese(quote_text: str) -> str:
    system = "Translate the following vendor quote into clear simplified Chinese, keeping amounts and dates exact."
    answer = _chat(system, quote_text)
    if answer:
        return answer
    return f"【模拟翻译】报价单内容（未配置 Kimi API，以下为原文摘要）：\n{quote_text[:500]}"


# ---------------------------------------------------------------------------
# Contract parsing
# ---------------------------------------------------------------------------

_MOCK_PARSE = {
    "contract_type": "residential",
    "start_date": "2025-01-15",
    "end_date": "2026-01-14",
    "duration_months": 12,
    "rent_amount": 850.0,
    "deposit_amount": 850.0,
    "has_rent_update_clause": True,
    "rent_update_date": "2026-01-15",
    "landlord_is_company": False,
    "notes": "Extracción de ejemplo (sin API Kimi). Revise los valores manualmente.",
}


def parse_contract_text(text: str) -> dict:
    system = (
        "Extract key data from this Spanish rental contract. Respond with strict JSON "
        'with keys: contract_type ("residential"|"seasonal"), start_date (YYYY-MM-DD), '
        "end_date, duration_months (int), rent_amount (number), deposit_amount (number), "
        "has_rent_update_clause (bool), rent_update_date (YYYY-MM-DD or null), "
        "landlord_is_company (bool), notes (short string)."
    )
    raw = _chat(system, text[:8000])
    if raw:
        try:
            data = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            data["source"] = "kimi"
            return data
        except (ValueError, KeyError):
            pass
    result = dict(_MOCK_PARSE)
    result["source"] = "mock"
    return result
