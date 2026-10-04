"""Tests for FR-8/FR-18 fail-closed citation enforcement in the serve path.

EventStore.snapshot() must raise ValidationError (via validate_citations) when a
served BRD citation does not resolve to active evidence, and the HTTP layer must
convert that into a structured 500 CITATION_INTEGRITY_VIOLATION — never a served
BRD projection and never a dropped connection.
"""
import json
import threading
import time
import urllib.request
import urllib.error
import pytest
from http.server import ThreadingHTTPServer

from demo_server import Handler, demo_store
import demo_server
import scopeshift.store
from scopeshift.store import EventStore
from scopeshift.validation import ValidationError


@pytest.fixture(scope="module")
def test_server():
    demo_server.STORE = demo_store(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 8772), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield "http://127.0.0.1:8772"
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


def _raise_violation(resolutions, active_evidence):
    raise ValidationError("synthetic citation violation for fail-closed test")


def test_snapshot_reports_citation_integrity_ok():
    store = demo_store(":memory:")
    snap = store.snapshot()
    assert snap["citation_integrity"] == "ok"
    assert snap["citation_warnings"] == []
    store.close()


def test_snapshot_fail_closed_on_citation_violation(monkeypatch):
    """snapshot() must propagate validate_citations failures, not swallow them."""
    monkeypatch.setattr(scopeshift.store, "validate_citations", _raise_violation)
    store = demo_store(":memory:")
    try:
        with pytest.raises(ValidationError, match="synthetic citation violation"):
            store.snapshot()
    finally:
        store.close()


def test_state_endpoint_fail_closed(test_server, monkeypatch):
    """GET /api/state must return a structured 500, never a BRD with bad citations."""
    monkeypatch.setattr(scopeshift.store, "validate_citations", _raise_violation)
    status, body, _ = req(f"{test_server}/api/state")
    assert status == 500
    assert body["error"]["code"] == "CITATION_INTEGRITY_VIOLATION"
    assert "synthetic citation violation" in body["error"]["message"]


def test_scrub_endpoint_fail_closed(test_server, monkeypatch):
    """POST /api/demo/scrub must fail closed the same way."""
    monkeypatch.setattr(scopeshift.store, "validate_citations", _raise_violation)
    # scrub calls validate_citations directly in demo_server, patch that binding too
    monkeypatch.setattr(demo_server, "validate_citations", _raise_violation)
    status, body, _ = req(f"{test_server}/api/demo/scrub", method="POST",
                          data={"sequence": 2})
    assert status == 500
    assert body["error"]["code"] == "CITATION_INTEGRITY_VIOLATION"


def test_state_endpoint_healthy_after_patch_removed(test_server):
    """Sanity: with the real validator restored, /api/state is 200 and clean."""
    status, body, _ = req(f"{test_server}/api/state")
    assert status == 200
    assert body["citation_integrity"] == "ok"
