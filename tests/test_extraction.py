"""Tests for scopeshift.extraction and scopeshift.ingest."""
from pathlib import Path
from unittest.mock import MagicMock
import json
import pytest

from scopeshift.extraction import Extractor, ExtractionResult, ClaimExtractionSchema
from scopeshift.ingest import IngestionPipeline
from scopeshift.store import EventStore

FX = Path(__file__).parent.parent / "fixtures"


def test_extractor_offline_mode():
    extractor = Extractor(api_key=None)  # No key -> deterministic offline fallback
    result = extractor.extract_from_text("We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.", "client_note")
    assert isinstance(result, ExtractionResult)
    assert result.mode == "fallback"
    assert len(result.claims) == 1
    c = result.claims[0]
    assert c["claim_id"] == "checkout.payment_methods"
    assert c["proposed_scope_change"] is True
    assert "Card" in c["quote"]


def test_extractor_pre_extracted_fixtures():
    extractor = Extractor(api_key=None)
    # BRD text
    brd_res = extractor.extract_from_text("REQ-PAY-01: Checkout shall support UPI payments only. Business rule: UPI is the exclusive payment method for v1.0.", "brd")
    assert brd_res.claims[0]["value"]["methods"] == ["UPI"]
    assert brd_res.claims[0]["value"]["exclusive"] is True

    # Screenshot
    shot_res = extractor.extract_from_image(FX / "checkout.png")
    assert shot_res.claims[0]["value"]["methods"] == ["Card"]
    assert shot_res.claims[0]["region"] is not None


def test_extractor_unknown_input_fallback_fails_closed():
    """Fallback mode must NOT return canned claims for unknown input."""
    extractor = Extractor(api_key=None)
    unknown_text = "Random unrelated specification document that is not a known demo fixture."
    res = extractor.extract_from_text(unknown_text, "brd", force_fallback=True)
    assert res.claims == []
    assert res.mode == "fallback"
    assert res.reason == "offline: no live extractor"

    # Unknown image bytes
    unknown_img = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    img_res = extractor.extract_from_image(unknown_img, force_fallback=True)
    assert img_res.claims == []
    assert img_res.mode == "fallback"
    assert img_res.reason == "offline: no live extractor"

    # Unknown PDF bytes
    unknown_pdf = b"%PDF-1.4 empty mock pdf stream"
    pdf_res = extractor.extract_from_pdf(unknown_pdf, force_fallback=True)
    assert pdf_res.claims == []
    assert pdf_res.mode == "fallback"
    assert pdf_res.reason == "offline: no live extractor"


def test_mock_gemini_schema_passed():
    """Verify response_schema and application/json MIME type passed to Gemini."""
    extractor = Extractor(api_key="mock_key")
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps([
        {
            "claim_id": "checkout.payment_methods",
            "observation": "Checkout supports card payments.",
            "quote": "Pay with Card",
            "proposed_scope_change": False,
            "value": {"methods": ["Card"]},
            "region": [10, 20, 100, 50],
        }
    ])
    mock_client.models.generate_content.return_value = mock_resp
    extractor._client = mock_client

    res = extractor.extract_from_text("Sample input text", "screenshot")
    assert res.mode == "live"
    assert len(res.claims) == 1
    assert mock_client.models.generate_content.called

    call_args = mock_client.models.generate_content.call_args
    config = call_args.kwargs.get("config")
    assert config is not None
    assert config.response_mime_type == "application/json"
    assert config.response_schema == list[ClaimExtractionSchema]


def test_mock_gemini_bad_json():
    """Verify bad JSON from Gemini is logged and returns structured failure reason."""
    extractor = Extractor(api_key="mock_key")
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "{invalid json: [not valid"
    mock_client.models.generate_content.return_value = mock_resp
    extractor._client = mock_client

    res = extractor.extract_from_text("Some text to extract", "brd")
    assert res.claims == []
    assert res.error_type == "JSONDecodeError"
    assert "JSON decode error" in res.reason


