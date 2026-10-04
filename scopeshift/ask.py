"""Deterministic evidence Q&A (Stream D: "Ask the evidence").

answer_question(snapshot, question) answers strictly from the live snapshot —
resolutions, sources, events, timeline. No LLM is involved anywhere: the facts
and the citations are computed, never generated. (If extraction ever runs in
"live" mode that only changes how evidence was extracted; answers stay
deterministic.)

Every citation returned is a real source_id whose quote is copied verbatim
from the snapshot. Unknown questions get an honest fallback that lists what
can be asked — never a fabricated answer.
"""
from __future__ import annotations

import re

MODE = "deterministic"

_CLAIM_KEYWORDS = {
    "checkout.payment_methods": ("payment", "payments", "card", "upi", "checkout", "method", "methods"),
    "checkout.currency": ("currency", "inr", "usd", "rupee", "dollar", "price", "prices"),
    "auth.mfa_requirement": ("mfa", "multi-factor", "multifactor", "auth", "authentication", "login", "logins"),
    "refunds.settlement_sla": ("refund", "refunds", "sla", "settlement"),
}

_FALLBACK = (
    "I can only answer from the current evidence snapshot — I won't guess beyond it. "
    "Try asking: 'Why is the payment claim disputed?', 'What governs the payment methods claim?', "
    "'What evidence do we have?', 'What disappeared?', 'List claims', or 'Summarize the current state'."
)

_WS = re.compile(r"\s+")


def _clean(text: str) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


def match_claims(question: str, claim_ids) -> list[str]:
    """Claim ids referenced by the question: literal id match or keyword hit."""
    q = _clean(question)
    hits = []
    for cid in claim_ids:
        if cid.lower() in q:
            hits.append(cid)
            continue
        for kw in _CLAIM_KEYWORDS.get(cid, ()):
            if re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", q):
                hits.append(cid)
                break
    return hits


def _sources_by_id(snapshot: dict) -> dict:
    return {s["id"]: s for s in snapshot.get("sources", [])}


def _citations(resolution: dict, sources_by_id: dict) -> list[dict]:
    """Only citations that reference a real source record in the snapshot."""
    out = []
    for c in resolution.get("citations") or []:
        sid = c.get("source_id")
        src = sources_by_id.get(sid)
        if src:
            out.append({"source_id": sid, "quote": src["quote"]})
    return out


def _cite_sources(sources: list[dict]) -> list[dict]:
    return [{"source_id": s["id"], "quote": s["quote"]} for s in sources]


def _pick_default_claim(snapshot: dict) -> str | None:
    """Deterministic fallback claim when the question names none: the most
    contested one — first DISPUTED, else first GOVERNED, else first claim."""
    res = snapshot.get("resolutions", {})
    for state in ("DISPUTED", "GOVERNED", "CONSISTENT", "UNKNOWN"):
        for cid, r in res.items():
            if r.get("state") == state:
                return cid
    return None


def _title(snapshot: dict, cid: str) -> str:
    r = snapshot.get("resolutions", {}).get(cid, {})
    return r.get("title") or cid


def _answer_why(snapshot: dict, cid: str, sources_by_id: dict) -> dict:
    r = snapshot["resolutions"][cid]
    title = _title(snapshot, cid)
    answer = f"The {title} claim ({cid}) is {r.get('state')}. {r.get('reason', '').strip()}"
    return {"answer": answer, "citations": _citations(r, sources_by_id), "mode": MODE}


def _answer_governs(snapshot: dict, cid: str, sources_by_id: dict) -> dict:
    r = snapshot["resolutions"][cid]
    title = _title(snapshot, cid)
    gov = r.get("governing_source")
    if gov and r.get("state") == "GOVERNED":
        src = sources_by_id.get(gov, {})
        answer = (f"{title} is governed by {gov}: \"{src.get('quote', '')}\". "
                  f"{r.get('reason', '').strip()}")
    else:
        answer = (f"Nothing governs {title} right now — the claim is {r.get('state')}. "
                  f"{r.get('reason', '').strip()}")
    return {"answer": answer, "citations": _citations(r, sources_by_id), "mode": MODE}


def _answer_disappeared(snapshot: dict, cids: list[str], sources_by_id: dict) -> dict:
    parts, cites = [], []
    for cid in cids:
        r = snapshot["resolutions"][cid]
        title = _title(snapshot, cid)
        d = r.get("disappeared")
        if d:
            parts.append(
                f"The {title} requirement disappeared at event #{d['event_sequence']}: "
                f"{d['source_id']} was {d['event']}. "
                f"Previously in the BRD: \"{d.get('previous_requirement')}\".")
            src = sources_by_id.get(d["source_id"])
            if src:
                cites.append({"source_id": src["id"], "quote": src["quote"]})
        else:
            parts.append(f"No disappearance recorded for {title} — it is {r.get('state')}.")
        cites.extend(_citations(r, sources_by_id))
    seen, uniq = set(), []
    for c in cites:
        if c["source_id"] not in seen:
            seen.add(c["source_id"])
            uniq.append(c)
    return {"answer": " ".join(parts), "citations": uniq[:8], "mode": MODE}


