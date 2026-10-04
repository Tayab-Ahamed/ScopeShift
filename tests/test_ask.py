"""Tests for POST /api/ask (deterministic evidence Q&A) and GET /api/audit/chain."""
import hashlib
import json
import threading
import time
import urllib.request
import urllib.error
import pytest
from http.server import ThreadingHTTPServer

from demo_server import Handler, demo_store
import demo_server
from scopeshift.ask import answer_question


@pytest.fixture(scope="module")
def test_server():
    demo_server.STORE = demo_store(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 8771), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield "http://127.0.0.1:8771"
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


def ask(server, question):
    return req(f"{server}/api/ask", "POST", {"question": question})


def valid_citations(server, body):
    """Every citation must reference a real source record with the exact quote."""
    _, state, _ = req(f"{server}/api/state")
    by_id = {s["id"]: s for s in state["sources"]}
    assert body["citations"], "answer must cite real evidence"
    for c in body["citations"]:
        assert c["source_id"] in by_id, f"citation {c['source_id']} is not a real source"
        assert c["quote"] == by_id[c["source_id"]]["quote"], "citation quote must match the evidence record"


def test_ask_why_disputed(test_server):
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})  # -> DISPUTED
    status, body, _ = ask(test_server, "Why is the payment claim disputed?")
    assert status == 200
    assert body["mode"] == "deterministic"
    assert "DISPUTED" in body["answer"]
    valid_citations(test_server, body)


def test_ask_what_governs_after_beat2(test_server):
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 2})  # -> GOVERNED
    status, body, _ = ask(test_server, "What governs the payment methods claim?")
    assert status == 200
    assert "SRC-03" in body["answer"]
    assert "GOVERNED" in body["answer"] or "govern" in body["answer"].lower()
    valid_citations(test_server, body)


def test_ask_disappeared_after_beat3(test_server):
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 3})  # withdraw SRC-03
    status, body, _ = ask(test_server, "Why did the payment requirement disappear?")
    assert status == 200
    assert "disappeared" in body["answer"].lower()
    assert "SRC-03" in body["answer"]
    valid_citations(test_server, body)


def test_ask_what_evidence(test_server):
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})
    status, body, _ = ask(test_server, "What evidence do we have?")
    assert status == 200
    assert "SRC-01" in body["answer"] and "SRC-02" in body["answer"]
    valid_citations(test_server, body)


def test_ask_list_claims(test_server):
    status, body, _ = ask(test_server, "List all claims")
    assert status == 200
    for cid in ("checkout.payment_methods", "checkout.currency",
                "auth.mfa_requirement", "refunds.settlement_sla"):
        assert cid in body["answer"]
    valid_citations(test_server, body)


def test_ask_summarize(test_server):
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})
    status, body, _ = ask(test_server, "Summarize the current state")
    assert status == 200
    assert "DISPUTED" in body["answer"]
    valid_citations(test_server, body)


def test_ask_unknown_question_falls_back_honestly(test_server):
    status, body, _ = ask(test_server, "What is the capital of France?")
    assert status == 200
    assert "only answer from the current evidence snapshot" in body["answer"]
    assert body["citations"] == []
    assert body["mode"] == "deterministic"


def test_ask_empty_question_rejected(test_server):
    for bad in ({}, {"question": ""}, {"question": "   "}, {"question": 42}):
        status, body, _ = req(f"{test_server}/api/ask", "POST", bad)
        assert status == 422
        assert body["error"]["code"] == "VALIDATION_ERROR"


def test_ask_engine_unit_level():
    # Deterministic engine: same snapshot + question -> same answer; facts only.
    demo_server.STORE = demo_store(":memory:")
    snap = demo_server.STORE.snapshot()
    a1 = answer_question(snap, "Why is the payment claim disputed?")
    a2 = answer_question(snap, "Why is the payment claim disputed?")
    assert a1 == a2
    with pytest.raises(ValueError):
        answer_question(snap, "  ")


def test_audit_chain_inputs_verify_genuinely(test_server):
    # The chain endpoint must expose raw inputs so a client can recompute every
    # block: verify hash + prev_hash linkage independently in Python.
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 3})
    status, body, _ = req(f"{test_server}/api/audit/chain")
    assert status == 200
    assert body["algorithm"] == "SHA-256"
    blocks = body["blocks"]
    assert len(blocks) >= 4
    prev = body["genesis_prev_hash"]
    assert prev == "0" * 64
    for b in blocks:
        assert b["prev_hash"] == prev, "prev_hash linkage broken"
        recomputed = hashlib.sha256(b["hash_input"].encode("utf-8")).hexdigest()
        assert recomputed == b["hash"], f"block #{b['sequence']} hash does not match its input"
        assert b["hash_input"] == f"{b['prev_hash']}:{b['sequence']}:{b['source_id']}:{b['event']}"
        prev = b["hash"]


def test_snapshot_sources_carry_region(test_server):
    # Artifact modal region overlay needs the evidence region in the snapshot.
    status, body, _ = req(f"{test_server}/api/state")
    assert status == 200
    shot = next(s for s in body["sources"] if s["id"] == "SRC-02")
    assert shot["region"] == [460, 285, 370, 80]
