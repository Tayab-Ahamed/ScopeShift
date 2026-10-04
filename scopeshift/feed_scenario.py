"""Scripted live-feed scenario (Stream C).

HONESTY CONTRACT: every arrival below is a *scripted, simulated* artifact —
Slack messages, emails and screenshot notes invented for the demo. They are
NEVER real external data, and the UI must keep the "simulated live feed —
scripted scenario" label wherever this scenario plays.

What IS real: each arrival is ingested through the genuine code pipeline —
the same validation boundary as POST /api/ingest
(validate_claim -> Evidence -> EventStore.seed -> add_event -> best-effort
BigQuery dual-write via _store_event). The resulting claim states are real
deterministic resolver outputs, not canned strings.

Arrival schema:
  delay_seconds:        pause before this arrival is emitted (demo pacing)
  kind:                 display label: slack | email | screenshot | directive | withdrawal
  source_type:          real source_type for validate_claim (brd | screenshot | client_note)
  claim_id:             one of the 4 registered claim ids
  text:                 the "original" artifact text the quote is verified against
  quote:                verbatim quote (must appear in text after NFKC normalization)
  observation:          human-readable note shown in the ticker
  proposed_scope_change: True only for explicit client scope directives (FR-7)
  value:                structured claim value (must pass the claim spec's normalize)
  region:               screenshot region [x, y, w, h] (screenshots only)
  alias:                optional name so a later withdrawal can reference this source
  withdraws_alias:      only on kind == "withdrawal": emit REMOVED for that source.
                        The withdrawal message itself is ALSO ingested as a new
                        client_note observation — the retraction is a real artifact
                        AND a real event.
"""

ARRIVALS = [
    {
        "delay_seconds": 1.2,
        "kind": "slack",
        "source_type": "client_note",
        "claim_id": "checkout.payment_methods",
        "text": "Priya (Slack, #checkout-launch): hey team — quick q: can we support Card payments at checkout for launch?",
        "quote": "can we support Card payments at checkout for launch",
        "observation": "Client asks about Card support on Slack — a question, not a decision",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
    },
    {
        "delay_seconds": 1.6,
        "kind": "email",
        "source_type": "client_note",
        "claim_id": "checkout.payment_methods",
        "text": "From: Priya Nair\nSubject: Re: checkout scope\n\nFollowing up on Slack — we'd like Card payments included in v1 scope. Let me know what you need from us to confirm.",
        "quote": "we'd like Card payments included in v1 scope",
        "observation": "Client email expresses interest — still no explicit authorization",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
    },
    {
        "delay_seconds": 1.4,
        "kind": "screenshot",
        "source_type": "screenshot",
        "claim_id": "checkout.payment_methods",
        "text": "",
        "quote": "Pay with Card",
        "observation": "New staging screenshot note: the Card button renders on the checkout page",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
        "region": [460, 285, 370, 80],
    },
    {
        "delay_seconds": 2.0,
        "kind": "directive",
        "source_type": "client_note",
        "claim_id": "checkout.payment_methods",
        "text": "From: Priya Nair (Client, Product Owner)\nSubject: DECISION — checkout payment scope\n\nDECISION: Card is approved in scope for v1. UPI moves to Phase 2. This is the formal scope authorization.",
        "quote": "Card is approved in scope for v1. UPI moves to Phase 2",
        "observation": "Explicit client scope directive — verified quote, proposed_scope_change=True",
        "proposed_scope_change": True,
        "value": {"methods": ["Card"], "deferred": ["UPI"]},
        "alias": "card-directive",
    },
    {
        "delay_seconds": 1.4,
        "kind": "email",
        "source_type": "client_note",
        "claim_id": "auth.mfa_requirement",
        "text": "From: Security review\nSubject: login hardening\n\nHeads-up: the security review notes we may need MFA for logins before launch. No decision yet — flagging for discussion.",
        "quote": "we may need MFA for logins before launch",
        "observation": "Security review flags MFA — an observation, no authority claimed",
        "proposed_scope_change": False,
        "value": {"mfa_required": True, "channels": ["TOTP Authenticator"]},
    },
    {
        "delay_seconds": 2.0,
        "kind": "directive",
        "source_type": "client_note",
        "claim_id": "auth.mfa_requirement",
        "text": "From: Priya Nair (Client, Product Owner)\nSubject: DECISION — MFA requirement\n\nDECISION: MFA is required for all logins via TOTP and SMS. Please record this as a governed requirement.",
        "quote": "MFA is required for all logins via TOTP and SMS",
        "observation": "Explicit client scope directive for MFA — verified, governing",
        "proposed_scope_change": True,
        "value": {"mfa_required": True, "channels": ["TOTP Authenticator", "SMS OTP"]},
        "alias": "mfa-directive",
    },
    {
        "delay_seconds": 2.2,
        "kind": "withdrawal",
        "source_type": "client_note",
        "claim_id": "checkout.payment_methods",
        "text": "From: Priya Nair\nSubject: HOLD — Card scope decision\n\nUpdate from legal: please hold the Card scope decision — reverting until the review completes. The earlier authorization is withdrawn.",
        "quote": "please hold the Card scope decision",
        "observation": "Client withdraws the earlier Card directive — the retraction is ingested as evidence AND emits REMOVED",
        "proposed_scope_change": False,
        "value": {"methods": ["Card"]},
        "withdraws_alias": "card-directive",
    },
    {
        "delay_seconds": 1.6,
        "kind": "directive",
        "source_type": "client_note",
        "claim_id": "refunds.settlement_sla",
        "text": "From: Priya Nair (Client, Product Owner)\nSubject: DECISION — refund SLA\n\nDECISION: Refund settlement SLA is 24 hours with instant automated settlement. Please record this as a governed requirement.",
        "quote": "Refund settlement SLA is 24 hours with instant automated settlement",
        "observation": "Explicit client scope directive for refund SLA — verified, governing",
        "proposed_scope_change": True,
        "value": {"sla_hours": 24, "instant_settlement": True},
        "alias": "sla-directive",
    },
]

SCENARIO_TITLE = "Evening with the client — scripted evidence arrivals"
