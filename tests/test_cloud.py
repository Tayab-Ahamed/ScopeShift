"""Tests for Tier 1 GCP integrations (scopeshift/cloud.py + demo_server wiring).

All tests run with NO GCP SDKs, NO credentials, NO network: adapters must
degrade to honest no-ops, dual-write must never raise, and the UI-facing
status endpoint must report connected=false everywhere.
"""
import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import demo_server
from demo_server import Handler, artifact_url, demo_store
from scopeshift.cloud import (
    BQ_DATASET_ENV,
    GCS_BUCKET_ENV,
    GCP_LOCATION_ENV,
    GCP_PROJECT_ENV,
    BigQueryLog,
    GCSOriginals,
    VertexExtractor,
    cloud_status,
)


@pytest.fixture(autouse=True)
def _no_gcp_env(monkeypatch):
    for var in (BQ_DATASET_ENV, GCS_BUCKET_ENV, GCP_PROJECT_ENV, GCP_LOCATION_ENV,
                "GOOGLE_APPLICATION_CREDENTIALS", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


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
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))


# --- Adapter fallback behaviour (no SDKs / no creds / no env) -----------------

def test_bigquery_disconnected_honest():
    bq = BigQueryLog()
    st = bq.status()
    assert st["connected"] is False
    assert st["reason"]  # honest reason, not a bare false
    assert "sdk not installed" in st["reason"] or "unset" in st["reason"] or "credentials" in st["reason"]


def test_bigquery_append_noop_never_raises():
    bq = BigQueryLog()
    fake = {"event_sequence": 1, "source_id": "SRC-01", "event": "ADDED"}
    assert bq.append(fake) is False  # no-op, no raise


def test_gcs_disconnected_honest():
    gcs = GCSOriginals()
    st = gcs.status()
    assert st["connected"] is False
    assert st["reason"]
    assert gcs.upload("x.png", b"data") is False
    assert gcs.signed_url("x.png") is None


def test_vertex_disconnected_honest():
    vx = VertexExtractor()
    st = vx.status()
    assert st["connected"] is False
    assert st["reason"]
    assert vx.extract_claims("text", "brd", "prompt") is None


def test_cloud_status_snapshot():
    snap = cloud_status()
    for key in ("bigquery", "gcs", "vertex"):
        assert snap[key]["connected"] is False
        assert isinstance(snap[key]["reason"], str) and snap[key]["reason"]


def test_reason_names_missing_env(monkeypatch):
    # With env vars set but no SDK/creds, the reason must still be honest.
    monkeypatch.setenv(BQ_DATASET_ENV, "demo_ds")
    monkeypatch.setenv(GCP_PROJECT_ENV, "demo-proj")
    monkeypatch.setenv(GCP_LOCATION_ENV, "us-central1")
    assert BigQueryLog().status()["connected"] is False
    assert VertexExtractor().status()["connected"] is False


# --- Connected path via monkeypatched fake clients (no real creds) -----------

def test_bigquery_append_calls_fake_client(monkeypatch):
    bq = BigQueryLog()
    calls = []

    class FakeClient:
        def insert_rows_json(self, table, rows):
            calls.append((table, rows))
            return []

    monkeypatch.setattr(bq, "_client", FakeClient())
    monkeypatch.setattr(bq, "_connected", True)
    monkeypatch.setattr(bq, "dataset_id", "ds")
    monkeypatch.setattr(bq, "table_id", "scopeshift_events")

    fake = {"event_sequence": 7, "source_id": "SRC-02", "event": "REMOVED"}
    assert bq.append(fake) is True
    assert len(calls) == 1
    table, rows = calls[0]
    assert table == "ds.scopeshift_events"
    row = rows[0]
    assert row["event_sequence"] == 7
    assert row["source_id"] == "SRC-02"
    assert row["event"] == "REMOVED"
    assert json.loads(row["payload"]) == {"source_id": "SRC-02", "event": "REMOVED"}
    assert "inserted_at" in row


