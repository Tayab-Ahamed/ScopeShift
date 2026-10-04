# ScopeShift (PS/P42)

> **"Seeing a button is not approving the button."**  
> *From conflicting evidence to governed requirements.*

ScopeShift is an evidence-governed BRD generator built for **PS/P42** in the **Commudle Hack Sprint**. It extracts claims from documents and screenshots, validates citations, detects contradictions, and only promotes a requirement when an explicit client scope decision authorizes it.

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
(Gemini)          (Code)                   (BigQuery / SQLite)            (Deterministic)       (Projected)
```

1. **Gemini is the extractor, not the authority:** Reads PDF, PNG, and text; extracts structured claims constrained to a fixed schema.
2. **Code validates citations:** Quotes must exist verbatim in the source text; screenshot regions must exist within image boundaries. Observations can never grant authority.
3. **Append-only event log:** Ingests `ADDED` and `REMOVED` events with strictly increasing sequence numbers.
4. **Deterministic resolver:** Keyed generically by `claim_id`. Promotes requirements only when an explicit, verified client scope decision governs the claim.

> **Honest Architecture Note:**  
> *"BigQuery is the persisted append-only log. The demo reads through an in-memory mirror of it."*

---

## 3-Beat Demo: DISPUTED → GOVERNED → DISPUTED

1. **Beat 01 (Conflict):** BRD (UPI only) + Screenshot (Card visible) &rarr; **`DISPUTED`**. Requirement withheld.
2. **Beat 02 (Decision):** Client note explicitly authorizes Card &rarr; **`GOVERNED`**. Requirement enters the BRD with governing citation and superseded baseline recorded.
3. **Beat 03 (Withdrawal):** Client decision is withdrawn (`SRC-03 REMOVED`) &rarr; **`DISPUTED`**. Requirement disappears and the explanation remains visible.

---

## Quickstart

### 1. Run the Demo Server
```powershell
python demo_server.py
```
Open **http://localhost:8765** in any modern browser.

- **Keyboard shortcuts:** Press `1`, `2`, or `3` to instantly step through the beats.
- **Inspect artifacts:** Click *View Artifact* on any source to inspect the original PDF, screenshot, or client note in an overlay modal.
- **Persistence mode:** Set `$env:SCOPESHIFT_DB="scopeshift.db"` before starting the server to run with persisted SQLite storage.

### 2. Run the Full Test Suite
```powershell
python -m pytest
```
Runs the complete test suite covering:
- Generic claim registry & validation rules (`tests/test_core.py`)
- Append-only event store & trigger guards (`tests/test_store.py`)
- Extraction & ingestion pipeline (`tests/test_extraction.py`)
- Demo server REST endpoints & security headers (`tests/test_api.py`)

### 3. Run the Empirical Baseline Experiment
```powershell
# Offline simulation / test run
python baseline.py --model gemini-2.5-flash --prompt plain --runs 10 --out out_plain --mock
python baseline.py --model gemini-2.5-flash --prompt hinted --runs 10 --out out_hinted --mock

# Live Gemini run (requires GEMINI_API_KEY)
python baseline.py --model gemini-2.5-flash --prompt plain --runs 10 --out out_plain
python baseline.py --model gemini-2.5-flash --prompt hinted --runs 10 --out out_hinted
```

---

## Submission Assets

- **Selection Deck:** [`submission/ScopeShift-HackSprint-Phase2-8slide.pptx`](submission/ScopeShift-HackSprint-Phase2-8slide.pptx) (8 core story slides + 1 empirical baseline appendix)
- **Deck Generator:** [`build_deck.py`](build_deck.py)
- **Fixtures:** `fixtures/brd.pdf`, `fixtures/checkout.png`, `fixtures/client_note.txt`
