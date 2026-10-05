# ScopeShift Platform Task Board

## Core Invariants
- **Authority Invariant:** Gemini proposes, code decides. Never let model output grant authority.
- **Fail-Closed Boundary:** Any verification error leaves claims unverified; unverified claims never govern.
- **Audit Lineage:** Monotonic SQLite append-only log with SHA-256 cryptographic hash chaining.
- **Truth in Documentation:** Every claim maps directly to an automated test or a verification script. Never fabricate numbers.

---

## Task Progress

- [x] **TASK 1 - Repo Hygiene & Clean Slate**
  - [x] Add `requirements.txt` (`google-genai`, `pypdf`, `Pillow`, `google-cloud-bigquery`, `google-cloud-storage`, `pytest`)
  - [x] Add `.env.example` with all configuration variables (`GEMINI_API_KEY`, `SCOPESHIFT_DB`, etc.)
  - [x] Make persistence the default (`SCOPESHIFT_DB` defaults to `./events.db`, `/api/health` reports `persisted: true`)
  - [x] Clean obsolete directories (`.ppt-build/`, `preview/`, `baseline_out/`, `build_deck.py`)
  - [x] Relocate PRD to `docs/PRD.md`, add MIT `LICENSE` and `.github/workflows/test.yml`
  - [x] README: one-command quickstart, architecture diagram, honest live vs offline table
  - [x] Automated tests passing & committed (`1f48781`)

- [x] **TASK 2 - Real Gemini Structured Extraction**
  - [x] Pass `response_schema` (`ClaimExtractionSchema` enum-locked `claim_id`) and `response_mime_type="application/json"`
  - [x] Support 3 modalities: text, raw PDF bytes (with pypdf fallback), and images with dynamic MIME detection
  - [x] Replace silent exceptions with structured failure tracking (`reason`, `error_type`) and exponential backoff retry (3 tries)
  - [x] Strict fallback: canned claims only for exact demo fixtures matched by SHA-256; unknown inputs fail closed with 0 claims
  - [x] Unit tests with mocked Gemini client (`tests/test_extraction.py`)
  - [x] Automated tests passing & committed (`44698b8`)

- [x] **TASK 3 - Wire Gemini into Application Flow**
  - [x] Implement `POST /api/extract` (multipart/form-data & base64 JSON payload support)
  - [x] Connect Ingestion Studio UI with file upload & text paste box, showing verified/rejected status & receipts
  - [x] Live SSE feed uses `Extractor` when key is present, labeled clearly as scripted otherwise
  - [x] Route indicator pill in UI and `/api/cloud/status` showing `live-gemini`, `live-vertex`, or `offline` with last failure reason
  - [x] Automated tests passing & committed (`5a7dac1`)

- [x] **TASK 4 - Real Screenshot Verification**
  - [x] Parse image dimensions from binary PNG/JPEG headers (`get_image_size`)
  - [x] Region verified strictly inside image bounds
  - [x] Pillow crop extraction + separate Gemini transcriber call + code-level string match (`verify_screenshot_crop`)
  - [x] Verifier outage fails closed: unverified claims demoted to observations
  - [x] Tests covering correct quote, fabricated quote, out-of-bounds region, and verifier outage (`tests/test_screenshot.py`)
  - [x] Automated tests passing & committed (`c76ef03`)

- [x] **TASK 5 - Source Identity & Approver Allowlist**
  - [x] Evidence carries `sender`, `channel`, `received_at`
  - [x] Load approver allowlist from `approvers.json` (`SCOPESHIFT_APPROVERS` env)
  - [x] Client note governance gate: requires `proposed_scope_change` AND `quote_verified` AND allowlisted sender
  - [x] Unauthorized senders demoted to observations with reason `"sender not authorised"`
  - [x] Sender/channel incorporated into event payload and covered by SHA-256 hash chain
  - [x] 5 real adversarial chaos tiles in UI and server (`forged_screenshot`, `unverified_note`, `rogue_currency`, `forged_sender`, `fabricated_screenshot_text`)
  - [x] Tests for each case (`tests/test_approvers.py`, `tests/test_api.py`)
  - [x] Automated tests passing & committed (`43b8530`)

- [x] **TASK 6 - Google Cloud, Live & Provable**
  - [x] Move `VertexExtractor` to `google-genai` SDK with `vertexai=True`, project, location, and structured `response_schema`
  - [x] BigQuery: payload column JSON string serialization, insert error handling, and `verify_read_back` query
  - [x] Cloud Storage: upload ingested evidence artifacts and serve short-lived signed URLs via `artifact_url`
  - [x] Verification probe `scripts/verify_cloud.py`: performs Vertex extraction, GCS upload + signed URL fetch, and BigQuery insert + select
  - [x] Probe fails closed: prints missing environment variables and exits non-zero without credentials (never fakes PASS)
  - [x] Add `docs/GOOGLE_CLOUD_SETUP.md` with exact `gcloud` provisioning and IAM commands
  - [x] Automated tests passing & committed (`e2f00ed`)

- [x] **TASK 7 - Benchmark Suite vs Plain Gemini**
  - [x] Implement `benchmark/run_benchmark.py`: compares Plain Gemini vs ScopeShift across checkout conflict (3 stages) and 5 adversarial attacks
  - [x] Evaluates metrics: unauthorized requirement admitted (Y/N), citation verbatim rate, correct state per stage
  - [x] Strict rule: exits cleanly with clear message when `GEMINI_API_KEY` is missing; results written from real runs only
  - [x] Unit test harness in `tests/test_benchmark.py` proving ScopeShift invariants and missing key exit behavior
  - [x] Automated tests passing & committed (`ecf1bf9`)

- [x] **TASK 8 - Deployment & Containerization**
  - [x] Server reads `HOST` and `PORT` from environment (`0.0.0.0` in container, `127.0.0.1` locally)
  - [x] `Dockerfile`: Python 3.11-slim, non-root system user (`scopeshift`), healthcheck on `/api/health`
  - [x] `.dockerignore`: excludes VCS, tests, caches, and secrets
  - [x] `deploy/cloudrun.md`: step-by-step `gcloud run deploy` commands with required environment variables
  - [x] Automated tests passing & committed (`0fe26ef`)

- [x] **TASK 9 - Docs Truth Pass & Claims Evidence Matrix**
  - [x] Synchronize `README.md`, `PRESENTER.md`, `tasks/todo.md` with test proofs
  - [x] Create `CLAIMS_EVIDENCE.md` matrix mapping every claim to test file, test name, and verification command