def test_bigquery_append_insert_errors_return_false(monkeypatch):
    bq = BigQueryLog()

    class FakeClient:
        def insert_rows_json(self, table, rows):
            return [{"index": 0, "errors": ["boom"]}]

    monkeypatch.setattr(bq, "_client", FakeClient())
    monkeypatch.setattr(bq, "_connected", True)
    assert bq.append({"event_sequence": 1, "source_id": "S", "event": "ADDED"}) is False


def test_gcs_upload_and_signed_url_fake_client(monkeypatch):
    gcs = GCSOriginals()
    uploaded = {}

    class FakeBlob:
        def __init__(self, name):
            self.name = name

        def upload_from_string(self, data, content_type=None):
            uploaded[self.name] = data

        def generate_signed_url(self, expiration=None):
            return f"https://gcs.example/{self.name}?sig=fake"

    class FakeBucket:
        def blob(self, name):
            return FakeBlob(name)

    monkeypatch.setattr(gcs, "_bucket", FakeBucket())
    monkeypatch.setattr(gcs, "_connected", True)
    assert gcs.upload("checkout.png", b"pngbytes") is True
    assert uploaded["checkout.png"] == b"pngbytes"
    assert gcs.signed_url("checkout.png") == "https://gcs.example/checkout.png?sig=fake"


# --- demo_server wiring -------------------------------------------------------

def test_dual_write_noop_still_persists_event(monkeypatch):
    store = demo_store(":memory:")
    monkeypatch.setattr(demo_server, "STORE", store)
    monkeypatch.setattr(demo_server, "BQ_LOG", BigQueryLog())  # disconnected no-op
    ev = demo_server._store_event(store, "SRC-01", "REMOVED")
    assert ev.event == "REMOVED"
    seqs = [e["event_sequence"] for e in store.snapshot()["events"]]
    assert ev.event_sequence in seqs


def test_dual_write_invokes_bigquery_append(monkeypatch):
    store = demo_store(":memory:")
    monkeypatch.setattr(demo_server, "STORE", store)
    seen = []

    class FakeBQ:
        def append(self, event):
            seen.append(event)
            return True

    monkeypatch.setattr(demo_server, "BQ_LOG", FakeBQ())
    ev = demo_server._store_event(store, "SRC-02", "REMOVED")
    assert len(seen) == 1
    assert seen[0].event_sequence == ev.event_sequence


def test_dual_write_failure_never_breaks_request(monkeypatch):
    store = demo_store(":memory:")
    monkeypatch.setattr(demo_server, "STORE", store)

    class RaisingBQ:
        def append(self, event):
            raise RuntimeError("network down")

    monkeypatch.setattr(demo_server, "BQ_LOG", RaisingBQ())
    ev = demo_server._store_event(store, "SRC-01", "REMOVED")  # must not raise
    assert ev.event == "REMOVED"


def test_api_cloud_status_all_disconnected(test_server):
    status, body = req(f"{test_server}/api/cloud/status")
    assert status == 200
    for key in ("bigquery", "gcs", "vertex"):
        assert body[key]["connected"] is False
        assert body[key]["reason"]
    assert body["extraction"]["mode"] == "deterministic-fallback"


def test_artifact_url_local_paths(test_server):
    # GCS disconnected -> local /fixtures paths, honest "via".
    assert artifact_url("SRC-02") == {"url": "/fixtures/checkout.png", "via": "local"}
    assert artifact_url("SRC-01") == {"url": "/fixtures/brd.pdf", "via": "local"}
    assert artifact_url("SRC-03") == {"url": "/fixtures/client_note.txt", "via": "local"}
    assert artifact_url("SRC-99") is None


def test_api_artifact_endpoint(test_server):
    status, body = req(f"{test_server}/api/artifact?source_id=SRC-02")
    assert status == 200
    assert body == {"url": "/fixtures/checkout.png", "via": "local"}
    status, body = req(f"{test_server}/api/artifact?source_id=SRC-99")
    assert status == 404


