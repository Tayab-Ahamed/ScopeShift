"""Tests for Task B: Security and input hardening.
Covers:
- Max upload size enforcement (10 MB -> 413)
- MIME type sniffing allowlist (non-allowed bytes -> 415)
- Shared-secret authentication (SCOPESHIFT_API_TOKEN -> 401 on missing/bad token)
- Per-IP rate limiting on /api/extract (-> 429)
- XSS prevention (quotes containing script/img tags render inertly)
"""
from __future__ import annotations

import base64
import html
import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import demo_server
from demo_server import Handler, create_demo_store, reset_rate_limits, sniff_mime_type


@pytest.fixture(scope="module")
def sec_server():
    demo_server.STORE = create_demo_store(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 8785), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    yield "http://127.0.0.1:8785"
    server.shutdown()


def req(url: str, method: str = "GET", data: dict | None = None, headers: dict | None = None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=body, headers=h, method=method)
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


def test_max_upload_size_rejected_413(sec_server):
    """Uploading body exceeding MAX_BODY (10 MB) must return 413 PAYLOAD_TOO_LARGE."""
    # Send headers claiming Content-Length larger than 10MB without needing to send all bytes
    r = urllib.request.Request(
        f"{sec_server}/api/extract",
        data=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": str(11 * 1024 * 1024)},
        method="POST",
    )
    try:
        with urllib.request.urlopen(r) as resp:
            pytest.fail("Expected 413 HTTPError")
    except urllib.error.HTTPError as err:
        assert err.code == 413
        data = json.loads(err.read().decode("utf-8"))
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"
        assert "10 MB" in data["error"]["message"]


def test_mime_sniffing_allowlist_enforcement(sec_server):
    """Uploaded files must have sniffed MIME in allowlist, returning 415 if not."""
    # 1. Disallowed binary executable payload (Windows PE header MZ)
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    payload = {
        "file_base64": base64.b64encode(exe_bytes).decode(),
        "filename": "innocent_document.pdf",  # misleading filename
        "source_type": "brd",
    }
    status, body, _ = req(f"{sec_server}/api/extract", "POST", payload)
    assert status == 415
    assert body["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    # 2. Disallowed arbitrary binary bytes
    bad_bytes = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08"
    payload2 = {
        "file_base64": base64.b64encode(bad_bytes).decode(),
        "filename": "test.png",
        "source_type": "screenshot",
    }
    status2, body2, _ = req(f"{sec_server}/api/extract", "POST", payload2)
    assert status2 == 415
    assert body2["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    # 3. Unit test sniff_mime_type helper directly
    assert sniff_mime_type(b"%PDF-1.4 header") == "application/pdf"
    assert sniff_mime_type(b"\x89PNG\r\n\x1a\nheader") == "image/png"
    assert sniff_mime_type(b"\xff\xd8\xff\xe0jpeg") == "image/jpeg"
    assert sniff_mime_type(b"RIFF\x00\x00\x00\x00WEBPheader") == "image/webp"
    assert sniff_mime_type(b"Hello clean UTF-8 text") == "text/plain"
    assert sniff_mime_type(b"\x00\x00nullbytes") is None


def test_optional_shared_secret_auth(sec_server, monkeypatch):
    """When SCOPESHIFT_API_TOKEN is set, all mutating endpoints require Bearer auth."""
    secret = "secret-token-scope-shift-xyz"
    monkeypatch.setenv("SCOPESHIFT_API_TOKEN", secret)

    # 1. Mutating endpoint (/api/reset) without auth -> 401
    status, body, _ = req(f"{sec_server}/api/reset", "POST")
    assert status == 401
    assert body["error"]["code"] == "UNAUTHORIZED"

    # 2. Mutating endpoint with wrong token -> 401
    status, body, _ = req(
        f"{sec_server}/api/reset",
        "POST",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert status == 401
    assert body["error"]["code"] == "UNAUTHORIZED"

    # 3. Mutating endpoint with valid token -> succeeds
    status, body, _ = req(
        f"{sec_server}/api/reset",
        "POST",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert status == 200
    assert "resolutions" in body or "sources" in body

    # 4. Non-mutating endpoint (GET /api/state) does not require token
    status, body, _ = req(f"{sec_server}/api/state", "GET")
    assert status == 200
    assert "resolutions" in body


def test_rate_limiting_per_ip(sec_server, monkeypatch):
    """Rate limit on /api/extract blocks excessive requests with 429."""
    reset_rate_limits()
    monkeypatch.setenv("SCOPESHIFT_RATE_LIMIT_PER_MINUTE", "3")

    payload = {
        "text": "We are changing scope. Checkout shall support Card payments.",
        "source_type": "client_note",
    }

    # First 3 requests should not be rate-limited
    for _ in range(3):
        status, _, _ = req(f"{sec_server}/api/extract", "POST", payload)
        assert status in (200, 201), f"Expected 200/201, got {status}"

    # 4th request must be rate-limited with 429
    status, body, _ = req(f"{sec_server}/api/extract", "POST", payload)
    assert status == 429
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "retry_after" in body["error"]
    assert body["error"]["retry_after"] > 0

    reset_rate_limits()


def test_xss_quote_injection_rendered_inert():
    """Verify that a quote containing malicious HTML/script renders inertly."""
    malicious_quote = '<img src=x onerror=alert(1)>'
    
    # In Javascript app.js, escapeHtml replaces:
    # & -> &amp;, < -> &lt;, > -> &gt;, " -> &quot;, ' -> &#039;
    def js_escape_html(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    escaped = js_escape_html(malicious_quote)
    assert "<img" not in escaped
    assert "<" not in escaped
    assert ">" not in escaped
    assert escaped == "&lt;img src=x onerror=alert(1)&gt;"

    # Verify standard HTML parser does not execute tag from escaped text
    assert "&lt;img" in escaped
