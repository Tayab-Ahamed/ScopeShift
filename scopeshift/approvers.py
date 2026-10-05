"""Approver allowlist management for ScopeShift.

Loads allowlisted approvers from approvers.json (configured via SCOPESHIFT_APPROVERS).
Enforces the invariant: only allowlisted senders can govern client notes.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

APPROVERS_ENV = "SCOPESHIFT_APPROVERS"
DEFAULT_APPROVERS_PATH = "./approvers.json"

DEFAULT_APPROVERS = [
    {
        "name": "Priya Nair",
        "email": "priya@meridian.internal",
        "role": "Client Product Owner",
        "channel": "any",
    },
    {
        "name": "Alex Mercer",
        "email": "alex@meridian.internal",
        "role": "Lead Architect",
        "channel": "any",
    },
]


def load_approvers(config_path: str | Path | None = None) -> list[dict]:
    path_str = config_path or os.environ.get(APPROVERS_ENV, DEFAULT_APPROVERS_PATH)
    path = Path(path_str)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.warning("Failed to load approvers from %s: %s", path, exc)
    return list(DEFAULT_APPROVERS)


def is_sender_allowlisted(sender: Optional[str], channel: Optional[str] = None) -> bool:
    """Check if the sender is allowlisted in approvers.json."""
    if not sender:
        return False
    approvers = load_approvers()
    s_norm = sender.strip().casefold()
    for app in approvers:
        name = app.get("name", "").strip().casefold()
        email_addr = app.get("email", "").strip().casefold()
        matched = False
        if name and (s_norm == name or name in s_norm or s_norm in name):
            matched = True
        elif email_addr and (s_norm == email_addr or email_addr in s_norm or s_norm in email_addr):
            matched = True

        if matched:
            app_ch = app.get("channel", "any")
            if channel and app_ch and app_ch.casefold() not in ("any", "*"):
                ch_norm = channel.strip().casefold()
                app_ch_norm = app_ch.strip().casefold()
                if ch_norm != app_ch_norm:
                    continue
            return True
    return False