def test_effective_extraction_mode_offline():
    from scopeshift.extraction import Extractor
    ex = Extractor()  # no key, no vertex env -> deterministic
    assert ex.effective_mode() == "deterministic-fallback"


def test_vertex_extractor_mocked_genai(monkeypatch):
    from unittest.mock import MagicMock
    from scopeshift.cloud import VertexExtractor
    from scopeshift.extraction import ClaimExtractionSchema

    vx = VertexExtractor()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps([
        {
            "claim_id": "checkout.payment_methods",
            "observation": "BRD specifies UPI only",
            "quote": "REQ-PAY-01: UPI only",
            "proposed_scope_change": False,
            "value": {"methods": ["UPI"]},
        }
    ])
    mock_client.models.generate_content.return_value = mock_resp

    monkeypatch.setattr(vx, "_client", mock_client)
    monkeypatch.setattr(vx, "_connected", True)

    res = vx.extract_claims("sample text", "brd", "Test prompt")
    assert res is not None
    assert len(res["claims"]) == 1
    assert res["claims"][0]["claim_id"] == "checkout.payment_methods"
    assert "vertex" in res["model"]

    call_args, call_kwargs = mock_client.models.generate_content.call_args
    cfg = call_kwargs["config"]
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_schema == list[ClaimExtractionSchema]


def test_vertex_extractor_404_fallback(monkeypatch):
    from unittest.mock import MagicMock
    from scopeshift.cloud import VertexExtractor

    vx = VertexExtractor(model="gemini-3.6-flash", fallbacks=["gemini-3.5-flash"])
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps([
        {
            "claim_id": "checkout.currency",
            "observation": "INR currency",
            "quote": "REQ-CUR-01: INR",
            "proposed_scope_change": False,
            "currency": "INR",
        }
    ])

    def side_effect(*args, **kwargs):
        m = kwargs.get("model")
        if m == "gemini-3.6-flash":
            raise Exception("404 models/gemini-3.6-flash not found")
        elif m == "gemini-3.5-flash":
            return mock_resp
        raise RuntimeError(f"Unexpected: {m}")

    mock_client.models.generate_content.side_effect = side_effect
    monkeypatch.setattr(vx, "_client", mock_client)
    monkeypatch.setattr(vx, "_connected", True)

    res = vx.extract_claims("sample text", "brd", "Test prompt")
    assert res is not None
    assert "gemini-3.5-flash" in res["model"]
    assert len(res["claims"]) == 1
    assert res["claims"][0]["value"] == {"currency": "INR"}
    assert mock_client.models.generate_content.call_count == 2


def test_bigquery_verify_read_back(monkeypatch):
    from unittest.mock import MagicMock
    from scopeshift.cloud import BigQueryLog

    bq = BigQueryLog()
    mock_client = MagicMock()
    mock_row = MagicMock()
    mock_row.get.side_effect = lambda k: {
        "event_sequence": 123,
        "source_id": "SRC-01",
        "event": "ADDED",
        "payload": '{"test": true}',
        "inserted_at": "2026-10-05T00:00:00Z",
    }.get(k)

    mock_job = MagicMock()
    mock_job.result.return_value = [mock_row]
    mock_client.query.return_value = mock_job

    monkeypatch.setattr(bq, "_client", mock_client)
    monkeypatch.setattr(bq, "_connected", True)
    monkeypatch.setattr(bq, "dataset_id", "test_ds")
    monkeypatch.setattr(bq, "table_id", "scopeshift_events")

    row = bq.verify_read_back(123)
    assert row is not None
    assert row["event_sequence"] == 123
    assert row["source_id"] == "SRC-01"
    assert row["payload"] == {"test": True}


def test_verify_cloud_script_fails_without_credentials():
    import subprocess
    import sys

    res = subprocess.run(
        [sys.executable, "scripts/verify_cloud.py"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "MISSING GOOGLE CLOUD CONFIGURATION / CREDENTIALS" in res.stdout
    assert "GOOGLE_CLOUD_PROJECT" in res.stdout
