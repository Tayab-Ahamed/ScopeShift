"""Domain tests: claim registry, validation, generic resolver, replay (PRD FR-5..FR-20, AT-1..AT-6)."""
import pytest

from scopeshift.models import Evidence, Event
from scopeshift.resolver import replay, resolve
from scopeshift.validation import (
    ValidationError, normalize, png_size, quote_in_text, validate_claim, validate_citations,
)

PAY = "checkout.payment_methods"
CUR = "checkout.currency"
BRD_TEXT = "REQ-PAY-01: Checkout shall support UPI payments only.\nUPI is the exclusive payment method."
NOTE_TEXT = "We are changing scope. Checkout shall support Card payments. UPI moves to Phase 2."


def ev(source_id, source_type, claim_id, value, quote="q", *, scope=False, verified=True):
    return Evidence(source_id, source_type, claim_id, value, quote,
                    proposed_scope_change=scope, quote_verified=verified)


def brd(sid="SRC-01"):
    return ev(sid, "brd", PAY, {"methods": ["UPI"], "exclusive": True})


def shot(sid="SRC-02", methods=("Card",)):
    return ev(sid, "screenshot", PAY, {"methods": list(methods)})


def note(sid="SRC-03", **kw):
    return ev(sid, "client_note", PAY, {"methods": ["Card"], "deferred": ["UPI"]}, scope=True, **kw)


def activate(*items, start=1):
    return [Evidence(**{**i.__dict__, "active": True, "event_sequence": start + n}) for n, i in enumerate(items)]


# ---------- resolver ----------
def test_brd_and_screenshot_conflict_is_disputed_and_withheld():
    r = resolve(PAY, activate(brd(), shot()))
    assert r.state == "DISPUTED" and r.requirement is None and not r.in_brd
    assert {c["source_id"] for c in r.citations} == {"SRC-01", "SRC-02"}


def test_verified_client_note_governs_and_supersedes_brd():
    r = resolve(PAY, activate(brd(), shot(), note()))
    assert r.state == "GOVERNED" and r.in_brd
    assert r.governing_source == "SRC-03" and r.superseded_sources == ["SRC-01"]
    assert "Card" in r.requirement and "UPI" in r.requirement and "Phase 2" in r.requirement
    assert r.replaced_requirement and "UPI" in r.replaced_requirement


def test_screenshot_can_never_govern_even_if_it_claims_scope_change():
    forged = ev("SRC-02", "screenshot", PAY, {"methods": ["Card"]}, scope=True)
    assert not forged.governing
    assert resolve(PAY, activate(brd(), forged)).state == "DISPUTED"


def test_unverified_client_note_cannot_govern():
    r = resolve(PAY, activate(brd(), shot(), note(verified=False)))
    assert r.state == "DISPUTED"


def test_non_scope_change_note_is_evidence_only():  # AT-2: "Looks good"
    ack = ev("SRC-03", "client_note", PAY, {"methods": ["Card"]}, scope=False)
    assert not ack.governing
    assert resolve(PAY, activate(brd(), shot(), ack)).state == "DISPUTED"


def test_non_exclusive_brd_plus_card_screenshot_is_not_a_contradiction():  # AT-3
    open_brd = ev("SRC-01", "brd", PAY, {"methods": ["UPI"], "exclusive": False})
    assert resolve(PAY, activate(open_brd, shot())).state == "CONSISTENT"
    both = ev("SRC-01", "brd", PAY, {"methods": ["UPI", "Card"], "exclusive": True})
    assert resolve(PAY, activate(both, shot())).state == "CONSISTENT"


def test_later_governing_decision_wins_by_event_sequence():
    first = note("SRC-03")
    second = ev("SRC-04", "client_note", PAY, {"methods": ["UPI", "Card"]}, scope=True)
    r = resolve(PAY, activate(brd(), first, second))
    assert r.governing_source == "SRC-04"
    r2 = resolve(PAY, [Evidence(**{**e.__dict__, "event_sequence": s, "active": True})
                       for e, s in ((brd(), 1), (first, 5), (second, 3))])
    assert r2.governing_source == "SRC-03"


def test_only_observation_never_becomes_a_requirement():
    r = resolve(PAY, activate(shot()))
    assert r.state == "UNKNOWN" and not r.in_brd


