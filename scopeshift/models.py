"""Domain records shared by validation, resolver and store."""
from __future__ import annotations

from dataclasses import dataclass, field

from .claims import SPECS


@dataclass(frozen=True)
class Evidence:
    source_id: str
    source_type: str
    claim_id: str
    value: dict
    quote: str
    observation: str = ""
    proposed_scope_change: bool = False
    quote_verified: bool = False
    region: tuple | None = None
    event_sequence: int = 0
    active: bool = False
    sender: str | None = None
    channel: str | None = None
    received_at: str | None = None

    @property
    def governing(self) -> bool:
        """FR-7: only a verified client-note scope change on a governable claim from an authorized sender can govern."""
        from .approvers import is_sender_allowlisted
        spec = SPECS.get(self.claim_id)
        if not (
            self.proposed_scope_change
            and self.quote_verified
            and self.source_type == "client_note"
            and spec is not None
            and spec.governable
        ):
            return False
        if self.sender is not None:
            return is_sender_allowlisted(self.sender, self.channel)
        return True


@dataclass(frozen=True)
class Event:
    event_sequence: int
    source_id: str
    event: str
    sender: str | None = None
    channel: str | None = None
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Resolution:
    claim_id: str
    state: str                       # GOVERNED | CONSISTENT | DISPUTED | UNKNOWN
    requirement: str | None = None
    rule: str | None = None
    basis: str | None = None         # client_decision | brd_baseline | None
    governing_source: str | None = None
    superseded_sources: list = field(default_factory=list)
    replaced_requirement: str | None = None
    citations: list = field(default_factory=list)
    reason: str = ""
    disappeared: dict | None = None

    @property
    def in_brd(self) -> bool:
        return self.state in ("GOVERNED", "CONSISTENT")

    def to_dict(self) -> dict:
        title = SPECS[self.claim_id].title if self.claim_id in SPECS else self.claim_id
        return {
            "claim_id": self.claim_id, "title": title, "state": self.state, "in_brd": self.in_brd,
            "requirement": self.requirement, "rule": self.rule, "basis": self.basis,
            "governing_source": self.governing_source, "superseded_sources": list(self.superseded_sources),
            "replaced_requirement": self.replaced_requirement, "citations": list(self.citations),
            "reason": self.reason, "disappeared": self.disappeared,
        }
