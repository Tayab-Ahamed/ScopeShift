# ScopeShift Enterprise

> **"Seeing a button is not approving the button."**  
> *From conflicting evidence to governed requirements.*

ScopeShift is an evidence-governed BRD generator and requirements authority engine. It extracts claims from documents and screenshots, validates citations, detects contradictions, and only promotes a requirement when an explicit client scope decision authorizes it.

---

## The Problem

Software teams lose time and trust because requirements are scattered across BRDs, UI screenshots, and client messages. When these sources conflict:
- **BRD:** Checkout shall support UPI only (`exclusive: true`).
- **Screenshot:** Staging UI shows a "Pay with Card" button.
- **Client note:** Card is in scope; UPI moves to Phase 2.

Existing AI tools summarize documents by guessing or silently overwriting the truth—treating visual observations as approval, losing source provenance, and baking withdrawn decisions into the specification.

## The Governed Flow

```
Evidence ──► Citation Validation ──► Append-Only Event Log ──► Deterministic Resolver ──► Current BRD
(Gemini)          (Code)                   (SQLite)                    (Deterministic)       (Projected)
```

1. **Gemini is the extractor, not the authority:** Reads PDF, PNG, and text; extracts structured claims constrained to a fixed schema.
2. **Code validates citations:** Quotes must exist verbatim in the source text; screenshot regions must exist within image boundaries. Observations can never grant authority.
3. **Append-only event log:** Ingests `ADDED` and `REMOVED` events with strictly increasing sequence numbers (SQLite; sequence assignment is atomic under the threaded server — FR-10).
4. **Deterministic resolver:** Keyed generically by `claim_id`. Promotes requirements only when an explicit, verified client scope decision governs the claim.

> **Honest Architecture Note:**
> *The append-only log in this demo is SQLite (in-memory by default, file-backed with `SCOPESHIFT_DB`).
> No GCP services are used by default; with no `GEMINI_API_KEY` configured, extraction runs on the deterministic
> fallback (pre-extracted evidence) and replay never calls Gemini. Tier-1 GCP integrations (BigQuery mirror,
> GCS originals, Vertex AI extraction) are env-gated and light up only with SDKs + env vars + credentials —
> the UI then shows them as live, otherwise as an honest "local mirror".*

---

## 3-Beat Demo: DISPUTED → GOVERNED → DISPUTED

1. **Beat 01 (Conflict):** BRD (UPI only) + Screenshot (Card visible) &rarr; **`DISPUTED`**. Requirement withheld.
2. **Beat 02 (Decision):** Client note explicitly authorizes Card &rarr; **`GOVERNED`**. Requirement enters the BRD with governing citation and superseded baseline recorded.
3. **Beat 03 (Withdrawal):** Client decision is withdrawn (`SRC-03 REMOVED`) &rarr; **`DISPUTED`**. Requirement disappears and the explanation remains visible.

---

## Quickstart

### 1. Run the Demo Server
```bash
python3 demo_server.py
```
Open **http://localhost:8765** in any modern browser.

- **Keyboard shortcuts:** Press `1`, `2`, or `3` to instantly step through the beats (strict order 1 → 2 → 3; re-pressing an applied beat is an explicit no-op with a recovery hint).
- **Extraction honesty:** With no `GEMINI_API_KEY` set, the extraction pill reads "DETERMINISTIC FALLBACK — pre-extracted evidence (replay never calls Gemini)". Beat 2's response includes the extraction outcome (claims, per-claim code validation, real mode).
- **Chaos tiles:** The adversarial test suite executes each attack through the real `validate_claim` boundary and returns a rejection receipt (rule fired, quote-diff/schema error, resulting classification).
- **Inspect artifacts:** Click *View Artifact* on any source to inspect the original PDF, screenshot, or client note in an overlay modal.
- **Persistence mode:** Set `SCOPESHIFT_DB="scopeshift.db"` before starting the server to run with persisted SQLite storage.
- **Stage cheat-sheet:** [`PRESENTER.md`](PRESENTER.md) (beat order, shortcuts, what to say, recovery).