def test_resolver_is_generic_second_claim_uses_same_function():
    b = ev("SRC-01", "brd", CUR, {"currency": "INR"})
    s_ok = ev("SRC-02", "screenshot", CUR, {"currency": "INR"})
    s_bad = ev("SRC-02", "screenshot", CUR, {"currency": "USD"})
    assert resolve(CUR, activate(b, s_ok)).state == "CONSISTENT"
    assert resolve(CUR, activate(b, s_bad)).state == "DISPUTED"
    assert resolve(CUR, activate(b, s_ok)).requirement == "All prices shall be shown and charged in INR."


def test_resolver_ignores_inactive_and_other_claims():
    inactive = Evidence(**{**note().__dict__, "active": False})
    r = resolve(PAY, activate(brd(), shot()) + [inactive, ev("SRC-09", "brd", CUR, {"currency": "INR"})])
    assert r.state == "DISPUTED"


# ---------- replay / state machine ----------
def pool():
    return [brd(), shot(), note()]


def E(seq, sid, kind):
    return Event(seq, sid, kind)


def test_three_beats_replay_from_log_alone():  # AT-1
    log = [E(1, "SRC-01", "ADDED"), E(2, "SRC-02", "ADDED")]
    assert replay(pool(), log).resolutions[PAY].state == "DISPUTED"
    log.append(E(3, "SRC-03", "ADDED"))
    assert replay(pool(), log).resolutions[PAY].state == "GOVERNED"
    log.append(E(4, "SRC-03", "REMOVED"))
    assert replay(pool(), log).resolutions[PAY].state == "DISPUTED"


def test_replay_is_deterministic_and_order_independent_of_input_order():  # AT-6
    log = [E(1, "SRC-01", "ADDED"), E(2, "SRC-02", "ADDED"), E(3, "SRC-03", "ADDED")]
    a = replay(pool(), log).snapshot()
    b = replay(pool(), list(reversed(log))).snapshot()
    assert a == b == replay(pool(), log).snapshot()


@pytest.mark.parametrize("log", [
    [E(1, "SRC-99", "REMOVED")],                                   # unknown source
    [E(1, "SRC-99", "ADDED")],                                     # unknown source
    [E(1, "SRC-01", "REMOVED")],                                   # remove before add
    [E(1, "SRC-01", "ADDED"), E(2, "SRC-01", "ADDED")],            # duplicate add
    [E(1, "SRC-01", "ADDED"), E(2, "SRC-01", "REMOVED"), E(3, "SRC-01", "REMOVED")],
    [E(1, "SRC-01", "ADDED"), E(2, "SRC-01", "REMOVED"), E(3, "SRC-01", "ADDED")],  # re-add
    [E(1, "SRC-01", "ARCHIVED")],
    [E(1, "SRC-01", "ADDED"), E(1, "SRC-02", "ADDED")],            # non-monotonic sequence
])
def test_invalid_transitions_rejected(log):  # AT-5
    with pytest.raises(ValueError):
        replay(pool(), log)


def test_timeline_and_disappearance_explanation():
    log = [E(1, "SRC-01", "ADDED"), E(2, "SRC-02", "ADDED"), E(3, "SRC-03", "ADDED"), E(4, "SRC-03", "REMOVED")]
    res = replay(pool(), log)
    states = [step["claims"][PAY]["state"] for step in res.timeline]
    assert states == ["UNKNOWN", "CONSISTENT", "DISPUTED", "GOVERNED", "DISPUTED"]
    final = res.resolutions[PAY]
    assert final.disappeared and final.disappeared["event_sequence"] == 4
    assert final.disappeared["source_id"] == "SRC-03"
    assert "withdrawn" in final.reason.lower()


def test_current_brd_citations_must_reference_active_evidence():  # FR-8, FR-18
    res = replay(pool(), [E(1, "SRC-01", "ADDED"), E(2, "SRC-02", "ADDED"), E(3, "SRC-03", "ADDED")])
    validate_citations(res.resolutions.values(), res.active_evidence)
    bad = replay(pool(), [E(1, "SRC-01", "ADDED")]).resolutions[PAY]
    object.__setattr__(bad, "citations", [{"source_id": "SRC-77", "quote": "x"}])
    with pytest.raises(ValidationError):
        validate_citations([bad], res.active_evidence)


# ---------- validation ----------
def test_normalize_handles_case_whitespace_and_curly_quotes():
    assert normalize("  Card\u2019s\n  IN   scope ") == "card's in scope"


