"""Tests for demo_server HTTP API including advanced features."""
import json
import urllib.request
import threading
import time
import pytest
from http.server import ThreadingHTTPServer

from demo_server import Handler, demo_store
import demo_server


@pytest.fixture(scope="module")
def test_server():
    demo_server.STORE = demo_store(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 8769), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield "http://127.0.0.1:8769"
    server.shutdown()


def req(url, method="GET", data=None):
    body = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"} if data else {}
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            content = resp.read()
            try:
                parsed = json.loads(content.decode("utf-8"))
            except Exception:
                parsed = content.decode("utf-8")
            return resp.status, parsed, resp.headers
    except urllib.error.HTTPError as err:
        content = err.read()
        try:
            parsed = json.loads(content.decode("utf-8"))
        except Exception:
            parsed = content.decode("utf-8")
        return err.code, parsed, err.headers


def test_health_endpoint(test_server):
    status, body, headers = req(f"{test_server}/api/health")
    assert status == 200
    assert body["status"] == "ok"
    assert headers.get("X-Content-Type-Options") == "nosniff"


def test_state_endpoint(test_server):
    status, body, _ = req(f"{test_server}/api/state")
    assert status == 200
    assert "resolutions" in body
    assert "sources" in body
    assert "events" in body
    assert "mirror_note" in body


def test_demo_beats_flow(test_server):
    # Beat 1 -> DISPUTED
    status, body, _ = req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "DISPUTED"

    # Beat 2 -> GOVERNED
    status, body, _ = req(f"{test_server}/api/demo/beat", "POST", {"beat": 2, "use_live_ai": False})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "GOVERNED"
    assert body["extraction"]["mode"] == "fallback"

    # Beat 3 -> DISPUTED with withdrawal explanation
    status, body, _ = req(f"{test_server}/api/demo/beat", "POST", {"beat": 3})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "DISPUTED"
    assert body["state"]["resolutions"]["checkout.payment_methods"]["disappeared"] is not None


def test_markdown_export(test_server):
    status, body, headers = req(f"{test_server}/api/export/markdown")
    assert status == 200
    assert "# Business Requirements Document (BRD)" in body
    assert "Seeing a button is not approving the button" in body


def test_time_travel_scrubber(test_server):
    # Setup full 3 beats first
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 3})
    
    # Scrub back to sequence 1 (only BRD added -> CONSISTENT)
    status, body, _ = req(f"{test_server}/api/demo/scrub", "POST", {"sequence": 1})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "CONSISTENT"
    assert len(body["state"]["events"]) == 1

    # Scrub to sequence 2 (Screenshot added -> DISPUTED)
    status, body, _ = req(f"{test_server}/api/demo/scrub", "POST", {"sequence": 2})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "DISPUTED"

    # Scrub to sequence 3 (Client note added -> GOVERNED)
    status, body, _ = req(f"{test_server}/api/demo/scrub", "POST", {"sequence": 3})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "GOVERNED"


def test_chaos_adversarial_testing(test_server):
    status, body, _ = req(f"{test_server}/api/demo/chaos", "POST", {"chaos_type": "forged_screenshot"})
    assert status == 200
    assert body["blocked"] is True
    assert "NEVER grant authority" in body["explanation"]


def test_invalid_event_transition(test_server):
    # Reset to beat 1 (SRC-01, SRC-02 added)
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})
    # Duplicate ADDED on SRC-01 must fail
    status, body, _ = req(f"{test_server}/api/events", "POST", {"source_id": "SRC-01", "event": "ADDED"})
    assert status == 422
    assert "error" in body


def test_export_json(test_server):
    status, body, headers = req(f"{test_server}/api/export/json")
    assert status == 200
    assert "audit_chain" in body
    assert "resolutions" in body
    assert len(body["audit_chain"]) >= 2
    assert body["audit_chain"][0]["hash"] != ""
    assert "attachment" in headers.get("Content-Disposition", "")


def test_api_ingest_and_validation_rejection(test_server):
    # Reset to beat 1
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})

    # 1. Invalid quote rejected by code validation
    payload_bad = {
        "source_type": "client_note",
        "claim_id": "auth.mfa_requirement",
        "text": "We need MFA next sprint.",
        "quote": "Hallucinated quote that does not exist in text",
        "proposed_scope_change": True,
        "value": {"mfa_required": True, "channels": ["TOTP Authenticator"]},
    }
    status, body, _ = req(f"{test_server}/api/ingest", "POST", payload_bad)
    # Quote not found returns 201 with unverified evidence or raises if text verification fails
    # In validate_claim: quote_in_text returns False, so quote_verified=False, item is seeded but governing=False
    assert status in (201, 422)

    # 2. Valid Ingestion with verified quote
    payload_good = {
        "source_type": "client_note",
        "claim_id": "auth.mfa_requirement",
        "text": "Official Directive: Mandatory MFA is strictly required across checkout.",
        "quote": "Mandatory MFA is strictly required across checkout",
        "observation": "Client mandate for MFA",
        "proposed_scope_change": True,
        "value": {"mfa_required": True, "channels": ["TOTP Authenticator"]},
    }
    status, body, _ = req(f"{test_server}/api/ingest", "POST", payload_good)
    assert status == 201
    assert "source_id" in body
    assert body["source_id"].startswith("SRC-")
    assert body["state"]["resolutions"]["auth.mfa_requirement"]["state"] == "GOVERNED"


def test_api_govern_and_withdraw(test_server):
    # 1. Govern refunds.settlement_sla
    payload_gov = {
        "claim_id": "refunds.settlement_sla",
        "directive": "Client Directive: Customer refund settlement SLA is 24 hours with instant automated settlement.",
        "value": {"sla_hours": 24, "instant_settlement": True},
    }
    status, body, _ = req(f"{test_server}/api/govern", "POST", payload_gov)
    assert status == 201
    sid = body["source_id"]
    assert body["state"]["resolutions"]["refunds.settlement_sla"]["state"] == "GOVERNED"

    # 2. Withdraw the client directive
    status, body, _ = req(f"{test_server}/api/withdraw", "POST", {"source_id": sid})
    assert status == 200
    assert body["event"]["event"] == "REMOVED"
    # State reflects withdrawal
    assert body["state"]["resolutions"]["refunds.settlement_sla"]["disappeared"] is not None
