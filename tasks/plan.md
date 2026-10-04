# Implementation Plan: ScopeShift Production System

## Overview
Transform ScopeShift from a fixed 3-beat stage demo into a full-scale, end-to-end production evidence-governed requirements platform satisfying Problem Statement PS/P42. Redesign the entire UI/UX with an out-of-the-box Tactile Swiss-Industrial High-End Precision Engineering palette, interactive 3D spatial matrix, live multi-file & client-note ingestion, multi-claim governance matrix, interactive scope authority console, and live document diff/annotation inspector.

## Out-of-the-Box Visual Identity (Anti-Slop)
- **Aesthetic:** Tactile High-Precision Industrial Governance Cockpit.
- **Background:** Deep Matte Carbon / Obsidian (`#0b0d11`, linear grid lines `#151922`).
- **Panels:** Slate-Graphite (`#131720`, border `#232a3b`, active `#1a202c`) with razor-sharp micro-borders and technical corner tick marks.
- **Tension & Conflict Accent:** International Safety Vermilion (`#ff3b00` / `#ff5500`) for contradictions, disputes, and the winning hook.
- **Governed & Authority Accent:** Luminous Acid Emerald (`#00f076` / `#05df72`) for verified decisions and approved requirements.
- **Provenance Accent:** Technical Cobalt (`#2b59ff` / `#4d74ff`) for baselines, schemas, and evidence linkages.
- **Typography:** Architectural typography with clean grotesque headers and JetBrains Mono for exact telemetry.

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
- [ ] Task 3: Out-of-the-Box Swiss-Industrial Design System & CSS Overhaul
- [ ] Task 4: Interactive 3D Spatial Knowledge Graph & Laser Vectors
- [ ] Task 5: Interactive Multi-Claim UI Modules, Ingestion Studio & BRD Generator
- [ ] Task 6: End-to-End Verification, Automated Tests & Visual Validation