def test_quote_must_exist_in_text():
    assert quote_in_text("Checkout shall support Card payments.", NOTE_TEXT)
    assert quote_in_text("checkout   SHALL support card payments.", NOTE_TEXT)
    assert not quote_in_text("Checkout shall support Bitcoin.", NOTE_TEXT)
    assert not quote_in_text("", NOTE_TEXT)


def good_raw(**kw):
    raw = {"claim_id": PAY, "observation": "Client authorises Card",
           "quote": "Checkout shall support Card payments. UPI moves to Phase 2.",
           "proposed_scope_change": True, "value": {"methods": ["Card"], "deferred": ["UPI"]}}
    raw.update(kw)
    return raw


def test_validate_text_claim_marks_governing_only_when_quote_verified():
    ok = validate_claim(good_raw(), "client_note", text=NOTE_TEXT)
    assert ok["quote_verified"] and ok["proposed_scope_change"]
    bad = validate_claim(good_raw(quote="invented sentence"), "client_note", text=NOTE_TEXT)
    assert not bad["quote_verified"]


def test_hallucinated_claim_id_and_bad_value_rejected():  # AT-4
    with pytest.raises(ValidationError):
        validate_claim(good_raw(claim_id="checkout.bitcoin"), "client_note", text=NOTE_TEXT)
    with pytest.raises(ValidationError):
        validate_claim(good_raw(value={"methods": []}), "client_note", text=NOTE_TEXT)
    with pytest.raises(ValidationError):
        validate_claim(good_raw(value="Card"), "client_note", text=NOTE_TEXT)
    with pytest.raises(ValidationError):
        validate_claim(good_raw(), "email", text=NOTE_TEXT)


def test_screenshot_region_checked_against_image_bounds_and_never_scope_change():
    raw = {"claim_id": PAY, "observation": "Card button", "quote": "Pay with Card",
           "proposed_scope_change": True, "value": {"methods": ["Card"]}, "region": [460, 285, 370, 80]}
    ok = validate_claim(raw, "screenshot", image_size=(900, 620))
    assert ok["quote_verified"] and ok["proposed_scope_change"] is False
    off = validate_claim({**raw, "region": [880, 600, 100, 100]}, "screenshot", image_size=(900, 620))
    assert not off["quote_verified"]
    missing = validate_claim({k: v for k, v in raw.items() if k != "region"}, "screenshot", image_size=(900, 620))
    assert not missing["quote_verified"]


def test_png_size_reads_header():
    from pathlib import Path
    data = Path(__file__).parent.parent.joinpath("fixtures", "checkout.png").read_bytes()
    assert png_size(data) == (900, 620)
    with pytest.raises(ValidationError):
        png_size(b"not a png")


def test_mfa_requirement_claim_resolution():
    mfa_id = "auth.mfa_requirement"
    b = ev("SRC-01", "brd", mfa_id, {"mfa_required": False})
    s = ev("SRC-02", "screenshot", mfa_id, {"mfa_required": True})
    n = ev("SRC-03", "client_note", mfa_id, {"mfa_required": True, "channels": ["TOTP Authenticator", "SMS OTP"]}, scope=True)

    # 1. Dispute when observation conflicts with baseline
    res_disputed = resolve(mfa_id, activate(b, s))
    assert res_disputed.state == "DISPUTED"
    assert not res_disputed.in_brd

    # 2. Governed when client authorizes
    res_governed = resolve(mfa_id, activate(b, s, n))
    assert res_governed.state == "GOVERNED"
    assert res_governed.in_brd
    assert "Multi-Factor Authentication" in res_governed.requirement
    assert "TOTP Authenticator" in res_governed.requirement


def test_refund_sla_claim_resolution():
    ref_id = "refunds.settlement_sla"
    b = ev("SRC-01", "brd", ref_id, {"sla_hours": 72, "instant_settlement": False})
    s = ev("SRC-02", "screenshot", ref_id, {"sla_hours": 24, "instant_settlement": True})
    n = ev("SRC-03", "client_note", ref_id, {"sla_hours": 24, "instant_settlement": True}, scope=True)

    # Dispute
    res_disputed = resolve(ref_id, activate(b, s))
    assert res_disputed.state == "DISPUTED"
    assert not res_disputed.in_brd

    # Governed
    res_governed = resolve(ref_id, activate(b, s, n))
    assert res_governed.state == "GOVERNED"
    assert res_governed.in_brd
    assert "24 hours" in res_governed.requirement
    assert "Instant automated settlement" in res_governed.requirement
