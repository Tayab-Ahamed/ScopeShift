#!/usr/bin/env python3
"""Load testing and hash-chain concurrency verification for ScopeShift.

Fires N concurrent ingests against a running server with T worker threads,
tracks latency and throughput, and verifies hash-chain cryptographic integrity.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from typing import Any, NamedTuple


class IngestResult(NamedTuple):
    index: int
    success: bool
    status_code: int
    latency_ms: float
    error: str | None


def send_ingest(
    base_url: str,
    index: int,
    token: str | None = None,
    timeout: float = 10.0,
) -> IngestResult:
    url = f"{base_url.rstrip('/')}/api/ingest"
    payload = {
        "source_type": "client_note",
        "claim_id": "checkout.payment_methods",
        "text": f"Load test note #{index}: Checkout shall support Card payments.",
        "quote": "Checkout shall support Card payments.",
        "observation": f"Load test note #{index}",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = (time.perf_counter() - start) * 1000.0
            return IngestResult(index, resp.status in (200, 201), resp.status, latency, None)
    except urllib.error.HTTPError as err:
        latency = (time.perf_counter() - start) * 1000.0
        return IngestResult(index, False, err.code, latency, f"HTTP {err.code}: {err.reason}")
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000.0
        return IngestResult(index, False, 0, latency, str(exc))


def verify_hash_chain(chain_blocks: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Cryptographically verify all blocks in the hash chain:
    1. Recompute sha256(hash_input) == hash for each block.
    2. Check genesis prev_hash == 64 zeros.
    3. Check prev_hash links to previous block's hash.
    4. Check sequence numbers are strictly monotonic without gaps.
    """
    errors: list[str] = []
    if not chain_blocks:
        errors.append("Empty audit chain")
        return False, errors

    prev_hash = "0" * 64
    for idx, block in enumerate(chain_blocks):
        seq = block.get("sequence")
        b_hash = block.get("hash")
        b_prev = block.get("prev_hash")
        h_input = block.get("hash_input")

        # 1. Monotonic sequence check
        expected_seq = idx + 1
        if seq != expected_seq:
            errors.append(f"Block #{idx}: sequence {seq} != expected {expected_seq}")

        # 2. Linkage check
        if b_prev != prev_hash:
            errors.append(f"Block #{idx} (seq {seq}): prev_hash {b_prev} != expected {prev_hash}")

        # 3. Hash computation check
        recomputed = hashlib.sha256(h_input.encode("utf-8")).hexdigest()
        if recomputed != b_hash:
            errors.append(f"Block #{idx} (seq {seq}): hash mismatch {b_hash} != {recomputed}")

        prev_hash = b_hash

    return len(errors) == 0, errors


def run_load_test(
    base_url: str = "http://127.0.0.1:8765",
    total_requests: int = 50,
    threads: int = 10,
    token: str | None = None,
) -> dict[str, Any]:
    # 1. Health check
    health_url = f"{base_url.rstrip('/')}/api/health"
    try:
        with urllib.request.urlopen(health_url, timeout=5.0) as resp:
            health_data = json.loads(resp.read().decode("utf-8"))
            if health_data.get("status") != "ok":
                raise RuntimeError(f"Server unhealthy: {health_data}")
    except Exception as exc:
        print(f"Error: Server unreachable at {health_url}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting load test against {base_url}...")
    print(f"Total ingests: {total_requests} | Concurrency: {threads} threads")

    start_wall = time.perf_counter()
    results: list[IngestResult] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [
            executor.submit(send_ingest, base_url, i + 1, token)
            for i in range(total_requests)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    duration = time.perf_counter() - start_wall

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    latencies = sorted(r.latency_ms for r in successful) if successful else [0.0]

    eps = len(successful) / duration if duration > 0 else 0.0

    def percentile(data: list[float], pct: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * (pct / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        d0 = data[int(f)] * (c - k)
        d1 = data[int(c)] * (k - f)
        return d0 + d1

    p50 = percentile(latencies, 50)
    p90 = percentile(latencies, 90)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    max_lat = max(latencies) if latencies else 0.0
    min_lat = min(latencies) if latencies else 0.0

    # 2. Cryptographic audit chain verification
    chain_url = f"{base_url.rstrip('/')}/api/audit/chain"
    with urllib.request.urlopen(chain_url, timeout=10.0) as resp:
        chain_data = json.loads(resp.read().decode("utf-8"))
        blocks = chain_data.get("blocks", [])

    chain_valid, chain_errors = verify_hash_chain(blocks)

    summary = {
        "requests": total_requests,
        "successful": len(successful),
        "failed": len(failed),
        "concurrency": threads,
        "duration_sec": round(duration, 3),
        "events_per_second": round(eps, 2),
        "latency_min_ms": round(min_lat, 2),
        "latency_p50_ms": round(p50, 2),
        "latency_p90_ms": round(p90, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2),
        "latency_max_ms": round(max_lat, 2),
        "chain_total_blocks": len(blocks),
        "chain_valid": chain_valid,
        "chain_errors": chain_errors,
    }

    print("\n" + "=" * 50)
    print("       ScopeShift Load Test Results")
    print("=" * 50)
    print(f"Total Requests:     {total_requests}")
    print(f"Successful:         {len(successful)}")
    print(f"Failed:             {len(failed)}")
    print(f"Threads:            {threads}")
    print(f"Duration:           {duration:.2f} s")
    print(f"Events / Sec (EPS): {eps:.2f}")
    print(f"Latency min:        {min_lat:.1f} ms")
    print(f"Latency p50:        {p50:.1f} ms")
    print(f"Latency p90:        {p90:.1f} ms")
    print(f"Latency p95:        {p95:.1f} ms")
    print(f"Latency p99:        {p99:.1f} ms")
    print(f"Latency max:        {max_lat:.1f} ms")
    print(f"Audit Chain Blocks: {len(blocks)}")
    print(f"Hash Chain Valid:   {chain_valid}")
    if chain_errors:
        print(f"Chain Errors:       {chain_errors}")
    print("=" * 50 + "\n")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScopeShift concurrent load test")
    parser.add_argument("--url", default="http://127.0.0.1:8765", help="Base URL of ScopeShift server")
    parser.add_argument("-n", "--requests", type=int, default=50, help="Number of ingests (default: 50)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Worker threads (default: 10)")
    parser.add_argument("--token", default=None, help="Bearer token if auth enabled")

    args = parser.parse_args()
    res = run_load_test(
        base_url=args.url,
        total_requests=args.requests,
        threads=args.threads,
        token=args.token,
    )
    if res["failed"] > 0 or not res["chain_valid"]:
        sys.exit(1)
    sys.exit(0)
