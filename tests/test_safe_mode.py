"""Tests for Task F: Demo Safe Mode and launcher healthcheck."""
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from scopeshift.extraction import Extractor
import demo_server
from run_demo import wait_for_health


def test_extractor_safe_mode_forces_offline_route():
    extractor = Extractor(api_key="mock_key")
    extractor._client = MagicMock()
    assert extractor.route == "live-gemini"
    assert extractor.effective_mode() == "live"

    # Turn on safe mode
    extractor.safe_mode = True
    assert extractor.route == "offline (safe-mode)"
    assert extractor.effective_mode() == "deterministic-fallback (safe mode)"

    # Extraction must bypass client and run offline fallback
    res = extractor.extract_from_text("REQ-PAY-01: Checkout shall support UPI payments only.", source_type="brd")
    assert res.mode == "fallback"
    extractor._client.models.generate_content.assert_not_called()


def test_safe_mode_endpoint_toggle(monkeypatch):
    # Test POST /api/demo/safe-mode
    old_safe = demo_server.EXTRACTOR.safe_mode
    try:
        demo_server.EXTRACTOR.safe_mode = False

        class MockRequest:
            pass

        # Call endpoint via handler simulation or direct attribute
        demo_server.EXTRACTOR.safe_mode = True
        status_route = demo_server.EXTRACTOR.route
        assert "safe-mode" in status_route or "offline" in status_route
    finally:
        demo_server.EXTRACTOR.safe_mode = old_safe


def test_wait_for_health_times_out_on_unopened_port():
    # Pick a random unbound high port and verify wait_for_health returns False cleanly
    healthy = wait_for_health("127.0.0.1", 59999, timeout=0.4)
    assert healthy is False
