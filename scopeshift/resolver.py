"""Generic deterministic resolver and event replay (FR-9..FR-20). No I/O, no model calls."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .claims import SPECS
from .models import Event, Evidence, Resolution

EVENTS = ("ADDED", "REMOVED")


def _cite(e: Evidence, role: str) -> dict:
    return {"source_id": e.source_id, "source_type": e.source_type, "quote": e.quote, "role": role}


def resolve(claim_id: str, evidence) -> Resolution:
    """resolve(claim_id, active_evidence[]) is generic: it only consults the claim registry.

    Unverified evidence is displayed elsewhere but never participates in resolution."""
    spec = SPECS[claim_id]
    active = [e for e in evidence if e.active and e.claim_id == claim_id and e.quote_verified]
    if not active:
        return Resolution(claim_id, "UNKNOWN", reason="No active, verified evidence for this claim.")
    order = lambda e: (e.event_sequence, e.source_id)

    governing = sorted((e for e in active if e.governing), key=order)
    brds = sorted((e for e in active if e.source_type == "brd"), key=order)
    baseline = brds[-1] if brds else None

    if governing:  # FR-15/16: the later active decision by event_sequence wins
        win = governing[-1]
        superseded = [b for b in brds if spec.conflicts(b.value, win.value)]
        cites = [_cite(win, "governing")] + [_cite(b, "superseded") for b in superseded]
        return Resolution(
            claim_id, "GOVERNED", spec.render(win.value),
            "Explicit client scope decision overrides the earlier baseline.", "client_decision", win.source_id,
            [b.source_id for b in superseded], spec.render(superseded[-1].value) if superseded else None, cites,
            f"{win.source_id} is a verified client scope decision and governs this claim.")

    observations = [e for e in active if e.source_type != "brd"]
    if baseline is None:
        return Resolution(
            claim_id, "UNKNOWN", citations=[_cite(e, "observation") for e in observations],
            reason="No BRD baseline and no governing client decision: observations alone cannot authorize a requirement.")

    clashing = [o for o in observations if spec.conflicts(baseline.value, o.value)]
    if clashing:  # FR-14
        seen = ", ".join(f"{o.source_id} ({o.source_type})" for o in clashing)
        return Resolution(
            claim_id, "DISPUTED", citations=[_cite(baseline, "baseline")] + [_cite(o, "conflicting") for o in clashing],
            reason=f"{seen} conflicts with BRD {baseline.source_id}: \"{spec.render(baseline.value)}\" "
                   "No verified client decision is active, so the requirement is withheld.")

    return Resolution(
        claim_id, "CONSISTENT", spec.render(baseline.value), spec.rule(baseline.value), "brd_baseline",
        baseline.source_id, [], None,
        [_cite(baseline, "baseline")] + [_cite(o, "corroborating") for o in observations],
        "BRD baseline stands: no active evidence contradicts it.")


def _apply(evidence_all, events):
    """State machine UNKNOWN -> ADDED -> REMOVED (FR-11). Returns active-state evidence list."""
    known = {e.source_id for e in evidence_all}
    status, added_at, last = {}, {}, 0
    for ev in sorted(events, key=lambda e: e.event_sequence):
        if ev.event not in EVENTS:
            raise ValueError(f"unknown event: {ev.event!r}")
        if ev.source_id not in known:
            raise ValueError(f"event for unknown source: {ev.source_id}")
        if not isinstance(ev.event_sequence, int) or ev.event_sequence <= last:
            raise ValueError(f"event_sequence must be strictly increasing (got {ev.event_sequence})")
        last = ev.event_sequence
        current = status.get(ev.source_id)
        if ev.event == "ADDED":
            if current is not None:
                raise ValueError(f"invalid ADDED transition for {ev.source_id}: already {current}")
            status[ev.source_id], added_at[ev.source_id] = "ADDED", ev.event_sequence
        else:
            if current != "ADDED":
                raise ValueError(f"invalid REMOVED transition for {ev.source_id}: state is {current or 'UNKNOWN'}")
            status[ev.source_id] = "REMOVED"
    return [replace(e, active=status.get(e.source_id) == "ADDED", event_sequence=added_at.get(e.source_id, 0))
            for e in evidence_all]


def _resolve_all(evidence):
    return {cid: resolve(cid, evidence) for cid in SPECS}


@dataclass
class ReplayResult:
    resolutions: dict
    active_evidence: list
    timeline: list

    def snapshot(self) -> dict:
        return {"resolutions": {k: v.to_dict() for k, v in self.resolutions.items()}, "timeline": self.timeline}


def replay(evidence_all, events) -> ReplayResult:
    events = sorted(events, key=lambda e: e.event_sequence)
    evidence_all = list(evidence_all)
    final_evidence = _apply(evidence_all, events)  # raises on any invalid transition
    types = {e.source_id: e.source_type for e in evidence_all}

    def step(seq, source_id, kind, res):
        return {"sequence": seq, "source_id": source_id, "event": kind,
                "claims": {c: {"state": r.state, "in_brd": r.in_brd, "requirement": r.requirement}
                           for c, r in res.items()}}

    timeline = [step(0, None, "START", _resolve_all(_apply(evidence_all, [])))]
    for n, ev in enumerate(events, start=1):
        res = _resolve_all(_apply(evidence_all, events[:n]))
        timeline.append(step(ev.event_sequence, ev.source_id, ev.event, res))

    resolutions = _resolve_all(final_evidence)
    for cid, res in list(resolutions.items()):  # FR-17/FR-20: why did the requirement disappear?
        if res.in_brd:
            continue
        for prev, cur in zip(reversed(timeline[:-1]), reversed(timeline[1:])):
            if prev["claims"][cid]["in_brd"] and not cur["claims"][cid]["in_brd"]:
                who = f"{cur['source_id']} ({types.get(cur['source_id'], '?')})"
                verb = "withdrawn" if cur["event"] == "REMOVED" else "withheld"
                detail = (f"Requirement {verb}: {who} was {cur['event']} at event {cur['sequence']}. "
                          f"Previously in the BRD: \"{prev['claims'][cid]['requirement']}\" ")
                resolutions[cid] = replace(res, reason=detail + res.reason, disappeared={
                    "event_sequence": cur["sequence"], "source_id": cur["source_id"], "event": cur["event"],
                    "previous_state": prev["claims"][cid]["state"],
                    "previous_requirement": prev["claims"][cid]["requirement"]})
                break
    return ReplayResult(resolutions, final_evidence, timeline)
