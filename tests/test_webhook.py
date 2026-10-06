"""Tests for Task C: Real-time fragmented intake via POST /api/webhook/inbound.
Covers:
- Valid signed message from allowlisted sender (governs, recorded in hash chain)
- Missing signature header (401)
- Bad HMAC signature (401)
- Stale timestamp > 5 minutes drift (401)
- Unknown sender not in approver allowlist (accepted as observation only, does not govern)
- Replay of the same message_id (409 Conflict)
- Real-time broadcast to SSE subscribers
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

import pytest

import demo_server
from demo_server import (
    Handler,
    create_demo_store,
    reset_processed_webhooks,
    subscribe_sse,
    unsubscribe_sse,
)
from scripts.send_webhook import send_webhook

WEBHOOK_SECRET = "test-webhook-secret-xyz-987"


@pytest.fixture(scope="module")
def webhook_server(monkeypatch_module=None):
    os.environ["SCOPESHIFT_WEBHOOK_SECRET"] = WEBHOOK_SECRET
    demo_server.STORE = create_demo_store(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 8790), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    yield "http://127.0.0.1:8790"
    server.shutdown()
    os.environ.pop("SCOPESHIFT_WEBHOOK_SECRET", None)


@pytest.fixture(autouse=True)
def clean_webhook_state():
    reset_processed_webhooks()
    yield
    reset_processed_webhooks()


def test_webhook_valid_allowlisted_sender(webhook_server):
    """Valid signed webhook from allowlisted sender Priya Nair is accepted and governs."""
    msg_id = f"test-valid-{time.time()}"
    status, body = send_webhook(
        secret=WEBHOOK_SECRET,
        url=f"{webhook_server}/api/webhook/inbound",
        sender="Priya Nair",
        channel="slack",
        text="We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.",
        message_id=msg_id,
    )
    assert status == 200
    assert body["ok"] is True
    assert body["message_id"] == msg_id
    assert body["claims_processed"] >= 1
    
    # Check receipt
    rc = body["receipts"][0]
    assert rc["claim_id"] == "checkout.payment_methods"
    assert rc["status"] == "verified"
    assert rc["governing"] is True
    assert rc["sender"] == "Priya Nair"

    # Check store and hash chain
    snap = body["state"]
    # Evidence item must be stored with sender and channel
    src_item = next(s for s in snap["sources"] if s["id"] == rc["source_id"])
    assert src_item["quote_verified"] is True
    assert src_item["proposed_scope_change"] is True

    # Check event log and audit chain in store
    events = demo_server.STORE._load_events()
    ev = next(e for e in events if e.source_id == rc["source_id"])
    assert ev.sender == "Priya Nair"
    assert ev.channel == "slack"
    
    chain = demo_server.STORE.audit_chain()
    entry = next(c for c in chain if c["source_id"] == rc["source_id"])
    assert entry["hash"] is not None and len(entry["hash"]) == 64
    assert entry["sender"] == "Priya Nair"
    assert entry["channel"] == "slack"


def test_webhook_missing_signature(webhook_server):
    """Webhook without signature header must be rejected with 401."""
    req_body = json.dumps({
        "sender": "Priya Nair",
        "channel": "slack",
        "text": "Scope change note",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "message_id": "no-sig-msg",
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{webhook_server}/api/webhook/inbound",
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req):
            pytest.fail("Expected 401 HTTPError")
    except urllib.error.HTTPError as err:
        assert err.code == 401
        data = json.loads(err.read().decode("utf-8"))
        assert data["error"]["code"] == "UNAUTHORIZED"


def test_webhook_bad_signature(webhook_server):
    """Webhook with forged/invalid HMAC signature must be rejected with 401."""
    status, body = send_webhook(
        secret=WEBHOOK_SECRET,
        url=f"{webhook_server}/api/webhook/inbound",
        sender="Priya Nair",
        channel="slack",
        text="Scope change note",
        message_id="bad-sig-msg",
        bad_sig=True,
    )
    assert status == 401
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_webhook_stale_timestamp(webhook_server):
    """Webhook with timestamp older than 5 minutes must be rejected with 401."""
    status, body = send_webhook(
        secret=WEBHOOK_SECRET,
        url=f"{webhook_server}/api/webhook/inbound",
        sender="Priya Nair",
        channel="slack",
        text="Scope change note",
        message_id="stale-msg",
        stale=True,
    )
    assert status == 401
    assert body["error"]["code"] == "STALE_TIMESTAMP"


def test_webhook_unknown_sender_not_governing(webhook_server):
    """Webhook from unknown/unauthorized sender is recorded as observation but CANNOT govern."""
    msg_id = f"test-unauth-{time.time()}"
    status, body = send_webhook(
        secret=WEBHOOK_SECRET,
        url=f"{webhook_server}/api/webhook/inbound",
        sender="Mallory Attacker",
        channel="telegram",
        text="We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.",
        message_id=msg_id,
    )
    assert status == 200
    assert body["ok"] is True
    assert body["claims_processed"] >= 1

    rc = body["receipts"][0]
    assert rc["governing"] is False
    assert rc["observation"] == "sender not authorised"

    # In store, evidence is marked as not governing
    snap = body["state"]
    src_item = next(s for s in snap["sources"] if s["id"] == rc["source_id"])
    assert src_item["proposed_scope_change"] is False


def test_webhook_replay_prevention(webhook_server):
    """Sending the same message_id twice must reject the replay with 409 Conflict."""
    msg_id = f"test-replay-{time.time()}"
    status1, body1 = send_webhook(
        secret=WEBHOOK_SECRET,
        url=f"{webhook_server}/api/webhook/inbound",
        sender="Priya Nair",
        channel="slack",
        text="We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.",
        message_id=msg_id,
    )
    assert status1 == 200
    assert body1["ok"] is True

    # Immediate replay with the same message_id
    status2, body2 = send_webhook(
        secret=WEBHOOK_SECRET,
        url=f"{webhook_server}/api/webhook/inbound",
        sender="Priya Nair",
        channel="slack",
        text="We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.",
        message_id=msg_id,
    )
    assert status2 == 409
    assert body2["error"]["code"] == "DUPLICATE_MESSAGE"


def test_webhook_pushes_to_sse_subscribers(webhook_server):
    """Accepted webhook message must broadcast an event to active SSE subscriber queues."""
    q = subscribe_sse()
    try:
        msg_id = f"test-sse-broadcast-{time.time()}"
        status, body = send_webhook(
            secret=WEBHOOK_SECRET,
            url=f"{webhook_server}/api/webhook/inbound",
            sender="Alex Mercer",
            channel="email",
            text="We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.",
            message_id=msg_id,
        )
        assert status == 200

        # Check queue
        ev_name, ev_payload = q.get(timeout=2.0)
        assert ev_name == "webhook-arrival"
        assert ev_payload["sender"] == "Alex Mercer"
        assert ev_payload["channel"] == "email"
        assert ev_payload["claim_id"] == "checkout.payment_methods"
    finally:
        unsubscribe_sse(q)
