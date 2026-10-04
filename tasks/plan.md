# Implementation Plan: ScopeShift Production System

## Overview
Transform ScopeShift from a fixed 3-beat stage demo into a full-scale, end-to-end production evidence-governed requirements platform satisfying Problem Statement PS/P42. Redesign the entire UI/UX with a light editorial design system, interactive 3D spatial matrix, live multi-file & client-note ingestion, multi-claim governance matrix, interactive scope authority console, and live document diff/annotation inspector.

## Visual Identity (as actually implemented)
- **Aesthetic:** Light Editorial Governance Cockpit — light canvas (`#f8f9fa`), serif headlines (Newsreader/Playfair Display), JetBrains Mono for exact telemetry.
- **Panels:** White surfaces (`#ffffff`), subtle borders (`#e2e8f0`), soft shadows.
- **Tension & Conflict Accent:** Crimson (`#e11d48`) for contradictions and disputes.
- **Governed & Authority Accent:** Emerald (`#059669`) for verified decisions and approved requirements.
- **Provenance Accent:** Royal blue (`#2563eb`) for baselines, schemas, and evidence linkages.
- **Caution Accent:** Amber (`#d97706`) for honest fallback-mode indicators.

## System Architecture & Capabilities
1. **Multi-Claim Engine (`scopeshift/claims.py`):**
   - Registry supporting `checkout.payment_methods`, `checkout.currency`, `auth.mfa_requirement`, and `refunds.settlement_sla`, plus dynamic custom claim definitions.
2. **Interactive Ingestion & Decision API (`demo_server.py` & `scopeshift/ingest.py`):**
   - `POST /api/ingest`: Accepts custom uploaded text / documents, runs extraction & code validation, assigns monotonic source IDs (`SRC-XX`), and appends to SQLite append-only log.
   - `POST /api/govern`: Authors an explicit client scope decision on any claim, verifies quotes, and promotes requirement.
   - `POST /api/withdraw`: Withdraws a client decision with full reason tracking.
   - `POST /api/demo/scrub`: Replays the state machine to any sequence number with full diff projection.
   - `GET /api/export/markdown`: Full production BRD document export.
   - `GET /api/export/json`: Complete audit trail export.
3. **Advanced 3D Spatial Matrix (Three.js):**
   - 3D spatial knowledge graph of sources, claim nodes, conflict lasers, and the central governance core with camera presets and interactive hover details.
4. **Production UI Cockpit (`index.html`, `styles.css`, `app.js`):**
   - Navigation across 5 production modules:
     - 1. **Live Executive Cockpit & 3D Spatial Matrix**
     - 2. **Multi-Claim Scope Governance Matrix**
     - 3. **Ingestion & Client Decision Console**
     - 4. **Governed BRD Document Generator**
     - 5. **Append-Only Immutable Audit Log**

## Task Breakdown
- [ ] Task 1: Expand Claim Registry and Multi-Claim Ingestion Engine
- [ ] Task 2: Backend API Endpoints for Custom Ingestion, Authoring Decisions & Export
- [ ] Task 3: Light Editorial Design System & CSS Overhaul
- [ ] Task 4: Interactive 3D Spatial Knowledge Graph & Laser Vectors
- [ ] Task 5: Interactive Multi-Claim UI Modules, Ingestion Studio & BRD Generator
- [ ] Task 6: End-to-End Verification & Automated Tests
- [x] Task 7: Tier-0 Credibility Fixes (Stream A)
  - Real chaos execution through `validate_claim` with genuine rejection receipts
  - Beat-2 extraction honesty (claims + per-claim validation + real mode in the response; honest status pill instead of the "Live Gemini Extractor" toggle)
  - Extraction prompt enum lists all 4 registry claim_ids
  - FR-8/FR-18 `citation_warnings` wired into the snapshot path
  - Dead legacy removed (`scopeshift_core.py`, `event_store.py`, `test_scopeshift_core.py`)
  - FR-10 atomic sequence assignment (threading.Lock) + concurrent regression test
  - Reset-aware beats (1 → 2 → 3; explicit `already_applied` no-ops) + `PRESENTER.md`
  - Docs truth pass (this file, `tasks/todo.md`, `README.md`)
