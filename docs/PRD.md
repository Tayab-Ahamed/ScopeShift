# ScopeShift — Product Requirements Document

**Tagline:** Evidence-Governed BRD Generation **Event:** Hack Sprint (PS42), Manipal Bengaluru, 17–18 Oct 2026 **Status:** Spec frozen. No feature expansion.

---

## 1. Overview

ScopeShift converts fragmented PDFs, screenshots and client notes into a traceable BRD. It refuses to turn conflicting evidence into a requirement until an explicit client scope decision governs it. If that decision is withdrawn, it re-evaluates the remaining evidence and changes the current BRD accordingly.

**Thesis:** Gemini understands the evidence. Deterministic governance decides what that evidence is allowed to become. **Memorable line:** "Seeing a button is not approving the button."

## 2. Problem

Requirements for one feature are spread across sources that disagree: a BRD says "Checkout accepts UPI only", a screenshot shows a Card button, a later client note says "Card is in scope. UPI moves to Phase 2." Extracting the statements is easy. Deciding what is *allowed* to become a requirement is the problem.

## 3. Goals / Non-goals

**Goals**

- G1. Extract structured evidence from PDF, image and text with Gemini.
- G2. Detect claim-level contradictions deterministically.
- G3. Grant authority only through a verified, explicit client scope decision.
- G4. Keep an append-only evidence history; derive the current BRD from it.
- G5. Demonstrate DISPUTED → GOVERNED → DISPUTED live.

**Non-goals (frozen)** RAG, vector DB, embeddings, knowledge graph, multi-agent system, payment APIs, GST, multiple business domains, enterprise-scale BRD, confidence scores, scale benchmarks, human-override subsystem, requirement lifecycle platform, role/permission engine, Vertex AI (unless a working call is actually used).

## 4. Users

- **Primary (demo):** a business analyst reconciling BRD, UI and client communication.
- **Secondary:** hackathon judges, who must see state changes and the reason for each.

## 5. Sources and authority

| Source | Role | Can grant authority? |
| --- | --- | --- |
| BRD (PDF) | Documented baseline | No |
| Screenshot | Observation of UI state | Never |
| Client note | Governing decision only if it explicitly changes scope | Yes, after code validation |

"Maybe we should consider cards", "Looks good 👍" and "The button looks nice" are evidence only.

## 6. Functional requirements

**Ingestion**

- FR-1. Store originals (PDF, PNG, TXT) in Cloud Storage.
- FR-2. The pipeline assigns `source_id` (SRC-01…) and knows `source_type`. Gemini never generates either.
- FR-3. Gemini returns structured output constrained to an enum of `claim_id` (`checkout.payment_methods`, `checkout.currency`), with `observation`, `quote`, `proposed_scope_change` and claim value.
- FR-4. Extraction runs once per source and is persisted. Replay never calls Gemini.

**Validation (code)**

- FR-5. Text sources (BRD text, client note): the quote must exist in the extracted text.
- FR-6. Screenshot: the cited crop/region must exist in the image. This does not prove the crop contains the stated element, and screenshots can never grant authority.
- FR-7. `GOVERNING` is assigned only if: `proposed_scope_change` is true AND quote verified AND `source_type == client_note` AND `claim_id` is allowed. Otherwise the evidence is `OBSERVATION`/evidence.
- FR-8. Every citation in the current BRD must reference an existing, active evidence record; otherwise reject.

**Event log**

- FR-9. Events are `ADDED` and `REMOVED`, as `(event_sequence, source_id, event)`. `decision` lives on the evidence record.
- FR-10. A single ingestion writer assigns monotonically increasing `event_sequence`. Ordering is by sequence, not timestamp.
- FR-11. State machine: UNKNOWN → ADDED → REMOVED. Reject REMOVED on an unknown source, REMOVED on an already-removed source, and duplicate ADDED.
- FR-12. Append-only by application design: INSERT only, no UPDATE or DELETE.

**Resolver**

- FR-13. `resolve(claim_id, active_evidence[])` is generic and keyed on `claim_id`, not on payments.
- FR-14. *Contradiction:* BRD `exclusive=true, methods={UPI}` and an observed method not in the set gives CONTRADICTS. If `exclusive=false` or Card is in `methods`, there is no contradiction.
- FR-15. *Supersession:* an active governing decision on the same `claim_id` that conflicts with an earlier claim SUPERSEDES it, giving GOVERNED.
- FR-16. *Multiple governing decisions:* the later active decision by `event_sequence` wins.
- FR-17. *Withdrawal:* after REMOVED, recompute from remaining active evidence. If it conflicts, the state is DISPUTED and the requirement leaves the current BRD. This is resolver output, not a database event.
- FR-18. Invariant: no requirement enters the current BRD unless its claim resolves from currently active evidence and every citation exists.

