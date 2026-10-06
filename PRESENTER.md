# ScopeShift — Stage Presenter Runbook

**One rule for the whole demonstration: trigger stages in order 1 → 2 → 3.** Stage 1 always re-seeds, so
you can run the sequence as many times as you like. Re-pressing an already-applied stage is an
honest no-op — the UI tells you ("press 1 to re-seed, then 2") instead of silently doing nothing.

## Before you present

1. **One-Command Launcher:**
   - Linux/Mac: `python run_demo.py`
   - Windows PowerShell: `.\run_demo.ps1` (or `python run_demo.py`)
   - *This starts `demo_server.py`, polls `/api/health` until ready, and automatically launches your browser.*
2. **Demo Safe Mode Toggle (Stage Safety Guarantee):**
   - In the header navigation bar, locate the **`🛡 Safe Mode`** button.
   - For an absolutely risk-free live presentation on stage with unpredictable conference Wi-Fi, click **`🛡 Safe Mode: ON`** (or launch with `python run_demo.py --safe-mode`).
   - Safe Mode instantly forces the deterministic offline fallback pipeline, guaranteeing that no live API network hiccups, rate limits, or latency spikes can disrupt your presentation.
3. **Extraction Status Pill:**
   - Reads: **`ROUTE: OFFLINE (SAFE MODE)`**, **`ROUTE: LIVE-GEMINI`**, or **`ROUTE: OFFLINE`**.
4. **Keyboard shortcuts:** **1**, **2**, **3** = stages (**Esc** closes modals/toasts, **?** opens stage keys).

---

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

---

## Chaos tiles (page 5, "Adversarial Stress Test Suite")

Five real attacks, each executed through the actual `validate_claim` code boundary — nothing canned:

| Tile | Attack | Rule that fires | Code Defense |
|------|--------|-----------------|--------------|
| **TEST 1 Forged Screenshot** | screenshot with `proposed_scope_change=true` | Invariant: screenshots can NEVER govern | Boundary forces `proposed_scope_change=False` |
| **TEST 2 Vague Note** | "Maybe consider Card?" with an unverifiable quote | Verbatim quote proof (NFKC normalized) | `quote_verified=False` &rarr; classified OBSERVATION only |
| **TEST 3 Rogue Currency** | `checkout.bitcoin` outside schema enum | Frozen schema enum check | Rejected with `ValidationError` before the event log |
| **TEST 4 Forged Sender** | Valid quote from unauthorized sender "Mallory" | Approver allowlist check (`approvers.json`) | Demoted to OBSERVATION only ("sender not authorised") |
| **TEST 5 Fabricated Screenshot Text** | Image crop text does not match submitted quote | Separate crop transcription verification | `quote_verified=False` &rarr; classified OBSERVATION only |

The toast and audit panel show the exact rule that fired + resulting classification for each attack. Point at it: *"The attacker never reaches the governed BRD — the code boundary intercepts and neutralizes them first."*

---

## Real-Time Fragmented Intake & Ingestion Studio

- **Ingestion Studio (Page 3):** Upload real documents (PDFs, screenshots, or pasted notes).
- **Scanned PDF Handling:** If a PDF lacks digital text (scanned image), `pypdfium2` renders pages to images, transcribes them visually, and matches quotes deterministically (fails closed if unverified).
- **Inbound Webhook Integration:** Live endpoint `POST /api/webhook/inbound` accepts external fragmented updates (Slack/email) with HMAC-SHA256 signature verification, replay protection, and SSE broadcast (`python scripts/send_webhook.py`).
- **Concurrent Scale & Integrity:** Run `python scripts/load_test.py -n 50 -t 10` to prove that concurrent multi-threaded writes maintain strict SQLite WAL ordering and 100% cryptographic SHA-256 chain validity.

---

## Route Indicator & Cloud Status

The header route pill reports the true operational route:
- **`live-gemini`**: Direct Google Gemini API extraction (`GEMINI_API_KEY` present)
- **`live-vertex`**: Vertex AI endpoint extraction via `google-genai` SDK (`vertexai=True`)
- **`offline`**: Deterministic offline fallback (exact SHA-256 fixture match; unknown input returns 0 claims)
- **`offline (safe-mode)`**: Demo Safe Mode active, bypassing live models

If a live extractor fails, the pill displays the exact `last_failure_reason`.

---

## Recovery

- **Wrong order / double-press:** you get a "no-op" toast with the hint. Press **1** to re-seed, then continue 1 → 2 → 3.
- **Something looks off:** the **Reset** button (or POST `/api/demo/reset`) rebuilds the seed.
- **Time-travel scrubber** (page 5): drag to any sequence number to replay the exact historical state.

---

## Truth in Presentation (Lines to remember)

- ❌ Never claim live extraction when running offline — point to the route indicator pill.
- ❌ Never claim model approval — always: *"Gemini proposes claims; code validates citations and decides authority."*
- ❌ Never claim benchmark results without running: `python benchmark/run_benchmark.py`
