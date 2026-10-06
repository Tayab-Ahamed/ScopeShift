"""Tests for Task D: Scanned PDF handling and fail-closed verification."""
from __future__ import annotations

import io
import pytest
from PIL import Image, ImageDraw

from scopeshift.validation import (
    validate_claim,
    render_pdf_page_to_image,
    verify_scanned_pdf_quote,
)


def make_scanned_pdf_bytes(text: str = "REQ-PAY-01: Checkout shall support UPI payments only.") -> bytes:
    """Create a synthetic single-page PDF containing an image of text, so pypdf sees no text."""
    img = Image.new("RGB", (600, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 80), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PDF")
    return buf.getvalue()


def test_scanned_pdf_pypdf_extracts_no_text():
    pdf_bytes = make_scanned_pdf_bytes("Test invoice")
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert len(extracted.strip()) < 50


def test_render_pdf_page_to_image():
    pdf_bytes = make_scanned_pdf_bytes("Rendering check")
    img_bytes = render_pdf_page_to_image(pdf_bytes, page_index=0)
    assert len(img_bytes) > 0
    with Image.open(io.BytesIO(img_bytes)) as img:
        assert img.width > 0
        assert img.height > 0


def test_scanned_pdf_verified_with_mock_transcriber():
    pdf_bytes = make_scanned_pdf_bytes("REQ-PAY-01: Checkout shall support UPI payments only.")
    raw_claim = {
        "claim_id": "checkout.payment_methods",
        "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
        "observation": "Scanned BRD requires UPI only.",
        "proposed_scope_change": False,
        "value": {"methods": ["UPI"]},
    }

    mock_transcriber = lambda crop: "Document header\nREQ-PAY-01: Checkout shall support UPI payments only.\nFooter"

    result = validate_claim(
        raw_claim,
        source_type="brd",
        text="",  # pypdf extracted almost no text
        pdf_bytes=pdf_bytes,
        transcriber=mock_transcriber,
    )

    assert result["quote_verified"] is True
    assert result["claim_id"] == "checkout.payment_methods"


def test_scanned_pdf_unverified_when_transcriber_does_not_contain_quote():
    pdf_bytes = make_scanned_pdf_bytes("Some completely different text")
    raw_claim = {
        "claim_id": "checkout.payment_methods",
        "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
        "observation": "Fabricated claim not on page.",
        "proposed_scope_change": False,
        "value": {"methods": ["UPI"]},
    }

    mock_transcriber = lambda crop: "Unrelated text: Total balance due is $100."

    result = validate_claim(
        raw_claim,
        source_type="brd",
        text="",
        pdf_bytes=pdf_bytes,
        transcriber=mock_transcriber,
    )

    assert result["quote_verified"] is False


def test_scanned_pdf_fail_closed_missing_transcriber():
    pdf_bytes = make_scanned_pdf_bytes("REQ-PAY-01: Checkout shall support UPI payments only.")
    raw_claim = {
        "claim_id": "checkout.payment_methods",
        "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
        "observation": "Scanned document with verifier offline.",
        "proposed_scope_change": False,
        "value": {"methods": ["UPI"]},
    }

    # Transcriber is None (verifier offline or unconfigured)
    result = validate_claim(
        raw_claim,
        source_type="brd",
        text="",
        pdf_bytes=pdf_bytes,
        transcriber=None,
    )

    assert result["quote_verified"] is False


def test_scanned_pdf_fail_closed_transcriber_exception():
    pdf_bytes = make_scanned_pdf_bytes("REQ-PAY-01: Checkout shall support UPI payments only.")
    raw_claim = {
        "claim_id": "checkout.payment_methods",
        "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
        "observation": "Scanned document with transcriber error.",
        "proposed_scope_change": False,
        "value": {"methods": ["UPI"]},
    }

    def failing_transcriber(crop: bytes):
        raise RuntimeError("Gemini API connection error 503")

    result = validate_claim(
        raw_claim,
        source_type="brd",
        text="",
        pdf_bytes=pdf_bytes,
        transcriber=failing_transcriber,
    )

    # Must fail closed without crashing
    assert result["quote_verified"] is False


def test_scanned_pdf_with_region_crop_and_out_of_bounds():
    pdf_bytes = make_scanned_pdf_bytes("REQ-PAY-01: Checkout shall support UPI payments only.")
    raw_claim = {
        "claim_id": "checkout.payment_methods",
        "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
        "value": {"methods": ["UPI"]},
        "region": [10, 10, 200, 100],
    }

    mock_transcriber = lambda crop: "REQ-PAY-01: Checkout shall support UPI payments only."

    # In bounds region
    res = validate_claim(
        raw_claim,
        source_type="brd",
        text="",
        pdf_bytes=pdf_bytes,
        transcriber=mock_transcriber,
    )
    assert res["quote_verified"] is True
    assert res["region"] == (10, 10, 200, 100)

    # Out of bounds region fails closed
    bad_claim = dict(raw_claim)
    bad_claim["region"] = [99999, 99999, 500, 500]
    bad_res = validate_claim(
        bad_claim,
        source_type="brd",
        text="",
        pdf_bytes=pdf_bytes,
        transcriber=mock_transcriber,
    )
    assert bad_res["quote_verified"] is False


def test_scanned_pdf_rendering_unavailable_fails_closed(monkeypatch):
    pdf_bytes = make_scanned_pdf_bytes("REQ-PAY-01: Checkout shall support UPI payments only.")
    raw_claim = {
        "claim_id": "checkout.payment_methods",
        "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
        "value": {"methods": ["UPI"]},
    }
    mock_transcriber = lambda crop: "REQ-PAY-01: Checkout shall support UPI payments only."

    monkeypatch.setattr("scopeshift.validation.render_pdf_page_to_image", lambda *a, **k: b"")

    res = validate_claim(
        raw_claim,
        source_type="brd",
        text="",
        pdf_bytes=pdf_bytes,
        transcriber=mock_transcriber,
    )
    assert res["quote_verified"] is False


def test_digital_pdf_uses_extracted_text_directly():
    pdf_bytes = make_scanned_pdf_bytes("Sample")
    digital_text = (
        "REQ-PAY-01: Checkout shall support UPI payments only. "
        "This is a long digital BRD document with lots of text that pypdf extracted easily."
    )
    raw_claim = {
        "claim_id": "checkout.payment_methods",
        "quote": "REQ-PAY-01: Checkout shall support UPI payments only.",
        "value": {"methods": ["UPI"]},
    }
    # No transcriber provided, but text >= 50 chars matches quote
    res = validate_claim(
        raw_claim,
        source_type="brd",
        text=digital_text,
        pdf_bytes=pdf_bytes,
        transcriber=None,
    )
    assert res["quote_verified"] is True
