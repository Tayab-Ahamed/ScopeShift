"""Claim registry: the only place that knows what a claim_id means.

The resolver is generic over this registry. Adding a claim is adding a ClaimSpec, not an if-branch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class ClaimValueError(ValueError):
    pass


@dataclass(frozen=True)
class ClaimSpec:
    claim_id: str
    title: str
    normalize: Callable[[object], dict]          # raises ClaimValueError on bad shape
    conflicts: Callable[[dict, dict], bool]      # (baseline_value, observed_value) -> bool
    render: Callable[[dict], str]                # value -> requirement sentence
    rule: Callable[[dict], str]                  # value -> business rule sentence
    governable: bool = True                      # may a client scope decision govern it?


def _str_list(raw, field: str, *, required: bool) -> list[str]:
    if raw is None and not required:
        return []
    if not isinstance(raw, list) or (required and not raw):
        raise ClaimValueError(f"{field} must be a non-empty list of strings")
    out = []
    for item in raw:
        if not isinstance(item, str) or not item.strip() or len(item) > 40:
            raise ClaimValueError(f"{field} entries must be short non-empty strings")
        out.append(item.strip())
    return out


_CANON = {"upi": "UPI", "card": "Card", "cards": "Card", "credit card": "Card", "debit card": "Card"}


def _canon_method(name: str) -> str:
    return _CANON.get(name.lower(), name)


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _norm_payment(value) -> dict:
    if not isinstance(value, dict):
        raise ClaimValueError("value must be an object")
    methods = [_canon_method(m) for m in _str_list(value.get("methods"), "methods", required=True)]
    out = {"methods": sorted(set(methods), key=methods.index)}
    if "exclusive" in value:
        if not isinstance(value["exclusive"], bool):
            raise ClaimValueError("exclusive must be a boolean")
        out["exclusive"] = value["exclusive"]
    deferred = [_canon_method(m) for m in _str_list(value.get("deferred"), "deferred", required=False)]
    if deferred:
        out["deferred"] = deferred
    return out


def _lower(items) -> set[str]:
    return {i.lower() for i in items}


def _payment_conflicts(baseline: dict, observed: dict) -> bool:
    return bool(baseline.get("exclusive")) and bool(_lower(observed.get("methods", [])) - _lower(baseline.get("methods", [])))


def _payment_render(value: dict) -> str:
    text = f"Checkout shall support {_join(value['methods'])} payments" + (" only." if value.get("exclusive") else ".")
    for d in value.get("deferred", []):
        text += f" {d} moves to Phase 2."
    return text


def _payment_rule(value: dict) -> str:
    if value.get("exclusive"):
        return f"{_join(value['methods'])} is the exclusive payment method; no other method is in scope."
    return f"{_join(value['methods'])} supported; the list is not declared exclusive."


def _norm_currency(value) -> dict:
    if not isinstance(value, dict):
        raise ClaimValueError("value must be an object")
    cur = value.get("currency")
    if not isinstance(cur, str) or len(cur.strip()) != 3 or not cur.strip().isalpha():
        raise ClaimValueError("currency must be a 3-letter code")
    return {"currency": cur.strip().upper()}


_MFA_CANON = {"totp": "TOTP Authenticator", "sms": "SMS OTP", "email": "Email OTP", "hardware_key": "Security Key", "biometric": "Biometrics"}


def _canon_mfa(name: str) -> str:
    return _MFA_CANON.get(name.lower(), name)


def _norm_mfa(value) -> dict:
    if not isinstance(value, dict):
        raise ClaimValueError("value must be an object")
    if "mfa_required" not in value or not isinstance(value["mfa_required"], bool):
        raise ClaimValueError("mfa_required must be a boolean")
    channels = [_canon_mfa(m) for m in _str_list(value.get("channels"), "channels", required=False)]
    return {"mfa_required": value["mfa_required"], "channels": channels or ["TOTP Authenticator"]}


def _mfa_conflicts(baseline: dict, observed: dict) -> bool:
    return baseline.get("mfa_required") != observed.get("mfa_required")


def _mfa_render(value: dict) -> str:
    if value.get("mfa_required"):
        ch = _join(value.get("channels", ["TOTP Authenticator"]))
        return f"User authentication shall enforce mandatory Multi-Factor Authentication (MFA) via {ch}."
    return "User authentication shall permit single-factor password authentication without mandatory MFA."


def _mfa_rule(value: dict) -> str:
    if value.get("mfa_required"):
        return "MFA mandate enforced for all checkout and account operations."
    return "Single-factor baseline active; MFA optional."


def _norm_refund(value) -> dict:
    if not isinstance(value, dict):
        raise ClaimValueError("value must be an object")
    sla = value.get("sla_hours")
    if not isinstance(sla, (int, float)) or sla <= 0:
        raise ClaimValueError("sla_hours must be a positive number")
    instant = value.get("instant_settlement", False)
    if not isinstance(instant, bool):
        raise ClaimValueError("instant_settlement must be a boolean")
    return {"sla_hours": int(sla), "instant_settlement": instant}


def _refund_conflicts(baseline: dict, observed: dict) -> bool:
    return (baseline.get("sla_hours") != observed.get("sla_hours")) or (baseline.get("instant_settlement") != observed.get("instant_settlement"))


def _refund_render(value: dict) -> str:
    text = f"Refund requests shall settle within {value['sla_hours']} hours."
    if value.get("instant_settlement"):
        text += " Instant automated settlement is enabled."
    return text


def _refund_rule(value: dict) -> str:
    return f"Customer settlement SLA guaranteed at {value['sla_hours']}h window."


SPECS: dict[str, ClaimSpec] = {
    "checkout.payment_methods": ClaimSpec(
        "checkout.payment_methods", "Payment methods", _norm_payment, _payment_conflicts,
        _payment_render, _payment_rule),
    "checkout.currency": ClaimSpec(
        "checkout.currency", "Currency", _norm_currency,
        lambda b, o: b["currency"] != o["currency"],
        lambda v: f"All prices shall be shown and charged in {v['currency']}.",
        lambda v: f"A single currency ({v['currency']}) applies across checkout."),
    "auth.mfa_requirement": ClaimSpec(
        "auth.mfa_requirement", "Multi-Factor Authentication", _norm_mfa, _mfa_conflicts,
        _mfa_render, _mfa_rule),
    "refunds.settlement_sla": ClaimSpec(
        "refunds.settlement_sla", "Refund Settlement SLA", _norm_refund, _refund_conflicts,
        _refund_render, _refund_rule),
}

CLAIM_IDS = tuple(SPECS)
SOURCE_TYPES = ("brd", "screenshot", "client_note")
