# CORTEX CLOUD AUTOPILOT — Master Implementation Plan
**Document:** `docs/IMPLEMENTATION_PLAN.md`  
**Date:** September 16, 2026  
**Status:** Approved Implementation Roadmap  

---

## 1. Architectural Component Categorization

| Category | Components / Modules | Rationale & Action |
| :--- | :--- | :--- |
| **KEEP** | `rag/build_index.py`, `rag/retrieve.py`, `orchestrator/agent.py` reasoning structure, `frontend/tests/` suites | The core vector retrieval, self-critique loop, and frontend test suites are functionally verified and pass all checks. |
| **UPGRADE** | `api_server.py`, `tools/actions.py`, `tools/event_bus.py`, `interfaces.py` | Connect FastAPI to the full orchestrator rather than bypassing it; add idempotency and distributed locks to actions; upgrade event bus to a hash-chained ledger. |
| **REPLACE** | Random sleep mocks in `tools/actions.py`, unauthenticated mutating routes, naive regex routing in `api_server.py` | Replace with controlled Docker/container operations, capability envelopes, and Pydantic-validated structured dispatch. |
| **ADD** | `topology/`, `twin/`, `forecasting/`, `optimization/`, `cortex/`, `verification/`, `evaluation/`, ShadcnStore UI layer | Implement the missing core pillars: dependency graphs, digital twin, ML forecasting, multi-objective optimizer, CORTEX Guard, and the 3-layer command center. |
| **DEFER** | Reinforcement learning, global multi-cloud live mutating deployment, enterprise SAML/OIDC IAM | Advanced research features reserved for post-MVP roadmap. |

---

## 2. Phased Implementation Roadmap

### Phase 0: Workspace Discovery & Baseline Verification [COMPLETED]
- [x] Comprehensive workspace audit (`docs/CURRENT_SYSTEM_AUDIT.md`).
- [x] Verification of existing backend smoke tests and orchestrator variants.
- [x] Verification of ChromaDB indexing pipeline (35 documents indexed).
- [x] Verification of frontend tests (43 passed tests across 6 tiers) and Vite build.
- [x] Verification of live localhost daemons (`http://localhost:8000` and `http://localhost:3000`).

### Phase 1: Evaluation Foundation & Ground-Truth Scenarios
- Create `backend/evaluation/` harness.
- Formulate ground-truth incident scenarios (symptoms, true root cause, valid remediation, dangerous action, expected blast radius, recovery target).
- Define quantitative evaluation metrics: Recall@k, Root Cause Accuracy, Unsafe Action Prevention Rate, False Block Rate, MTTR.

### Phase 2: State & Topology Engine (`backend/topology/`)
- Implement multi-tier dependency graph modeling (API Gateway → Auth / Orders / Payments → Databases / Caches).
- Implement downstream path traversal and critical path identification.
- Implement graph-based blast radius calculation function ($0 - 100$ score and human-readable explanation).

### Phase 3: Counterfactual Digital Twin (`backend/twin/`)
- Implement shadow state cloner (in-memory abstract infrastructure state).
- Implement candidate action applicator (simulate DB restart, service termination, replica cuts).
- Implement downstream backpressure and cascade simulator.
- Output predicted SLO impact, affected nodes, and reversibility flag.

### Phase 4: CORTEX Guard & Governance Engine (`backend/cortex/`)
- Implement deterministic policy engine (Policy-as-Code).
- Implement capability contract envelopes per incident/actor.
- Implement action risk classifier (dynamic context-based: service criticality, redundancy, traffic).
- Implement approval gate manager with TTL expiration (120s) and human decision recording.
- Implement tamper-evident hash chaining for security-sensitive events.

### Phase 5: Workload Forecast Engine & Anomaly Detection (`backend/forecasting/`)
- Generate realistic time-series workload patterns (diurnal cycles, flash crowds, gradual drift).
- Implement 5m, 15m, and 30m horizon forecasting models with confidence/uncertainty intervals.
- Implement adaptive capacity reserve controller.
- Implement Isolation Forest anomaly detector across CPU, RAM, RPS, and latency.

### Phase 6: Multi-Objective Optimizer (`backend/optimization/`)
- Implement composite scoring function: Cost, Latency Penalty, Reliability Risk, SLO Risk, Energy Estimate, Change Risk.
- Implement Pareto frontier generator to isolate non-dominated configurations.
- Implement operating mode selector: `BALANCED`, `COST`, `PERFORMANCE`, `RELIABILITY`, `GREEN`, `EMERGENCY`.

### Phase 7: Closed-Loop Verification & Automated Rollback (`backend/verification/`)
- Implement post-action telemetry observation with configurable settling period.
- Compare pre-action and post-action SLO compliance.
- Classify outcomes: `RECOVERED`, `PARTIALLY_RECOVERED`, `NO_CHANGE`, `WORSE`.
- Implement automatic rollback trigger upon degradation.

### Phase 8: Unified Control Plane & API Synchronization (`backend/api/`)
- Refactor `api_server.py` to route all operations through CORTEX Guard and the full orchestrator.
- Expose endpoints for `/api/topology`, `/api/forecast`, `/api/twin/simulate`, `/api/optimizer`, `/api/cortex/policies`, `/api/cortex/approvals`, and `/api/chaos/inject`.
- Implement Server-Sent Events (SSE) or WebSocket streaming for real-time UI updates.

### Phase 9: Three-Layer Frontend Command Center (`frontend/src/`)
- Scaffold ShadcnStore components (data-table, dialog, sheet, command, tabs, sonner).
- **Layer 1:** Build the 15-section cinematic Landing Page (`/`) with interactive Hero topology, live status rail, and scroll-driven control loop.
- **Layer 2:** Build the Operations Command Center (`/console`) with live React Flow graph, CORTEX decision card, and active timeline.
- **Layer 3:** Build dedicated deep analysis pages (`/incidents`, `/topology`, `/predictions`, `/optimizer`, `/cortex`, `/simulator`, `/approvals`, `/policies`, `/chaos`, `/reliability`, `/cost`, `/audit`, `/evaluation`, `/demo`).
- Wire Global Command Palette (`Cmd/Ctrl + K`), Incident Drawer, and Service Inspector.

### Phase 10: Verification, Chaos Testing & Final Documentation
- Run automated chaos test suite (fault injection → detection → diagnosis → simulation → approval → action → verification → recovery).
- Run full regression tests (backend pytest + frontend tsx test runner).
- Verify end-to-end user journeys in the browser.
- Produce final documentation suite (`README.md`, `ARCHITECTURE.md`, `DEMO.md`, `EVALUATION.md`, `SECURITY.md`).