**Output**

- FR-19. The current BRD is a projection of resolver state. GOVERNED shows the requirement, business rule, governing source and superseded source. DISPUTED shows "requirement withheld" and the reason.
- FR-20. For each requirement answer: what, why, source, what it replaced, why it disappeared.

## 7. Demo (acceptance scenario)

1. **Beat 1:** BRD + screenshot → 🔴 DISPUTED, no Card requirement in the BRD.
2. **Beat 2:** add client note → Gemini proposes, code validates → 🟢 GOVERNED: "Checkout shall support Card payments. UPI → Phase 2." Source: Client Note #01. Supersedes: BRD p.2.
3. **Beat 3:** append `SRC-03 REMOVED` (no Gemini call) → 🔴 DISPUTED, requirement withheld.

**Acceptance tests**

- AT-1. Beats 1–3 produce DISPUTED, GOVERNED, DISPUTED from the stored log alone.
- AT-2. "Looks good 👍" does not become GOVERNING.
- AT-3. BRD with `exclusive=false` plus a Card screenshot gives no contradiction.
- AT-4. Hallucinated `claim_id` is outside the output schema; unknown quote is rejected.
- AT-5. Invalid event transitions (FR-11) are rejected.
- AT-6. Replaying the same log twice yields identical state.

## 8. UI (one screen)

Three panels (Sources | Evidence | Current BRD) plus a timeline. The state transition and its reason are the priority. No dashboards, login or analytics.

## 9. Architecture

Cloud Storage (originals) → Gemini (structured extraction) → persisted evidence → validation → append-only events in BigQuery → deterministic resolver → current BRD.

- BigQuery wording: "append-only by application design, insert-only access." Never "immutable" or "tamper-proof."
- Live demo reads through an in-memory mirror of the log (or batch loads) to avoid streaming-visibility lag. In Q&A: "BigQuery is the persisted append-only log. The demo reads through an in-memory mirror of it."
- Beat 2 attempts a live Gemini call on the client note, with the pre-extracted result ready as a one-click fallback if latency or availability becomes a stage risk.

## 10. Baseline experiment (before Slide 4)

`baseline.py`, 10 independent runs per test, API-default temperature.

- Test A: BRD + screenshot + note. Correct = Card settled in scope.
- Test B: BRD + screenshot. Correct = conflict flagged. Settling on Card or UPI-only is wrong.
- Conditions: **plain** (primary baseline) and **hinted** (prompt states the governance rule). Optional `--temperature 0` run kept separate.
- Record: correct counts, outcome distribution, distinct requirement wordings, valid / invalid / screenshot-unverifiable citations, errors. Keep `runs.jsonl` unedited.
- Report only measured results. If Gemini scores 10/10, differentiate on persisted evidence, validated provenance, deterministic authority, append-only history and replay without re-calling Gemini.

## 11. Slides

1. Problem / solution: ScopeShift
2. DISPUTED → GOVERNED → DISPUTED
3. How it works (architecture): Evidence → BigQuery append-only event log → Resolver → Current BRD
4. Measured baseline (plain vs hinted)

## 12. Claims policy

- Say: "produces governed requirements according to explicit, auditable rules"; "new evidence enters the same extraction, evidence and resolution pipeline."
- Don't say: "accurate", "immutable", "tamper-proof", "enterprise-scale", "scales to millions", "deterministic" about Gemini output.

## 13. Risks

| Risk | Mitigation |
| --- | --- |
| Gemini extracts wrongly (e.g. `exclusive`) | Test wording variants; report extraction accuracy separately |
| Live Gemini call fails on stage | Pre-extracted fallback |
| BigQuery visibility lag in Beat 3 | In-memory mirror / batch load |
| Pre-building violates hackathon rules | Confirm with organizers; build in the 24h window |
| Judge: "just if-statements" | Generic `resolve(claim_id, evidence[])` plus a second harmless claim in the log |

## 14. Proposed build order

Fixtures → extraction schema → resolver with a test per rule → citation validation → append-only events → one-screen UI → baseline → recorded demo → slides and Q&A.
