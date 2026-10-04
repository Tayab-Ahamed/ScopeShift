"""Tests for the live SSE evidence feed (Stream C): GET /api/feed."""
import json
import threading
import time
import urllib.request
import urllib.error
import pytest
from http.server import ThreadingHTTPServer

from demo_server import Handler, demo_store
import demo_server
from scopeshift.feed_scenario import ARRIVALS
from scopeshift.validation import quote_in_text, validate_claim


@pytest.fixture(scope="module")
def test_server():
    demo_server.STORE = demo_store(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 8770), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield "http://127.0.0.1:8770"
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


def read_sse(url, max_events=12, timeout=60):
    """Read SSE events from url until max_events or the server closes the stream.

    Returns (content_type, [(event_name, payload), ...]). Closing the response
    simulates a client disconnect.
    """
    r = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    events = []
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        ev_name = None
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("event:"):
                ev_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and ev_name:
                events.append((ev_name, json.loads(line.split(":", 1)[1].strip())))
                ev_name = None
                if len(events) >= max_events:
                    break
    return ctype, events


def test_feed_returns_event_stream(test_server):
    ctype, events = read_sse(f"{test_server}/api/feed", max_events=2)
    assert "text/event-stream" in ctype
    assert events[0][0] == "feed-start"
    start = events[0][1]
    assert start["simulated"] is True
    assert start["arrivals"] == len(ARRIVALS) == 8
    assert start["loop"] is False
    assert events[1][0] == "evidence-arrival"


def test_feed_first_arrival_uses_real_pipeline(test_server):
    # Reset-aware beat 1: clean seed, 2 events in the log.
    status, body, _ = req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})
    assert status == 200
    assert len(body["state"]["events"]) == 2

    _, events = read_sse(f"{test_server}/api/feed", max_events=2)
    name, data = events[1]
    assert name == "evidence-arrival"

    # The arrival went through the REAL pipeline: new source + appended event.
    assert data["simulated"] is True
    assert data["ingest_error"] is None
    assert data["source_id"].startswith("SRC-")
    assert data["quote_verified"] is True
    ev = data["event"]
    assert ev["event"] == "ADDED"
    assert ev["event_sequence"] == 3  # appended after the 2 seed events

    # State was recomputed live: full snapshot travels with the payload.
    assert "state" in data and "claim_states" in data
    assert data["claim_states"]["checkout.payment_methods"] == "DISPUTED"
    assert len(data["state"]["events"]) == 3
    assert data["state"]["resolutions"]["checkout.payment_methods"]["state"] == "DISPUTED"


def test_feed_full_pass_transitions_and_feed_end(test_server):
    req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})
    _, events = read_sse(f"{test_server}/api/feed", max_events=12)

    arrivals = [d for n, d in events if n == "evidence-arrival"]
    assert len(arrivals) == 8, "the full scripted scenario must stream all 8 arrivals"
    assert events[-1][0] == "feed-end"
    assert events[-1][1]["will_repeat"] is False

    # No arrival was rejected by the validation boundary.
    assert all(d["ingest_error"] is None for d in arrivals)
    assert all(d["source_id"].startswith("SRC-") for d in arrivals)

    # The directive arrival genuinely governs (verified quote + scope flag).
    directive = next(d for d in arrivals if d["kind"] == "directive"
                     and d["claim_id"] == "checkout.payment_methods")
    assert directive["governing"] is True
    assert directive["quote_verified"] is True

    # Real state transitions happened through the resolver, not canned text.
    gov = [t for d in arrivals for t in d["transitions"]
           if t["claim_id"] == "checkout.payment_methods" and t["from"] == "DISPUTED" and t["to"] == "GOVERNED"]
    assert gov, "the client directive must flip payment_methods DISPUTED -> GOVERNED"
    back = [t for d in arrivals for t in d["transitions"]
            if t["claim_id"] == "checkout.payment_methods" and t["from"] == "GOVERNED" and t["to"] == "DISPUTED"]
    assert back, "the withdrawal must flip payment_methods back GOVERNED -> DISPUTED"

    # The withdrawal arrival ingested its own evidence AND emitted a real REMOVED.
    withdrawal = next(d for d in arrivals if d["kind"] == "withdrawal")
    assert withdrawal["withdraws"] is not None
    assert withdrawal["withdraws"]["event"] == "REMOVED"
    assert withdrawal["withdraws"]["source_id"] == directive["source_id"]

    # Final recomputed state matches the scenario arc.
    final = events[-1][1]["state"]["resolutions"]
    assert final["checkout.payment_methods"]["state"] == "DISPUTED"
    assert final["checkout.payment_methods"]["disappeared"] is not None  # reason retained
    assert final["auth.mfa_requirement"]["state"] == "GOVERNED"
    assert final["refunds.settlement_sla"]["state"] == "GOVERNED"


def test_feed_loop_param_accepted(test_server):
    ctype, events = read_sse(f"{test_server}/api/feed?loop=1", max_events=3)
    assert "text/event-stream" in ctype
    assert events[0][0] == "feed-start"
    assert events[0][1]["loop"] is True
    assert events[1][0] == "evidence-arrival"
    assert events[2][0] == "evidence-arrival"
    # Leaving the `with` block disconnects mid-loop; the server must survive it.


def test_feed_disconnect_does_not_corrupt_store(test_server):
    # Abrupt disconnect mid-loop (booth browser closed).
    read_sse(f"{test_server}/api/feed?loop=1", max_events=2)
    time.sleep(3.5)  # let the server thread hit the dead socket and exit cleanly

    # The store is still fully consistent and servable.
    status, body, _ = req(f"{test_server}/api/state")
    assert status == 200
    assert "resolutions" in body and "events" in body

    # Beats still work afterwards: reset-aware beat 1, then beat 2 governs.
    status, body, _ = req(f"{test_server}/api/demo/beat", "POST", {"beat": 1})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "DISPUTED"
    status, body, _ = req(f"{test_server}/api/demo/beat", "POST", {"beat": 2})
    assert status == 200
    assert body["state"]["resolutions"]["checkout.payment_methods"]["state"] == "GOVERNED"


def test_feed_scenario_is_honest_and_valid():
    """The scripted scenario must survive the REAL validation boundary itself.

    Every arrival's quote verifies against its text and its value passes the
    claim spec — the feed can never claim a state the pipeline wouldn't produce.
    """
    assert len(ARRIVALS) >= 8
    required = {"delay_seconds", "kind", "source_type", "claim_id", "text", "quote",
                "observation", "proposed_scope_change", "value"}
    aliases = set()
    for a in ARRIVALS:
        assert required <= set(a), f"arrival missing keys: {required - set(a)}"
        assert a["kind"] in {"slack", "email", "screenshot", "directive", "withdrawal"}
        assert a["source_type"] in {"brd", "screenshot", "client_note"}
        if a.get("alias"):
            aliases.add(a["alias"])
        v = validate_claim(
            {"claim_id": a["claim_id"], "quote": a["quote"], "observation": a["observation"],
             "proposed_scope_change": a["proposed_scope_change"], "value": a["value"],
             "region": a.get("region")},
            a["source_type"],
            text=a.get("text", ""),
            image_size=(900, 620) if a["source_type"] == "screenshot" else None,
        )
        assert v["quote_verified"] is True, f"{a['kind']} arrival quote must verify"
        if a["kind"] != "screenshot":
            assert quote_in_text(a["quote"], a["text"])
    for a in ARRIVALS:
        if a.get("withdraws_alias"):
            assert a["withdraws_alias"] in aliases, "withdrawal must reference a real earlier alias"
