# ScopeShift Live Run Log

**Date:** 2026-10-06  
**Environment:** Windows, Python 3.13.5  
**Active API Key:** Configured in `.env` (`AIzaSy...`)

---

## 1. Live Smoke Probe Results (`scripts/smoke_live.py`)

The live smoke probe was executed directly against Google Gemini Developer API using the official `google-genai` SDK.

### 1.1 Multi-Model Failover Live Probe (2026-10-06)

| Modality | Input | Target Model | Answering Model | Status | Claims Extracted | Latency |
|:---|:---|:---|:---|:---:|:---:|:---|
| **Text** | Pasted scope change note | `gemini-3.6-flash` | `gemini-2.5-flash` (auto failover) | **PASS** | 2 | 7,771.8 ms |
| **PDF** | `fixtures/brd.pdf` (raw bytes) | `gemini-3.6-flash` | `gemini-2.5-flash` (auto failover) | **PASS** | 3 | 13,463.1 ms |
| **Image** | `fixtures/checkout.png` (bytes) | `gemini-3.6-flash` | `gemini-2.5-flash` (auto failover) | **PASS** | 3 | 8,637.4 ms |

### 1.2 Direct Zero-Fallback Probe: `gemini-3.6-flash` Only (2026-10-07)

Executed with `SCOPESHIFT_GEMINI_MODEL=gemini-3.6-flash SCOPESHIFT_GEMINI_FALLBACKS=` (no fallbacks):

| Modality | Input | Target Model | Answering Model | Status | Claims | Latency / Error Details |
|:---|:---|:---|:---|:---:|:---:|:---|
| **Text** | Pasted scope change note | `gemini-3.6-flash` | `gemini-3.6-flash` | **PASS** | 2 | 8,507.5 ms |
| **PDF** | `fixtures/brd.pdf` (raw bytes) | `gemini-3.6-flash` | None (fail closed) | **FAIL** | 0 | `ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}` |
| **Image** | `fixtures/checkout.png` | `gemini-3.6-flash` | — | **STOPPED** | — | Stopped per instructions after PDF failure |

**Observation:** `gemini-3.6-flash` successfully extracted structured claims from raw text (8.5 s), but failed on multi-modal PDF processing with remote `503 UNAVAILABLE` (high demand spike). With fallbacks disabled, the engine fails closed as designed. Benchmark run paused per instructions.

---

## 2. Issues Discovered and Fixes Applied

1. **Gemini Developer API Schema Constraint (`additionalProperties`)**:
   - *Issue:* Gemini Developer API returned HTTP 400 when Pydantic `ClaimExtractionSchema` had `model_config = {"extra": "allow"}` because OpenAPI schemas with `additionalProperties: true` are rejected by Google's structured output validator.
   - *Fix:* Changed `ClaimExtractionSchema` to `model_config = {"extra": "ignore"}`.

2. **Per-Model Quota Failover**:
   - *Issue:* Experimental models (`gemini-3.6-flash`, `gemini-3.5-flash`) operate under strict 20 req/day free-tier limits. When exhausted, Google returns HTTP 429 with `RESOURCE_EXHAUSTED`.
   - *Fix:* Extended `is_model_unavailable_error` in `scopeshift/extraction.py` to identify HTTP 429, 503, `"resource_exhausted"`, `"quota exceeded"`, and `"high demand"`. Added `gemini-2.5-flash` to `SCOPESHIFT_GEMINI_FALLBACKS`.

3. **Method Signatures in Extraction**:
   - *Issue:* `Extractor.extract_from_pdf` and `Extractor.extract_from_image` were invoked by `demo_server.py` with `source_type=...`, throwing `TypeError`.
   - *Fix:* Added optional `source_type` argument to both methods.

4. **Hermetic Test Isolation**:
   - *Issue:* `demo_server.py` loaded `.env` at module import time, causing test runs to hit live Google APIs and burn daily quota.
   - *Fix:* Confined `.env` loading to `if __name__ == "__main__":` blocks so pytest test runs execute offline with 0 network calls and 100% determinism.

---

## 3. Quota and Benchmark Status

- **Benchmark Run**: Benchmark has not been run; `benchmark/results.md` and `benchmark/results.json` do not exist yet. Automated execution of `benchmark/run_benchmark.py` requires 24+ live API calls across 3 iterations and will only be run once sustained quota or billing is available. In accordance with the project rule: *Never fabricate benchmark numbers. If an API key or credentials are missing/exhausted, say so and stop that step.*
- **Live Daily Quota**: Following the initial live probe runs, free-tier per-model daily limits restrict continuous batch benchmarking runs.

---

## 4. Latency Characteristics

**Latency Note:** Live extraction takes approximately 8–13 s per call (observed: 7.8 s text, 13.5 s PDF, 8.6 s image). This latency is driven by full multi-modal document upload, strict structured JSON schema enforcement, remote Gemini multi-modal reasoning, and fail-closed code-level verification.

---

## 5. Container Deployment Readiness (Docker)

- **Docker Status:** **VERIFIED & PASSING (2026-10-07)**
- **Diagnostic & Verification:**
  - Docker Desktop daemon initialized via local engine on Windows / WSL2.
  - Image build executed: `docker build -t scopeshift:latest .` (successfully packaged Python 3.11-slim, all dependencies including `google-genai`, `pypdfium2`, `Pillow`, and non-root user `scopeshift`).
  - Container execution: `docker run -d --name scopeshift-test -p 8769:8765 scopeshift:latest`.
  - Healthcheck verification: `GET http://127.0.0.1:8769/api/health` returned HTTP `200` with payload `{"status": "ok", "version": "1.0.0", "persisted": true}`. Built-in Dockerfile HEALTHCHECK verified passing.
  - Container safely stopped and cleaned.
