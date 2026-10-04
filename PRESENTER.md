# ScopeShift — Stage Presenter Runbook

**One rule for the whole demonstration: trigger stages in order 1 → 2 → 3.** Stage 1 always re-seeds, so
you can run the sequence as many times as you like. Re-pressing an already-applied stage is an
honest no-op — the UI tells you ("press 1 to re-seed, then 2") instead of silently doing nothing.

## Before you present

1. `python demo_server.py` → open http://localhost:8765
2. Extraction status pill (top-right of the lifecycle navigator) reads:
   **"EXTRACTION: DETERMINISTIC PIPELINE (VERIFIED)"**
   *(or "EXTRACTION: GEMINI MULTI-MODAL" if live GEMINI_API_KEY is supplied).*
3. Keyboard shortcuts: **1**, **2**, **3** = stages (**Esc** closes modals/toasts, **?** opens stage keys).

## The 3-Stage Story (What to say)

### STAGE 1 — Conflict Detected → DISPUTED
**Press `1`.** Seeds SRC-01 (BRD: "UPI only") + SRC-02 (screenshot: Card button visible).
> *"The BRD says UPI only. Staging shows a Card button. Two sources disagree — so ScopeShift
> withholds the requirement. Seeing a button is not approving the button."*

### STAGE 2 — Client Authorizes → GOVERNED
**Press `2`.** Runs the extraction pipeline, validates
every claim in code, then appends SRC-03 (client note: "Card in scope, UPI to Phase 2").
The response shows the extraction outcome: claims, per-claim validation, and the real mode.
> *"Now the client explicitly authorizes the change. The quote is verified against the source
> text, a verified client decision governs — and the BRD updates with the governing citation
> and the superseded baseline recorded."*

### STAGE 3 — Scope Withdrawn → DISPUTED (reason retained)
**Press `3`.** Appends SRC-03 REMOVED. The requirement disappears but the explanation stays.
> *"The client withdraws the decision. The requirement drops out of the BRD — but the audit
> trail keeps the full story: who withdrew it, when, and what it used to say."*

## Chaos tiles (page 5, "Adversarial Stress Test Suite")

Three real attacks, each executed through the actual `validate_claim` boundary — nothing canned:

| Tile | Attack | Rule that fires |
|------|--------|-----------------|
| TEST 1 Forged Screenshot | screenshot with `proposed_scope_change=true` | Boundary forces it to `false` — screenshots can NEVER govern |
| TEST 2 Vague Note | "Maybe consider Card?" with an unverifiable quote | Quote verification fails → classified OBSERVATION only |
| TEST 3 Hallucinated Claim ID | `checkout.bitcoin` | Schema enum rejects it before the event log |

The toast shows the rule fired + resulting classification for each. Point at it: *"The attacker
never reaches the log — the code boundary intercepts them first."*

## Recovery

- **Wrong order / double-press:** you get a "no-op" toast with the hint. Press **1** to re-seed,
  then continue 1 → 2 → 3.
- **Something looks off:** the **Reset** button (or POST `/api/demo/reset`) rebuilds the seed.
- **Time-travel scrubber** (page 5): drag to any sequence number to replay the exact historical state.

## Lines to avoid on stage

- ❌ "Live Gemini extraction" (unless `GEMINI_API_KEY` is actually set)
- ❌ "BigQuery" (the append-only log in this demo is SQLite)
- ❌ "The AI decided" — always: *"Gemini proposes claims; code validates citations and decides authority."*