def _answer_evidence(snapshot: dict) -> dict:
    sources = snapshot.get("sources", [])
    if not sources:
        return {"answer": "The snapshot contains no evidence sources yet.", "citations": [], "mode": MODE}
    lines = []
    for s in sources:
        flag = "ACTIVE" if s.get("active") else "WITHDRAWN"
        ver = "verified" if s.get("quote_verified") else "unverified"
        lines.append(f"{s['id']} ({s['type']}, {flag}, quote {ver}): \"{s['quote']}\"")
    answer = "Evidence in the current snapshot: " + " ".join(lines)
    return {"answer": answer, "citations": _cite_sources(sources)[:8], "mode": MODE}


def _answer_list_claims(snapshot: dict, sources_by_id: dict) -> dict:
    res = snapshot.get("resolutions", {})
    if not res:
        return {"answer": "No claims are registered.", "citations": [], "mode": MODE}
    parts = [f"{_title(snapshot, cid)} ({cid}): {r.get('state')}" for cid, r in res.items()]
    answer = f"{len(res)} registered claims. " + " ".join(parts) + "."
    cites = []
    for cid, r in res.items():
        cites.extend(_citations(r, sources_by_id))
    seen, uniq = set(), []
    for c in cites:
        if c["source_id"] not in seen:
            seen.add(c["source_id"])
            uniq.append(c)
    return {"answer": answer, "citations": uniq[:8], "mode": MODE}


def _answer_summarize(snapshot: dict, sources_by_id: dict) -> dict:
    res = snapshot.get("resolutions", {})
    counts: dict[str, int] = {}
    for r in res.values():
        counts[r.get("state", "?")] = counts.get(r.get("state", "?"), 0) + 1
    tally = ", ".join(f"{n} {s}" for s, n in sorted(counts.items()))
    detail = " ".join(
        f"{_title(snapshot, cid)}: {r.get('state')} — {(r.get('requirement') or r.get('reason') or '').strip()[:140]}"
        for cid, r in res.items())
    answer = (f"Current snapshot: {len(res)} claims ({tally}). "
              f"{len(snapshot.get('events', []))} events in the append-only log. {detail}")
    cites = []
    for r in res.values():
        cites.extend(_citations(r, sources_by_id))
    seen, uniq = set(), []
    for c in cites:
        if c["source_id"] not in seen:
            seen.add(c["source_id"])
            uniq.append(c)
    return {"answer": answer, "citations": uniq[:8], "mode": MODE}


def answer_question(snapshot: dict, question: str) -> dict:
    """Deterministic answer over a store snapshot. Raises ValueError on empty questions."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    q = _clean(question)
    claim_ids = list(snapshot.get("resolutions", {}).keys())
    sources_by_id = _sources_by_id(snapshot)
    matched = match_claims(question, claim_ids)

    # 1. disappearances — checked first so "why did X disappear" doesn't hit the why-state rule
    if re.search(r"disappear|withdrawn|revok|removed|drop(?:ped)? out|went away|withheld", q):
        cids = matched or ([_pick_default_claim(snapshot)] if _pick_default_claim(snapshot) else [])
        if cids:
            return _answer_disappeared(snapshot, cids, sources_by_id)

    # 2. why is X in its state
    if re.search(r"\bwhy\b|withheld|conflict", q):
        cid = matched[0] if matched else _pick_default_claim(snapshot)
        if cid:
            note = "" if matched else f"(Your question named no claim, so I answered for {_title(snapshot, cid)}.) "
            ans = _answer_why(snapshot, cid, sources_by_id)
            ans["answer"] = note + ans["answer"]
            return ans

    # 3. what/who governs or authorized
    if re.search(r"govern|authoriz|approv|authority|who decided|basis", q):
        cid = matched[0] if matched else _pick_default_claim(snapshot)
        if cid:
            return _answer_governs(snapshot, cid, sources_by_id)

    # 4. evidence / sources / citations
    if re.search(r"evidence|sources?|artifacts?|citations?|ingested", q):
        return _answer_evidence(snapshot)

    # 5. list claims
    if re.search(r"list.*claims|which claims|all claims|claims\?", q):
        return _answer_list_claims(snapshot, sources_by_id)

    # 6. summary of state
    if re.search(r"summar|overall|state of|status|how (are|is) things|current state", q):
        return _answer_summarize(snapshot, sources_by_id)

    return {"answer": _FALLBACK, "citations": [], "mode": MODE}
