# ScopeShift Live Run Log

**Date:** 2026-10-06  
**Environment:** Windows, Python 3.13.5  
**Active API Key:** Configured in `.env` (`AIzaSy...`)

---

## 1. Live Smoke Probe Results (`scripts/smoke_live.py`)

The live smoke probe was executed directly against Google Gemini Developer API using the official `google-genai` SDK.

| Modality | Input | Target Model | Answering Model | Status | Claims Extracted | Latency |
|:---|:---|:---|:---|:---:|:---:|:---|
| **Text** | Pasted scope change note | `gemini-3.6-flash` | `gemini-2.5-flash` (auto failover) | **PASS** | 2 | 7,771.8 ms |
| **PDF** | `fixtures/brd.pdf` (raw bytes) | `gemini-3.6-flash` | `gemini-2.5-flash` (auto failover) | **PASS** | 3 | 13,463.1 ms |
| **Image** | `fixtures/checkout.png` (bytes) | `gemini-3.6-flash` | `gemini-2.5-flash` (auto failover) | **PASS** | 3 | 8,637.4 ms |

**Result:** All 3 modalities passed live execution (`exit code 0`).

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

- **Live Daily Quota**: Following the successful live probe runs, the Google Cloud free tier quota (20 requests/day per project per model) reached daily exhaustion for `gemini-3.6-flash`, `gemini-3.5-flash`, and `gemini-2.5-flash`.
- **Benchmark Run**: Further automated runs of `benchmark/run_benchmark.py` (which requires 24+ calls across 3 iterations) are cleanly paused in accordance with the project rule: *Never fabricate benchmark numbers. If an API key or credentials are missing/exhausted, say so and stop that step.* Existing benchmark baseline numbers in `benchmark/results.md` remain intact.

---

## 4. Container Deployment Readiness (Docker)

- **Docker Status:** **BLOCKED**
- **Diagnostic:** Docker CLI version 29.8.0 is installed, but the local Docker Engine / Docker Desktop daemon is not running (`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`).
- Per project rules, container execution is reported as BLOCKED without fabricated outputs.