### Optional Cloud Integrations (env-gated, never required)

SQLite is the source of truth and the demo works fully offline. Three Tier-1 GCP
integrations light up only when their SDK, env vars, **and** credentials are all
present — otherwise they are honest no-ops and the UI shows "local mirror".

| Service | Env vars (stage laptop) | Optional SDK |
|---|---|---|
| **BigQuery** event mirror | `SCOPESHIFT_BQ_DATASET` + credentials (`GOOGLE_APPLICATION_CREDENTIALS`) | `google-cloud-bigquery` |
| **GCS** originals + signed artifact URLs | `SCOPESHIFT_GCS_BUCKET` + credentials | `google-cloud-storage` |
| **Vertex AI** extraction route | `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` + credentials | `google-cloud-aiplatform` |

Install only if you want the cloud paths (never hard deps — stdlib + SQLite only):

```bash
pip install google-cloud-bigquery google-cloud-storage google-cloud-aiplatform
```

Status: `GET /api/cloud/status` → per-service `{"connected", "reason"}` plus the
effective extraction mode. The backend-status cluster in the UI polls it on load.
Startup logs honest lines, e.g. `BigQuery: not connected (env SCOPESHIFT_BQ_DATASET unset) — local mirror active`.

### 2. Run the Full Test Suite
```bash
python3 -m pytest
```
Runs the complete test suite covering:
- Generic claim registry & validation rules (`tests/test_core.py`)
- Append-only event store, trigger guards & FR-10 concurrency race test (`tests/test_store.py`)
- Extraction & ingestion pipeline (`tests/test_extraction.py`)
- Demo server REST endpoints, real chaos execution, beat honesty & security headers (`tests/test_api.py`)
- Env-gated GCP integrations: offline no-op fallbacks, honest status reasons, dual-write & signed-URL wiring (`tests/test_cloud.py`)

### 3. Run the Empirical Baseline Experiment
```bash
# Offline simulation / test run
python3 baseline.py --model gemini-2.5-flash --prompt plain --runs 10 --out out_plain --mock
python3 baseline.py --model gemini-2.5-flash --prompt hinted --runs 10 --out out_hinted --mock

# Live Gemini run (requires GEMINI_API_KEY)
python3 baseline.py --model gemini-2.5-flash --prompt plain --runs 10 --out out_plain
python3 baseline.py --model gemini-2.5-flash --prompt hinted --runs 10 --out out_hinted
```

---

## What Is Actually Implemented

- **5 pages:** Live Executive Cockpit (+ 3D spatial twin), Multi-Claim Scope Governance Matrix, Ingestion & Client Decision Console, Governed BRD Document Generator, Append-Only Immutable Audit Log.
- **Light editorial design system:** light canvas (`#f8f9fa`), serif headlines (Newsreader), crimson/emerald/royal accent palette — not a dark "industrial" theme.
- **Real chaos execution:** adversarial tiles run hostile payloads through the genuine `validate_claim` boundary; each returns a rejection receipt naming the rule fired.
- **Extraction honesty:** no "Live Gemini Extractor" theater — an honest status pill shows the real mode; Beat 2's response exposes claims, per-claim validation, and mode.
- **Reset-aware beats:** 1 → 2 → 3 ordering enforced by design; re-pressing an applied beat returns an explicit `already_applied` hint.

---

## Submission Assets

- **Selection Deck:** [`submission/ScopeShift-HackSprint-Phase2-8slide.pptx`](submission/ScopeShift-HackSprint-Phase2-8slide.pptx) (8 core story slides + 1 empirical baseline appendix)
- **Deck Generator:** [`build_deck.py`](build_deck.py)
- **Fixtures:** `fixtures/brd.pdf`, `fixtures/checkout.png`, `fixtures/client_note.txt`
