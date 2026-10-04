"""Small deterministic ScopeShift resolver used for the pre-build test."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Evidence:
    source_id: str
    source_type: str
    claim_id: str
    value: object
    quote: str
    proposed_scope_change: bool = False
    quote_verified: bool = False
    event_sequence: int = 0
    active: bool = True

    @property
    def governing(self) -> bool:
        return (
            self.proposed_scope_change
            and self.quote_verified
            and self.source_type == "client_note"
            and self.claim_id in {"checkout.payment_methods", "checkout.currency"}
        )


@dataclass(frozen=True)
class Event:
    event_sequence: int
    source_id: str
    event: str


def resolve_payment_methods(evidence: Iterable[Evidence]) -> dict:
    active = [e for e in evidence if e.active and e.claim_id == "checkout.payment_methods"]
    governing = sorted((e for e in active if e.governing), key=lambda e: e.event_sequence)
    if governing:
        winner = governing[-1]
        return {
            "state": "GOVERNED",
            "requirement": winner.value,
            "governing_source": winner.source_id,
            "superseded_source": "SRC-01",
            "reason": "An explicit, verified client scope decision governs the claim.",
        }

    brd = next((e for e in active if e.source_type == "brd"), None)
    observations = [e for e in active if e.source_type == "screenshot"]
    contradiction = bool(
        brd and brd.value.get("exclusive") and any(
            method not in brd.value.get("methods", [])
            for obs in observations
            for method in obs.value.get("methods", [])
        )
    )
    if contradiction:
        return {
            "state": "DISPUTED",
            "requirement": None,
            "governing_source": None,
            "superseded_source": None,
            "reason": "The screenshot shows Card while the BRD allows UPI only; no governing decision is active.",
        }
    return {
        "state": "GOVERNED",
        "requirement": brd.value if brd else None,
        "governing_source": brd.source_id if brd else None,
        "superseded_source": None,
        "reason": "No active contradiction exists.",
    }


def replay(evidence: list[Evidence], events: list[Event]) -> dict:
    active = {e.source_id: e for e in evidence}
    for event in sorted(events, key=lambda e: e.event_sequence):
        if event.event == "ADDED":
            if event.source_id not in active or active[event.source_id].active:
                raise ValueError(f"invalid ADDED transition: {event.source_id}")
            active[event.source_id] = Evidence(**{**active[event.source_id].__dict__, "active": True})
        elif event.event == "REMOVED":
            if event.source_id not in active or not active[event.source_id].active:
                raise ValueError(f"invalid REMOVED transition: {event.source_id}")
            active[event.source_id] = Evidence(**{**active[event.source_id].__dict__, "active": False})
        else:
            raise ValueError(f"unknown event: {event.event}")
    return resolve_payment_methods(active.values())
