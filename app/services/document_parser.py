"""Document text extraction and keyword-based auto-categorization."""
from __future__ import annotations

import logging

logger = logging.getLogger("valenciaguard.docs")

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# magic bytes that indicate executables / scripts -> reject
_BAD_MAGIC = (b"MZ", b"\x7fELF", b"#!")

_CATEGORY_KEYWORDS = {
    "contract": ("contrato", "arrendamiento", "contract", "inquilino", "arrendador"),
    "deposit_receipt": ("fianza", "depósito", "deposit"),
    "insurance": ("seguro", "póliza", "insurance", "policy"),
    "inspection": ("inspección", "inspection", "informe técnico", "certificado"),
    "invoice": ("factura", "invoice", "presupuesto", "recibo"),
}


def sniff_is_executable(data: bytes) -> bool:
    return any(data.startswith(magic) for magic in _BAD_MAGIC)


def extract_text(file_path: str, ext: str) -> str:
    """Extract text from a stored document. Never raises."""
    try:
        if ext == "pdf":
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            return "\n".join((page.extract_text() or "") for page in reader.pages)[:20000]
        if ext in ("jpg", "jpeg", "png"):
            try:
                import pytesseract  # type: ignore
                from PIL import Image  # type: ignore
            except ImportError:
                logger.info("pytesseract/Pillow not available; skipping OCR for %s", file_path)
                return ""
            return pytesseract.image_to_string(Image.open(file_path))[:20000]
    except Exception:
        logger.exception("Text extraction failed for %s", file_path)
    return ""


def categorize(text: str, fallback: str = "other") -> str:
    low = text.lower()
    scores = {
        cat: sum(low.count(kw) for kw in kws)
        for cat, kws in _CATEGORY_KEYWORDS.items()
    }
    best, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best if best_score > 0 else fallback
