"""Tests for scopeshift.extraction and scopeshift.ingest."""
from pathlib import Path
import pytest

from scopeshift.extraction import Extractor, ExtractionResult
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