def test_mock_gemini_timeout_then_retry():
    """Verify exponential backoff retry on timeout (up to 3 tries)."""
    extractor = Extractor(api_key="mock_key", retry_delay_base=0.01)
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps([
        {
            "claim_id": "checkout.currency",
            "observation": "Currency is INR.",
            "quote": "charged in INR",
            "proposed_scope_change": False,
            "value": {"currency": "INR"},
        }
    ])
    # Fails twice with TimeoutError, succeeds on 3rd attempt
    mock_client.models.generate_content.side_effect = [
        TimeoutError("Attempt 1 timed out"),
        TimeoutError("Attempt 2 timed out"),
        mock_resp,
    ]
    extractor._client = mock_client

    res = extractor.extract_from_text("Prices charged in INR", "brd")
    assert mock_client.models.generate_content.call_count == 3
    assert len(res.claims) == 1
    assert res.claims[0]["claim_id"] == "checkout.currency"

    # Test all 3 failing fails closed
    mock_client.models.generate_content.reset_mock()
    mock_client.models.generate_content.side_effect = [
        TimeoutError("Timeout 1"),
        TimeoutError("Timeout 2"),
        TimeoutError("Timeout 3"),
    ]
    failed_res = extractor.extract_from_text("Unknown text that times out", "brd")
    assert mock_client.models.generate_content.call_count == 3
    assert failed_res.claims == []
    assert failed_res.error_type == "TimeoutError"
    assert "TimeoutError" in failed_res.reason or "timed out" in failed_res.reason.lower()


def test_mock_gemini_hallucinated_claim_id():
    """Verify hallucinated claim_id (outside frozen enum) is rejected."""
    extractor = Extractor(api_key="mock_key")
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps([
        {
            "claim_id": "checkout.bitcoin",  # Hallucinated / outside enum
            "observation": "Accepts crypto.",
            "quote": "Pay with Bitcoin",
            "proposed_scope_change": True,
            "value": {"crypto": "BTC"},
        },
        {
            "claim_id": "checkout.payment_methods",  # Valid
            "observation": "Accepts card.",
            "quote": "Pay with Card",
            "proposed_scope_change": False,
            "value": {"methods": ["Card"]},
        },
    ])
    mock_client.models.generate_content.return_value = mock_resp
    extractor._client = mock_client

    res = extractor.extract_from_text("Text with mixed claims", "screenshot")
    # The valid claim is kept, the hallucinated claim is rejected
    assert len(res.claims) == 1
    assert res.claims[0]["claim_id"] == "checkout.payment_methods"
    assert res.error_type == "ValidationError"
    assert "checkout.bitcoin" in res.reason


def test_ingestion_pipeline_end_to_end():
    pipeline = IngestionPipeline()
    evidence_items = pipeline.ingest_fixtures(FX)
    
    # We expect SRC-01 (brd), SRC-02 (screenshot), SRC-03 (client_note)
    assert len(evidence_items) >= 3
    sids = [e.source_id for e in evidence_items]
    assert "SRC-01" in sids
    assert "SRC-02" in sids
    assert "SRC-03" in sids

    brd_ev = next(e for e in evidence_items if e.source_id == "SRC-01")
    assert brd_ev.quote_verified is True
    assert brd_ev.governing is False

    shot_ev = next(e for e in evidence_items if e.source_id == "SRC-02")
    assert shot_ev.quote_verified is True
    assert shot_ev.governing is False

    note_ev = next(e for e in evidence_items if e.source_id == "SRC-03")
    assert note_ev.quote_verified is True
    assert note_ev.proposed_scope_change is True
    assert note_ev.governing is True


def test_ingestion_into_store():
    store = EventStore(":memory:")
    pipeline = IngestionPipeline()
    evidence_items = pipeline.ingest_fixtures(FX)
    store.seed(evidence_items)

    snap = store.snapshot()
    assert len(snap["sources"]) >= 3
