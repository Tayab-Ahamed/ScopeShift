# ScopeShift Claims & Evidence Matrix

Every claim made in the ScopeShift documentation, presentation materials, and architecture specifications maps directly to an automated test, an executable verification script, or a verified codebase artifact.

In accordance with ScopeShift Non-Negotiable Rules:
- **Invariant:** Gemini proposes, code decides. Never let model output grant authority.
- **Fail Closed:** Any verification error leaves claims unverified; unverified claims never govern.
- **Truth in Documentation:** Never fabricate numbers or test results. Mark anything unperformed or blocked on credentials honestly.

---

## Claims Evidence Table

| # | System Claim | Implementation File | Verification Test / Script | Verification Command | Status |
|:---:|:---|:---|:---|:---|:---:|
| 1 | **Gemini proposes, code decides:** model output cannot grant authority; visual UI observations cannot alter BRD | [`scopeshift/validation.py`](scopeshift/validation.py), [`scopeshift/models.py`](scopeshift/models.py) | `test_screenshot_observation_never_governs` in [`tests/test_core.py`](tests/test_core.py) | `pytest tests/test_core.py -k test_screenshot_observation_never_governs` | **DONE** |
| 2 | **Fail-closed boundary:** verification failures permanently store claims as unverified; unverified claims never govern | [`scopeshift/models.py`](scopeshift/models.py), [`scopeshift/validation.py`](scopeshift/validation.py) | `tests/test_citation_enforcement.py` & `test_verifier_outage_fails_closed` in [`tests/test_screenshot.py`](tests/test_screenshot.py) | `pytest tests/test_citation_enforcement.py tests/test_screenshot.py` | **DONE** |
| 3 | **Real Gemini structured extraction:** `gemini-3.6-flash` default, `gemini-3.5-flash` 404 fallback, typed schema fields (`methods`, `currency`, `required_factors`, `sla_days`), no temperature/top_p/top_k | [`scopeshift/extraction.py`](scopeshift/extraction.py), [`scopeshift/cloud.py`](scopeshift/cloud.py) | `test_mock_gemini_404_fallback_model`, `test_claim_extraction_schema_typed_fields_conversion`, `test_vertex_extractor_404_fallback` | `pytest tests/test_extraction.py tests/test_cloud.py` | **DONE** |
| 4 | **Multi-modal ingestion:** supports raw text, PDF bytes (with pypdf fallback), and images with dynamic MIME header detection | [`scopeshift/extraction.py`](scopeshift/extraction.py) | `test_extractor_pdf_bytes_modality`, `test_extractor_image_bytes_modality`, `test_detect_image_mime` in [`tests/test_extraction.py`](tests/test_extraction.py) | `pytest tests/test_extraction.py` | **DONE** |
| 5 | **Structured failure reasons & retries:** replaced silent exceptions with `reason`/`error_type` and exponential backoff retry (3 tries) | [`scopeshift/extraction.py`](scopeshift/extraction.py) | `test_extractor_retry_on_timeout`, `test_extractor_bad_json_handling` in [`tests/test_extraction.py`](tests/test_extraction.py) | `pytest tests/test_extraction.py` | **DONE** |
| 6 | **Deterministic fallback integrity:** canned claims only for exact demo fixtures matched by SHA-256; unknown inputs return 0 claims | [`scopeshift/extraction.py`](scopeshift/extraction.py) | `test_extractor_fallback_canned_for_known_hash`, `test_extractor_fallback_zero_for_unknown_input` in [`tests/test_extraction.py`](tests/test_extraction.py) | `pytest tests/test_extraction.py` | **DONE** |
| 7 | **POST `/api/extract` endpoint:** accepts PDF, PNG/JPEG, or text; runs Extractor &rarr; validate_claim &rarr; Evidence &rarr; ADDED event &rarr; returns receipts | [`demo_server.py`](demo_server.py) | `test_extract_endpoint_known_fixture_pdf`, `test_extract_endpoint_unknown_text_offline` in [`tests/test_api.py`](tests/test_api.py) | `pytest tests/test_api.py -k test_extract_endpoint` | **DONE** |
| 8 | **True route indicator:** UI pill & `/api/cloud/status` report `live-gemini`, `live-vertex`, or `offline` with `last_failure_reason` | [`demo_server.py`](demo_server.py), [`scopeshift/extraction.py`](scopeshift/extraction.py) | `test_api_cloud_status_route_and_failure_reason` in [`tests/test_api.py`](tests/test_api.py) | `pytest tests/test_api.py -k test_api_cloud_status_route` | **DONE** |
| 9 | **Image dimensions parsed from header:** image size parsed dynamically from binary PNG/JPEG header bytes, not hardcoded | [`scopeshift/validation.py`](scopeshift/validation.py) | `test_get_image_size_png`, `test_get_image_size_jpeg` in [`tests/test_screenshot.py`](tests/test_screenshot.py) | `pytest tests/test_screenshot.py` | **DONE** |
| 10 | **Spatial + transcript screenshot verification:** region verified inside bounds, Pillow crop transcribed with separate Gemini call, code string match | [`scopeshift/validation.py`](scopeshift/validation.py) | `test_correct_quote_verified`, `test_fabricated_quote_rejected`, `test_region_out_of_bounds_rejected` in [`tests/test_screenshot.py`](tests/test_screenshot.py) | `pytest tests/test_screenshot.py` | **DONE** |
| 11 | **Source identity metadata:** client note carries `sender`, `channel`, `received_at`; approver allowlist loaded from `approvers.json` | [`scopeshift/approvers.py`](scopeshift/approvers.py), [`approvers.json`](approvers.json) | `test_load_approvers_file`, `test_is_sender_allowlisted` in [`tests/test_approvers.py`](tests/test_approvers.py) | `pytest tests/test_approvers.py` | **DONE** |
| 12 | **Approver governance gate:** client note governs only if `proposed_scope_change` AND `quote_verified` AND sender allowlisted; else observation | [`scopeshift/validation.py`](scopeshift/validation.py), [`scopeshift/models.py`](scopeshift/models.py) | `test_approver_allowlist_enforcement` in [`tests/test_approvers.py`](tests/test_approvers.py) | `pytest tests/test_approvers.py` | **DONE** |
| 13 | **Cryptographic sender coverage:** `sender` and `channel` recorded in event payload and covered by monotonic SHA-256 hash chain | [`scopeshift/store.py`](scopeshift/store.py), [`demo_server.py`](demo_server.py) | `test_event_store_includes_sender_and_channel_in_hash_chain` in [`tests/test_approvers.py`](tests/test_approvers.py) | `pytest tests/test_approvers.py` | **DONE** |
| 14 | **Adversarial Chaos Suite (5 Tiles):** real execution for forged screenshot, vague note, rogue currency, forged sender, fabricated screenshot text | [`demo_server.py`](demo_server.py), [`index.html`](index.html) | `test_chaos_forged_sender`, `test_chaos_fabricated_screenshot_text` in [`tests/test_api.py`](tests/test_api.py) | `pytest tests/test_api.py -k test_chaos` | **DONE** |
| 15 | **Vertex AI SDK adapter:** `VertexExtractor` migrated to `google-genai` SDK with `vertexai=True`, project, location, and `response_schema` | [`scopeshift/cloud.py`](scopeshift/cloud.py) | `test_vertex_extractor_mocked_genai` in [`tests/test_cloud.py`](tests/test_cloud.py) | `pytest tests/test_cloud.py -k test_vertex_extractor_mocked` | **DONE** |
| 16 | **BigQuery payload JSON serialization & read-back:** inserts JSON string payload into BigQuery and verifies via `verify_read_back` query | [`scopeshift/cloud.py`](scopeshift/cloud.py) | `test_bigquery_append_calls_fake_client`, `test_bigquery_verify_read_back` in [`tests/test_cloud.py`](tests/test_cloud.py) | `pytest tests/test_cloud.py -k test_bigquery` | **DONE** |
| 17 | **Cloud Storage artifact upload & signed URLs:** uploads ingested originals to GCS and serves signed URLs via `artifact_url` | [`scopeshift/cloud.py`](scopeshift/cloud.py), [`demo_server.py`](demo_server.py) | `test_gcs_upload_and_signed_url_fake_client`, `test_artifact_url_local_paths` in [`tests/test_cloud.py`](tests/test_cloud.py) | `pytest tests/test_cloud.py -k test_gcs` | **DONE** |
| 18 | **Cloud verification probe script:** `scripts/verify_cloud.py` tests Vertex AI, GCS, BigQuery with credentials or exits non-zero without faking | [`scripts/verify_cloud.py`](scripts/verify_cloud.py) | `test_verify_cloud_script_fails_without_credentials` in [`tests/test_cloud.py`](tests/test_cloud.py) | `python scripts/verify_cloud.py` (code 1) | **DONE** |
| 19 | **Google Cloud setup documentation:** exact `gcloud` provisioning and IAM commands for Vertex AI, BigQuery, GCS, service accounts | [`docs/GOOGLE_CLOUD_SETUP.md`](docs/GOOGLE_CLOUD_SETUP.md) | Verified documentation file | Manual review / `gcloud` CLI | **DONE** |
| 20 | **Benchmark suite harness:** `benchmark/run_benchmark.py` compares Plain Gemini vs ScopeShift across 3 stages + 5 attacks; exits cleanly when key is missing | [`benchmark/run_benchmark.py`](benchmark/run_benchmark.py) | `test_benchmark_exits_cleanly_without_api_key`, `test_benchmark_scopeshift_checkout_stages`, `test_benchmark_scopeshift_adversarial_all_blocked` in [`tests/test_benchmark.py`](tests/test_benchmark.py) | `pytest tests/test_benchmark.py` | **DONE** |
| 21 | **Environment HOST & PORT resolution:** server reads `HOST` and `PORT` from environment (`0.0.0.0` in container, `127.0.0.1` locally) | [`demo_server.py`](demo_server.py) | `test_server_reads_host_and_port_env` in [`tests/test_api.py`](tests/test_api.py) | `pytest tests/test_api.py -k test_server_reads_host_and_port_env` | **DONE** |
| 22 | **Containerization & Cloud Run guide:** Dockerfile with python-slim, non-root user `scopeshift`, `/api/health` healthcheck, `.dockerignore`, `deploy/cloudrun.md` | [`Dockerfile`](Dockerfile), [`.dockerignore`](.dockerignore), [`deploy/cloudrun.md`](deploy/cloudrun.md) | Verified Dockerfile, `.dockerignore`, and Cloud Run guide | `docker build -t scopeshift .` | **DONE** |
| 23 | **Default persistence:** `SCOPESHIFT_DB` defaults to `./events.db`, `/api/health` reports `{"persisted": true}` | [`demo_server.py`](demo_server.py), [`scopeshift/store.py`](scopeshift/store.py) | `test_health_endpoint` in [`tests/test_api.py`](tests/test_api.py) | `pytest tests/test_api.py -k test_health_endpoint` | **DONE** |
| 24 | **Live smoke test probe:** `scripts/smoke_live.py` executes live text, PDF, and image extractions, prints model used, fails closed non-zero without API key | [`scripts/smoke_live.py`](scripts/smoke_live.py) | `test_smoke_live_script_fails_without_api_key` in [`tests/test_extraction.py`](tests/test_extraction.py) | `python scripts/smoke_live.py` | **DONE** |

---

## Status of Items Blocked on External Credentials

In accordance with project integrity constraints:
- **Live Google Cloud Probe Execution against Live GCP:**
  - Status: **BLOCKED ON CREDENTIALS**
  - Reason: `GOOGLE_APPLICATION_CREDENTIALS` / `GOOGLE_CLOUD_PROJECT` are not configured in this local environment.
  - Verification: `python scripts/verify_cloud.py` correctly identified all missing variables and exited with code `1` rather than faking a PASS.
- **Live Gemini Extraction Smoke Probe (`scripts/smoke_live.py`):**
  - Status: **BLOCKED ON CREDENTIALS**
  - Reason: `GEMINI_API_KEY` is not present in this local environment.
  - Verification: `python scripts/smoke_live.py` correctly identified missing `GEMINI_API_KEY`, printed required action, and exited with code `1`.
- **Live Gemini Benchmark Execution (`benchmark/results.json`, `benchmark/results.md`):**
  - Status: **BLOCKED ON CREDENTIALS**
  - Reason: `GEMINI_API_KEY` is not present in this local environment.
  - Verification: `python benchmark/run_benchmark.py` executed, outputted the clear required missing-key warning, and exited cleanly with code `1` without fabricating benchmark numbers.
