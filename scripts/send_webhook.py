#!/usr/bin/env python3
"""Script to sign and send an inbound webhook message to ScopeShift.

Usage:
  python scripts/send_webhook.py [--secret SECRET] [--url URL] [--sender SENDER]
                                 [--channel CHANNEL] [--text TEXT] [--message-id ID]
                                 [--stale] [--bad-sig]
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()


def send_webhook(
    secret: str,
    url: str = "http://127.0.0.1:8765/api/webhook/inbound",
    sender: str = "Priya Nair",
    channel: str = "slack",
    text: str = "We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.",
    message_id: str | None = None,
    stale: bool = False,
    bad_sig: bool = False,
) -> tuple[int, dict]:
    msg_id = message_id or f"msg-{int(time.time() * 1000)}"
    
    # Generate timestamp
    if stale:
        # 10 minutes in the past
        received_at = datetime.fromtimestamp(time.time() - 600, tz=timezone.utc).isoformat()
    else:
        received_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "channel": channel,
        "sender": sender,
        "text": text,
        "received_at": received_at,
        "message_id": msg_id,
        "attachments": [],
    }

    body_bytes = json.dumps(payload).encode("utf-8")

    if bad_sig:
        signature = "sha256=" + "0" * 64
    else:
        mac = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        signature = f"sha256={mac}"

    headers = {
        "Content-Type": "application/json",
        "X-ScopeShift-Signature": signature,
    }

    req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as err:
        try:
            data = json.loads(err.read().decode("utf-8"))
        except Exception:
            data = {"raw": err.read().decode("utf-8", errors="replace")}
        return err.code, data


def main() -> int:
    parser = argparse.ArgumentParser(description="Send signed inbound webhook to ScopeShift")
    parser.add_argument("--secret", default=os.environ.get("SCOPESHIFT_WEBHOOK_SECRET", "default-dev-secret"))
    parser.add_argument("--url", default="http://127.0.0.1:8765/api/webhook/inbound")
    parser.add_argument("--sender", default="Priya Nair")
    parser.add_argument("--channel", default="slack")
    parser.add_argument("--text", default="We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2.")
    parser.add_argument("--message-id", default=None)
    parser.add_argument("--stale", action="store_true", help="Send timestamp > 5 minutes old")
    parser.add_argument("--bad-sig", action="store_true", help="Send deliberately invalid HMAC signature")

    args = parser.parse_args()

    print(f"Sending webhook to {args.url} (sender: '{args.sender}', channel: '{args.channel}')...")
    status, res = send_webhook(
        secret=args.secret,
        url=args.url,
        sender=args.sender,
        channel=args.channel,
        text=args.text,
        message_id=args.message_id,
        stale=args.stale,
        bad_sig=args.bad_sig,
    )

    print(f"Response status: {status}")
    print(json.dumps(res, indent=2))
    return 0 if status in (200, 201) else 1


if __name__ == "__main__":
    if (REPO_ROOT / ".env").exists():
        try:
            import dotenv
            dotenv.load_dotenv(REPO_ROOT / ".env")
        except Exception:
            pass
    sys.exit(main())
