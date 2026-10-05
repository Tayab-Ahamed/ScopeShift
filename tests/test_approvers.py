"""Tests for Task 5: Source identity, approver allowlist, and authorization enforcement."""
import json
import pytest
from pathlib import Path

from scopeshift.approvers import load_approvers, is_sender_allowlisted
from scopeshift.models import Evidence
from scopeshift.validation import validate_claim
from scopeshift.resolver import resolve


def test_load_approvers_from_file(tmp_path):
    custom_approvers = [
        {"name": "Alice Smith", "role": "Lead Architect", "channel": "slack"},
        {"name": "Bob Jones", "role": "VP Product", "channel": "email"},
    ]
    approvers_file = tmp_path / "custom_approvers.json"
    approvers_file.write_text(json.dumps(custom_approvers), encoding="utf-8")

    loaded = load_approvers(approvers_file)
    assert len(loaded) == 2
    assert loaded[0]["name"] == "Alice Smith"
    assert loaded[1]["name"] == "Bob Jones"


def test_is_sender_allowlisted():
    # Priya Nair is in default approvers.json
    assert is_sender_allowlisted("Priya Nair") is True
    assert is_sender_allowlisted("priya@meridian.internal") is True
    assert is_sender_allowlisted("Alex Mercer") is True

    # Unauthorized external senders
    assert is_sender_allowlisted("Mallory (Attacker)") is False
    assert is_sender_allowlisted("unknown@external.com") is False
    assert is_sender_allowlisted("") is False
    assert is_sender_allowlisted(None) is False


def test_client_note_governs_only_when_sender_allowlisted():
    text = "Official Directive: Checkout shall support Card payments. UPI moves to Phase 2."
    quote = "Checkout shall support Card payments. UPI moves to Phase 2."

    # Authorized sender: Priya Nair -> governs
    raw_auth = {
        "claim_id": "checkout.payment_methods",
        "quote": quote,
        "observation": "Client decision",
        "proposed_scope_change": True,
        "value": {"methods": ["Card"], "deferred": ["UPI"]},
        "sender": "Priya Nair",
        "channel": "slack",
    }
    v_auth = validate_claim(raw_auth, "client_note", text=text)
    assert v_auth["proposed_scope_change"] is True
    assert v_auth["quote_verified"] is True
    ev_auth = Evidence(
        "SRC-03", "client_note", v_auth["claim_id"], v_auth["value"], v_auth["quote"],
        proposed_scope_change=v_auth["proposed_scope_change"],
        quote_verified=v_auth["quote_verified"],
        sender=v_auth["sender"],
        channel=v_auth["channel"],
    )
    assert ev_auth.governing is True

    # Unauthorized sender: Mallory -> demoted to observation with reason 'sender not authorised'
    raw_forged = {
        "claim_id": "checkout.payment_methods",
        "quote": quote,
        "observation": "Client decision",
        "proposed_scope_change": True,
        "value": {"methods": ["Card"], "deferred": ["UPI"]},
        "sender": "Mallory (Impersonator)",
        "channel": "slack",
    }
    v_forged = validate_claim(raw_forged, "client_note", text=text)
    assert v_forged["proposed_scope_change"] is False
    assert "sender not authorised" in v_forged["observation"]
    ev_forged = Evidence(
        "SRC-04", "client_note", v_forged["claim_id"], v_forged["value"], v_forged["quote"],
        proposed_scope_change=v_forged["proposed_scope_change"],
        quote_verified=v_forged["quote_verified"],
        sender=v_forged["sender"],
        channel=v_forged["channel"],
    )
    assert ev_forged.governing is False


def test_unauthorized_sender_cannot_govern_in_resolver():
    ev_brd = Evidence(
        "SRC-01", "brd", "checkout.payment_methods",
        {"methods": ["UPI"], "exclusive": True}, "UPI only",
        proposed_scope_change=False, quote_verified=True, active=True, event_sequence=1,
    )
    ev_shot = Evidence(
        "SRC-02", "screenshot", "checkout.payment_methods",
        {"methods": ["Card"]}, "Pay with Card",
        proposed_scope_change=False, quote_verified=True, active=True, event_sequence=2,
    )
    # Mallory sends note with proposed_scope_change=False (forced by validator)
    ev_forged = Evidence(
        "SRC-03", "client_note", "checkout.payment_methods",
        {"methods": ["Card"], "deferred": ["UPI"]}, "Card approved",
        proposed_scope_change=False,  # forced False
        quote_verified=True,
        sender="Mallory (Impersonator)",
        active=True, event_sequence=3,
    )

    # Resolution remains DISPUTED — unverified/unauthorized note CANNOT govern!
    res = resolve("checkout.payment_methods", [ev_brd, ev_shot, ev_forged])
    assert res.state == "DISPUTED"
    assert res.in_brd is False
