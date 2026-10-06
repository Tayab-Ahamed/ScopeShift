"""Tests for Task E: Concurrency, thread safety, and hash chain integrity."""
from __future__ import annotations

import concurrent.futures
import hashlib
from pathlib import Path
import tempfile
import pytest

from scopeshift.models import Evidence
from scopeshift.store import EventStore
from scripts.load_test import verify_hash_chain


def test_concurrent_source_id_allocation():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_concurrent_alloc.db"
        store = EventStore(db_path)

        def allocate_worker(_):
            return store.allocate_source_id()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            allocated = list(executor.map(allocate_worker, range(20)))

        # All 20 allocated IDs must be unique
        assert len(allocated) == 20
        assert len(set(allocated)) == 20
        assert all(s.startswith("SRC-") for s in allocated)
        store.close()


def test_concurrent_20_writes_preserves_hash_chain_integrity():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_concurrency.db"
        store = EventStore(db_path)

        # Confirm WAL mode enabled on persisted DB
        mode = store.db.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() == "wal"

        # Pre-seed items
        evidence_items = []
        for i in range(1, 21):
            sid = f"SRC-{i:02d}"
            ev = Evidence(
                source_id=sid,
                source_type="client_note",
                claim_id="checkout.payment_methods",
                value={"methods": ["Card"]},
                quote="Checkout shall support Card payments.",
                observation=f"Concurrent item {i}",
                proposed_scope_change=False,
                quote_verified=True,
                region=None,
                event_sequence=i,
                active=False,
            )
            evidence_items.append(ev)

        store.seed(evidence_items)

        # Concurrently add 20 events across 10 threads
        def worker(idx: int):
            sid = f"SRC-{idx:02d}"
            return store.add_event(sid, "ADDED")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(worker, range(1, 21)))

        assert len(results) == 20

        # Verify audit chain
        chain = store.audit_chain()
        assert len(chain) == 20

        # Every block sequence must be strictly sequential 1..20
        sequences = [b["sequence"] for b in chain]
        assert sequences == list(range(1, 21))

        # Cryptographically verify the hash chain
        is_valid, errors = verify_hash_chain(chain)
        assert is_valid is True, f"Hash chain verification failed: {errors}"
        assert len(errors) == 0

        # Test snapshot
        snap = store.snapshot()
        assert snap["chain_valid"] is True
        assert snap["current_seq"] == 20

        store.close()


def test_concurrent_mixed_writes_and_reads():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_mixed.db"
        store = EventStore(db_path)

        def write_worker(idx: int):
            sid = store.allocate_source_id()
            ev = Evidence(
                source_id=sid,
                source_type="client_note",
                claim_id="checkout.currency",
                value={"currency": "INR"},
                quote="All prices shall be shown and charged in INR.",
                observation="Mixed concurrent worker",
                proposed_scope_change=False,
                quote_verified=True,
                region=None,
                event_sequence=idx,
                active=False,
            )
            store.seed([ev])
            store.add_event(sid, "ADDED")
            return sid

        def read_worker(_):
            chain = store.audit_chain()
            is_valid, _ = verify_hash_chain(chain)
            return is_valid

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            write_futures = [executor.submit(write_worker, i) for i in range(1, 21)]
            read_futures = [executor.submit(read_worker, i) for i in range(10)]

            for f in concurrent.futures.as_completed(write_futures):
                f.result()
            for f in concurrent.futures.as_completed(read_futures):
                valid = f.result()
                assert valid is True

        chain = store.audit_chain()
        assert len(chain) == 20
        is_valid, errors = verify_hash_chain(chain)
        assert is_valid is True, f"Hash chain errors: {errors}"
        store.close()


def test_load_test_against_http_server():
    import threading
    from http.server import ThreadingHTTPServer
    import demo_server
    from scripts.load_test import run_load_test

    old_store = demo_server.STORE
    test_store = demo_server.create_demo_store(":memory:")
    demo_server.STORE = test_store

    server = ThreadingHTTPServer(("127.0.0.1", 0), demo_server.Handler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        summary = run_load_test(
            base_url=f"http://127.0.0.1:{port}",
            total_requests=20,
            threads=5,
        )
        assert summary["successful"] == 20
        assert summary["failed"] == 0
        assert summary["chain_valid"] is True
        assert summary["events_per_second"] > 0
    finally:
        server.shutdown()
        server.server_close()
        demo_server.STORE = old_store
        test_store.close()
