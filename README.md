<div align="center">

# ScopeShift
### Deterministic Evidence Governance &amp; Requirements Verification Engine

> **"Seeing a button is not approving the button."**  
> Decoupling multi-modal LLM extraction from specification authority through code-level citation proofs and tamper-evident event streaming.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-90%2F90%20passed%20(100%25)-emerald?style=flat-square&logo=pytest&logoColor=white)](tests/)
[![Architecture](https://img.shields.io/badge/Architecture-Fail--Closed%20Deterministic-blueviolet?style=flat-square)](#the-governed-pipeline)
[![Audit](https://img.shields.io/badge/Audit%20Ledger-SHA--256%20Hash--Chained-success?style=flat-square)](#immutable-event-ledger)
[![Cloud Mirrors](https://img.shields.io/badge/Cloud%20Dual--Write-BigQuery%20%7C%20GCS%20%7C%20Vertex-informational?style=flat-square&logo=googlecloud&logoColor=white)](#enterprise-cloud-architecture)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey?style=flat-square)](LICENSE)

<br/>

<img src="assets/scopeshift-architecture.svg" alt="ScopeShift Deterministic Pipeline" width="100%">

</div>

---

## Executive Overview

Modern software teams and autonomous AI coding agents face a critical drift vulnerability: **unauthorized visual scope creep**. When an engineering staging UI, mock, or chat snippet introduces a feature, current AI tools silently bake it into requirements specifications—treating mere visual observation as stakeholder approval.

**ScopeShift establishes a strict, verifiable boundary:**
1. **Extraction is decoupled from authority:** Multi-modal foundation models (Gemini 2.5 Flash / Vertex AI) extract structured claims, but are never permitted to make governance decisions.
2. **Code enforces citation integrity:** Every cited quote must match verbatim in the source document. Every UI screenshot must fall within physical bounding boxes. Dangling or hallucinated citations fail closed.
3. **Deterministic resolution:** Requirements advance into the published Business Requirements Document (BRD) strictly when an authorized, verified client decision explicitly mandates them.

---

## The Governed Pipeline

```
Evidence Artifacts ──► Verbatim Citation Gate ──► Append-Only Event Store ──► Deterministic Resolver ──► Governed BRD Spec
(PDF / PNG / Notes)       (Fail-Closed Code)          (Monotonic SHA-256)        (Pure State Machine)     (Live Projection)
```

| Pipeline Stage | Function | Guarantees |
|---|---|---|
| **1. Multi-Modal Ingestion** | Extracts candidate claims from PDFs, UI screenshots, and client messages. | Constrained schema extraction. Deterministic offline fallback preserved for zero-downtime reliability. |
| **2. Verbatim Citation Gate** | Code-level substring proof and spatial pixel bounding validation. | Fail-closed. Rejects fabricated quotes, forged scopes, and out-of-bounds bounding boxes with structured rejection receipts. |
| **3. Immutable Event Ledger** | Sequences mutations into an append-only log with SHA-256 cryptographic hash chains. | Monotonic ordering with SQLite atomic concurrency guards. Dual-writes to Google BigQuery streaming log. |
| **4. Deterministic Resolver** | Projector keyed by claim ID that computes conflict matrices and resolves governing authority. | Mathematical determinism: identical event sequences always yield identical requirements state. |
| **5. Governed BRD Document** | Generates authoritative markdown specifications with full audit lineage. | Real-time diff against baseline, governing source attribution, and superseded baseline references. |

---

## Core Capabilities

### 🛡️ Fail-Closed Citation Proofs
AI extractors cannot hallucinate authority. If a model generates a citation whose quote does not appear verbatim in the source payload, the ingestion boundary rejects the payload with an immutable rejection receipt (`UNVERIFIED_QUOTE`). Visual observations (`screenshot`) are permanently classified as non-authoritative.

### 👁️ Visual Provenance Diff Inspector
Clicking the governance banner in the Cockpit launches an interactive modal displaying side-by-side evidence cards for the active claim:
- Baseline BRD requirements vs staging UI observations vs client statements.
- Direct quote spans, image bounding-box overlays, and authority tier indicators.
- Live resolver rationale explaining why a claim is withheld or promoted.

### 🎯 1-Click Scenario Presets
Test the real validation pipeline and state machine with single-click production scenarios:
- **Security Mandate (`mfa`):** Baseline BRD specifies optional MFA &rarr; Client directive enforces TOTP &amp; SMS &rarr; Promoted to `GOVERNED`.
- **Scope Change (`currency`):** Baseline INR policy &rarr; Client switches to multi-currency USD &rarr; Replaces baseline as `GOVERNED`.
- **Adversarial Injection (`hostile`):** Injects fabricated quotes, forged scope overrides, and unregistered claims &rarr; Safely contained at the boundary.

### 🌐 3D Spatial Evidence Twin
Interactive Three.js visualizer rendering requirements topology in 3D coordinate space. When unverified staging evidence contradicts baseline documentation, a physical red vector clash barrier halts progression—visually demonstrating why observation is never approval.

### ⛓️ Cryptographic Audit Ledger &amp; BigQuery Stream
Every state change is recorded in an append-only event store. Each event calculates a SHA-256 digest over its sequence, payload, timestamp, and the preceding event's hash. The browser UI features a client-side **Verify Hash Chain** tool that recalculates the entire chain independently.

---

## Three-Stage Governance Lifecycle

The system enforces a strict 3-stage lifecycle demonstration:

```
[ STAGE 01: DISPUTED ] ────────► [ STAGE 02: GOVERNED ] ────────► [ STAGE 03: DISPUTED ]
Baseline BRD: UPI only           Client Note: Card authorized      Client revokes decision
UI shows Card button             Enters BRD with governing ref     Withdrawn from BRD immediately
Result: Requirement Withheld     Baseline marked SUPERSEDED        Forensic history preserved
```

---

## Quickstart

### Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome, Firefox, Safari, Edge)
- *Optional:* Google Cloud credentials (for live BigQuery / GCS / Vertex AI dual-write)

### 1. Launch the Server
```bash
python demo_server.py
```
Open **`http://localhost:8765`** in your browser.

- **Keyboard Shortcuts:** Press `1`, `2`, or `3` to instantly step through the 3 governance stages.
- **Automated Walkthrough:** Click `▶ Automated Walkthrough` in the header for a timed automated walkthrough.
- **Persistence Mode:** Set `SCOPESHIFT_DB="scopeshift.db"` to persist events to disk.

### 2. Run the Test Suite
The complete test suite runs in under 30 seconds with zero external dependencies:
```bash
python -m pytest -q
```
```
........................................................................ [ 80%]
..................                                                       [100%]
90 passed in 27.27s
```

### 3. Optional Enterprise Cloud Dual-Write
ScopeShift is built **fail-safe and offline-first**. All features function locally out-of-the-box. Optional GCP integrations activate automatically when environment variables and SDKs are present:

```bash
# Install optional cloud SDKs
pip install google-cloud-bigquery google-cloud-storage google-cloud-aiplatform

# Set configuration variables
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
export SCOPESHIFT_BQ_DATASET="scopeshift_audit"
export SCOPESHIFT_GCS_BUCKET="scopeshift-artifacts"
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

Check connection status at any time via `GET /api/cloud/status` or the live backend indicator cluster in the navigation bar.

---

## Test Architecture (90/90 Passing)

| Test Module | Coverage Scope |
|---|---|
| [`tests/test_core.py`](tests/test_core.py) | Domain claim registries, schema validators, invariant rules, and deterministic state transitions. |
| [`tests/test_store.py`](tests/test_store.py) | Monotonic sequence assignment, SHA-256 hash chains, trigger guards, and concurrent race integrity. |
| [`tests/test_extraction.py`](tests/test_extraction.py) | Multi-modal claim extraction, verbatim quote substring proofs, and coordinate bounding boundary checks. |
| [`tests/test_api.py`](tests/test_api.py) | REST endpoint validation, adversarial payload rejection receipts, stage progression, and security headers. |
| [`tests/test_cloud.py`](tests/test_cloud.py) | Graceful cloud fallback, offline no-op mirrors, honest connection diagnostics, and signed URL generation. |

---

## Technical Specifications

- **Backend:** Python 3 (standard library `http.server`, `sqlite3`, `hashlib`, `json`, `dataclasses`).
- **Frontend:** Vanilla modern ES6+, CSS Custom Properties, Canvas 2D sparklines, Three.js 3D spatial twin. Zero frontend build steps or bloated frameworks.
- **Extraction Model:** Google Gemini 2.5 Flash / Vertex AI with deterministic fallback pipeline.
- **Storage:** Atomic SQLite append-only log with optional Google BigQuery streaming dual-write and Google Cloud Storage artifact storage.
- **Design Language:** Light technical editorial canvas, Newsreader &amp; Inter typography, WCAG AA compliant contrast.

---

## License

Distributed under the Apache 2.0 License. See `LICENSE` for details.
