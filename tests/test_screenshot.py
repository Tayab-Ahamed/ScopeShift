"""Tests for Task 4: Real screenshot header parsing and crop transcription verification."""
import io
import pytest
from PIL import Image

from scopeshift.validation import (
    ValidationError,
    get_image_size,
    crop_image,
    verify_screenshot_crop,
    validate_claim,
)


def _make_test_png(width=800, height=600) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_test_jpeg(width=640, height=480) -> bytes:
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_real_dimensions_parsed_from_png_and_jpeg_headers():
    png_data = _make_test_png(1024, 768)
    assert get_image_size(png_data) == (1024, 768)

    jpeg_data = _make_test_jpeg(800, 600)
    assert get_image_size(jpeg_data) == (800, 600)


def test_screenshot_correct_quote_verified():
    img_bytes = _make_test_png(900, 620)
    raw = {
        "claim_id": "checkout.payment_methods",
        "quote": "Pay with Card",
        "observation": "Card button visible",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
        "region": [460, 285, 370, 80],
    }
    # Transcriber simulates separate Gemini call transcribing the cropped region
    mock_transcriber = lambda crop: "Pay with Card and UPI"

    validated = validate_claim(
        raw,
        "screenshot",
        image_bytes=img_bytes,
        transcriber=mock_transcriber,
    )
    assert validated["quote_verified"] is True
    assert validated["region"] == (460, 285, 370, 80)


def test_screenshot_fabricated_quote_rejected():
    img_bytes = _make_test_png(900, 620)
    raw = {
        "claim_id": "checkout.payment_methods",
        "quote": "Cryptocurrency Approved At Checkout",
        "observation": "Fabricated text claim",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
        "region": [460, 285, 370, 80],
    }
    # Separate transcriber returns actual image text ("Pay with Card")
    mock_transcriber = lambda crop: "Pay with Card"

    validated = validate_claim(
        raw,
        "screenshot",
        image_bytes=img_bytes,
        transcriber=mock_transcriber,
    )
    # String match fails -> quote_verified must be False
    assert validated["quote_verified"] is False


def test_screenshot_region_out_of_bounds_rejected():
    img_bytes = _make_test_png(800, 600)
    raw = {
        "claim_id": "checkout.payment_methods",
        "quote": "Pay with Card",
        "observation": "Out of bounds box",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
        "region": [750, 550, 100, 100],  # extends beyond 800x600 (x+w = 850 > 800)
    }
    mock_transcriber = lambda crop: "Pay with Card"

    validated = validate_claim(
        raw,
        "screenshot",
        image_bytes=img_bytes,
        transcriber=mock_transcriber,
    )
    assert validated["quote_verified"] is False
    assert validated["region"] is None


def test_screenshot_verifier_outage_fails_closed():
    img_bytes = _make_test_png(900, 620)
    raw = {
        "claim_id": "checkout.payment_methods",
        "quote": "Pay with Card",
        "observation": "Card button visible",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
        "region": [460, 285, 370, 80],
    }

    # Case A: transcriber raises an Exception (Gemini outage / timeout / 503)
    def broken_transcriber(crop):
        raise RuntimeError("Gemini API connection error")

    val_a = validate_claim(
        raw,
        "screenshot",
        image_bytes=img_bytes,
        transcriber=broken_transcriber,
    )
    assert val_a["quote_verified"] is False

    # Case B: transcriber is None (offline verifier)
    val_b = validate_claim(
        raw,
        "screenshot",
        image_bytes=img_bytes,
        transcriber=None,
    )
    assert val_b["quote_verified"] is False
