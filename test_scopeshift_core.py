import sqlite3

from event_store import EventStore
from scopeshift_core import Evidence, Event, replay


def fixtures():
    return [
        Evidence("SRC-01", "brd", "checkout.payment_methods", {"exclusive": True, "methods": ["UPI"]}, "Checkout accepts UPI only.", quote_verified=True, event_sequence=1, active=False),
        Evidence("SRC-02", "screenshot", "checkout.payment_methods", {"methods": ["Card"]}, "Card button", quote_verified=True, event_sequence=2, active=False),
        Evidence("SRC-03", "client_note", "checkout.payment_methods", "Card payments; UPI moves to Phase 2", "Card is in scope. UPI moves to Phase 2.", proposed_scope_change=True, quote_verified=True, event_sequence=3, active=False),
    ]


def test_three_beats_replay_to_governed_then_disputed():
    evidence = fixtures()
    beat1 = replay(evidence[:2], [Event(1, "SRC-01", "ADDED"), Event(2, "SRC-02", "ADDED")])
    beat2 = replay(evidence, [Event(1, "SRC-01", "ADDED"), Event(2, "SRC-02", "ADDED"), Event(3, "SRC-03", "ADDED")])
    beat3 = replay(evidence, [Event(1, "SRC-01", "ADDED"), Event(2, "SRC-02", "ADDED"), Event(3, "SRC-03", "ADDED"), Event(4, "SRC-03", "REMOVED")])
    assert beat1["state"] == "DISPUTED"
    assert beat2["state"] == "GOVERNED"
    assert beat3["state"] == "DISPUTED"


def test_unverified_client_note_cannot_govern():
    evidence = fixtures()
    evidence[-1] = Evidence(**{**evidence[-1].__dict__, "quote_verified": False})
    result = replay(evidence, [Event(1, "SRC-01", "ADDED"), Event(2, "SRC-02", "ADDED"), Event(3, "SRC-03", "ADDED")])
    assert result["state"] == "DISPUTED"


def test_invalid_removal_is_rejected():
    try:
        replay(fixtures()[:2], [Event(1, "SRC-99", "REMOVED")])
    except ValueError:
        return
    raise AssertionError("expected invalid removal to be rejected")


def test_sqlite_store_is_append_only_and_replays():
    store = EventStore()
    store.seed(fixtures())
    store.add_event("SRC-01", "ADDED")
    store.add_event("SRC-02", "ADDED")
    assert store.snapshot()["state"]["state"] == "DISPUTED"
    store.add_event("SRC-03", "ADDED")
    assert store.snapshot()["state"]["state"] == "GOVERNED"
    try:
        store.db.execute("DELETE FROM event_log")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("event log must reject deletes")
