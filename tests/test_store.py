"""Tests for scopeshift.store (SQLite append-only event store)."""
import sqlite3
import pytest
from pathlib import Path

from scopeshift.models import Evidence, Event
from scopeshift.store import EventStore

PAY = "checkout.payment_methods"


@pytest.fixture
def sample_evidence():
    return [
        Evidence("SRC-01", "brd", PAY, {"methods": ["UPI"], "exclusive": True}, "UPI only",
                 quote_verified=True, event_sequence=1),
        Evidence("SRC-02", "screenshot", PAY, {"methods": ["Card"]}, "Card visible",
                 quote_verified=True, event_sequence=2),
        Evidence("SRC-03", "client_note", PAY, {"methods": ["Card"], "deferred": ["UPI"]},
                 "Card in scope. UPI moves to Phase 2.", proposed_scope_change=True,
                 quote_verified=True, event_sequence=3),
    ]


def test_store_initialization_and_seeding(sample_evidence):
    store = EventStore(":memory:")
    store.seed(sample_evidence)
    snap = store.snapshot()
    assert len(snap["sources"]) == 3
    assert len(snap["events"]) == 0
    assert snap["resolutions"][PAY]["state"] == "UNKNOWN"


def test_store_append_events_and_snapshot(sample_evidence):
    store = EventStore(":memory:")
    store.seed(sample_evidence)
    
    # Beat 1
    ev1 = store.add_event("SRC-01", "ADDED")
    ev2 = store.add_event("SRC-02", "ADDED")
    assert ev1.event_sequence == 1
    assert ev2.event_sequence == 2
    
    snap1 = store.snapshot()
    assert snap1["resolutions"][PAY]["state"] == "DISPUTED"
    assert len(snap1["events"]) == 2

    # Beat 2
    store.add_event("SRC-03", "ADDED")
    snap2 = store.snapshot()
    assert snap2["resolutions"][PAY]["state"] == "GOVERNED"
    assert snap2["resolutions"][PAY]["governing_source"] == "SRC-03"

    # Beat 3
    store.add_event("SRC-03", "REMOVED")
    snap3 = store.snapshot()
    assert snap3["resolutions"][PAY]["state"] == "DISPUTED"
    assert snap3["resolutions"][PAY]["disappeared"] is not None


def test_store_prevents_mutation_and_deletion(sample_evidence):
    store = EventStore(":memory:")
    store.seed(sample_evidence)
    store.add_event("SRC-01", "ADDED")

    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("UPDATE evidence SET quote = 'hacked' WHERE source_id = 'SRC-01'")

    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("DELETE FROM evidence WHERE source_id = 'SRC-01'")

    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("UPDATE event_log SET event = 'REMOVED' WHERE event_sequence = 1")

    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("DELETE FROM event_log WHERE event_sequence = 1")


def test_store_rejects_invalid_transitions_without_corrupting_log(sample_evidence):
    store = EventStore(":memory:")
    store.seed(sample_evidence)
    store.add_event("SRC-01", "ADDED")

    with pytest.raises(ValueError):
        store.add_event("SRC-01", "ADDED")  # duplicate ADDED

    with pytest.raises(ValueError):
        store.add_event("SRC-03", "REMOVED")  # remove before add

    with pytest.raises(ValueError):
        store.add_event("SRC-99", "ADDED")  # unknown source

    # Ensure only 1 event exists
    events = store.db.execute("SELECT COUNT(*) FROM event_log").fetchone()[0]
    assert events == 1


def test_store_persists_to_file(tmp_path, sample_evidence):
    db_file = tmp_path / "test.db"
    store1 = EventStore(db_file)
    store1.seed(sample_evidence)
    store1.add_event("SRC-01", "ADDED")
    store1.add_event("SRC-02", "ADDED")
    store1.close()

    store2 = EventStore(db_file)
    snap = store2.snapshot()
    assert snap["resolutions"][PAY]["state"] == "DISPUTED"
    assert len(snap["events"]) == 2
    store2.close()
