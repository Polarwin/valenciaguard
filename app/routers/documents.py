"""Document upload/download with validation and auto-categorization."""
import os
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from ..audit import log_action
from ..auth import csrf_protect, redirect, require_admin
from ..config import settings
from ..database import get_session
from ..models import Document, Property, User
from ..services import document_parser

router = APIRouter(prefix="/properties/{property_id}/documents", tags=["documents"])


def validate_upload(filename: str, data: bytes) -> str:
    """Return the lowercase extension if valid, else raise 400."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in document_parser.ALLOWED_EXTENSIONS:
        raise HTTPException(400, "File type not allowed (pdf/jpg/jpeg/png only)")
    if len(data) > document_parser.MAX_UPLOAD_BYTES:
        raise HTTPException(400, "File too large (max 10 MB)")
    if document_parser.sniff_is_executable(data):
        raise HTTPException(400, "Executable content rejected")
    return ext


def store_file(property_id: int, ext: str, data: bytes) -> str:
    folder = os.path.join(settings.upload_dir, f"property_{property_id}")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{uuid.uuid4().hex}.{ext}")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


@router.post("")
async def upload_document(
    property_id: int,
    request: Request,
    file: UploadFile,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
    category: str = Form("auto"),
):
    if not session.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    data = await file.read()
    ext = validate_upload(file.filename or "", data)
    path = store_file(property_id, ext, data)
    text = document_parser.extract_text(path, ext)
    final_category = document_parser.categorize(text) if category == "auto" else category
    doc = Document(
        property_id=property_id,
        category=final_category,
        filename=file.filename or "file",
        file_path=path,
        extracted_text=text,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    log_action(session, user, "create", "document", doc.id, doc.filename)
    return redirect(f"/properties/{property_id}#documents")


@router.get("/{document_id}/download")
def download_document(
    property_id: int,
    document_id: int,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    doc = session.get(Document, document_id)
    if not doc or doc.property_id != property_id:
        raise HTTPException(404, "Document not found")
    if not os.path.exists(doc.file_path):
        raise HTTPException(404, "File missing on disk")
    return FileResponse(doc.file_path, filename=doc.filename)


@router.post("/{document_id}/delete")
def delete_document(
    property_id: int,
    document_id: int,
    request: Request,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session),
    _csrf: None = Depends(csrf_protect),
):
    doc = session.get(Document, document_id)
    if not doc or doc.property_id != property_id:
        raise HTTPException(404, "Document not found")
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    session.delete(doc)
    session.commit()
    log_action(session, user, "delete", "document", document_id, doc.filename)
    return redirect(f"/properties/{property_id}#documents")
