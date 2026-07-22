"""Upload validation: extensions, magic-byte sniffing, happy path."""
import io

import pytest
from fastapi import HTTPException

from app.routers.documents import validate_upload
from tests.conftest import get_csrf

MINIMAL_PDF = (
    b"%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF"
)


def test_reject_bad_extension():
    with pytest.raises(HTTPException) as exc:
        validate_upload("evil.exe", b"MZ....")
    assert exc.value.status_code == 400


def test_reject_executable_magic_bytes_even_with_pdf_extension():
    with pytest.raises(HTTPException):
        validate_upload("contract.pdf", b"MZ\x90\x00 fake exe")
    with pytest.raises(HTTPException):
        validate_upload("contract.pdf", b"\x7fELF fake")
    with pytest.raises(HTTPException):
        validate_upload("contract.pdf", b"#!/bin/sh\nrm -rf /")


def test_reject_oversized():
    with pytest.raises(HTTPException) as exc:
        validate_upload("big.pdf", b"x" * (10 * 1024 * 1024 + 1))
    assert exc.value.status_code == 400


def test_accept_valid_pdf():
    assert validate_upload("contract.PDF", MINIMAL_PDF) == "pdf"


def test_upload_endpoint_happy_path(admin_client):
    csrf = get_csrf(admin_client, "/properties/1")
    resp = admin_client.post(
        "/properties/1/documents",
        data={"csrf_token": csrf, "category": "auto"},
        files={"file": ("contrato.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_upload_endpoint_rejects_exe(admin_client):
    csrf = get_csrf(admin_client, "/properties/1")
    resp = admin_client.post(
        "/properties/1/documents",
        data={"csrf_token": csrf, "category": "auto"},
        files={"file": ("evil.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
        follow_redirects=False,
    )
    assert resp.status_code == 400
