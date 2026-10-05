"""Tests for benchmark/run_benchmark.py functionality and honest failure on missing key."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from benchmark.run_benchmark import (
    ADVERSARIAL_PROMPTS,
    evaluate_scopeshift_adversarial,
    evaluate_scopeshift_stage1,
    evaluate_scopeshift_stage2,
    evaluate_scopeshift_stage3,
)
from scopeshift.store import EventStore


def test_benchmark_exits_cleanly_without_api_key(monkeypatch):
    """Missing key must exit with code 1 and a clear message without fabricating numbers."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = subprocess.run(
        [sys.executable, "benchmark/run_benchmark.py"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "GEMINI_API_KEY is not set" in res.stdout
    assert "Never fabricate benchmark numbers" in res.stdout


def test_benchmark_scopeshift_checkout_stages():
    """Verify ScopeShift state transitions across the 3 checkout conflict stages."""
    store = EventStore(":memory:")
    s1 = evaluate_scopeshift_stage1(store)
    assert s1["state"] == "CONSISTENT"
    assert s1["in_brd"] is True
    assert s1["admitted_card"] is False

    s2 = evaluate_scopeshift_stage2(store)
    assert s2["state"] == "DISPUTED"
    assert s2["in_brd"] is False
    assert "withheld" in s2["reason"].lower()
    assert s2["admitted_card"] is False

    s3 = evaluate_scopeshift_stage3(store)
    assert s3["state"] == "GOVERNED"
    assert s3["in_brd"] is True
    assert s3["governing_source"] == "SRC-03"
    assert s3["admitted_card"] is True


def test_benchmark_scopeshift_adversarial_all_blocked():
    """All 5 adversarial chaos cases must be rejected/withheld by ScopeShift code invariants."""
    for case in ADVERSARIAL_PROMPTS:
        res = evaluate_scopeshift_adversarial(case)
        assert res["admitted"] is False, f"Case {case} should have been blocked"
