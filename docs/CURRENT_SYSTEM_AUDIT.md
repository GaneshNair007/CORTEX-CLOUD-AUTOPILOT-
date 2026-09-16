# CORTEX CLOUD AUTOPILOT — Current System Audit
**Repository:** `https://github.com/GaneshNair007/agentic_ops`  
**Target Repository:** `https://github.com/GaneshNair007/CORTEX-CLOUD-AUTOPILOT-`  
**Date:** September 16, 2026  
**Auditor:** CORTEX Control Plane Architecture Team  

---

## 1. Executive Summary

The existing repository (`agentic_ops`) implements an initial prototype of an AI Site Reliability Engineer (AI SRE) copilot. It features:
1. A dense vector retrieval system (ChromaDB + SentenceTransformers `all-MiniLM-L6-v2`) over 20 incident reports and 15 operational runbooks.
2. An agentic reasoning loop (`orchestrator/agent.py`) that performs hypothesis generation, self-critique, confidence scoring, confidence gating, action execution, and memory persistence.
3. A mock action engine (`tools/actions.py`) supporting 8 remediation operations with JSON Lines audit logging.
4. A thread-safe event bus (`tools/event_bus.py`) persisting timeline events to `tools/events.jsonl`.
5. A FastAPI backend (`api_server.py`) exposing REST endpoints for retrieval, action dispatch, event logging, and a streamlined incident pipeline.
6. A Streamlit interactive dashboard (`app.py`) for live incident simulation and knowledge inspection.
7. A React 19 + TypeScript + Vite frontend (`frontend/`) featuring an SRE console with 43 automated tests across 6 tiers.

While the conceptual pipeline (Incident → Retrieve → Hypothesize → Self-Critique → Confidence Gate → Act → Remember) is sound, the underlying execution is simulated. The API server bypasses the agentic orchestrator, actions lack dependency awareness, safety guardrails are hardcoded, and there is no predictive forecasting or digital twin simulation.

---

## 2. Component Inspection & Current State

### 2.1 Backend Architecture (`backend/`)

| Module | Files | Status | Observations |
| :--- | :--- | :--- | :--- |
| **API Server** | `api_server.py` | Working (Disjoint) | Exposes FastAPI endpoints. However, `/api/pipeline/run` completely bypasses `orchestrator/agent.py` and uses trivial string matching (`if "database" in symptom.lower()`) to pick actions. |
| **Streamlit App** | `app.py` | Working | 4-tab interactive dashboard providing live simulation, vector memory querying, mock action console, and audit logs. |
| **Frozen Interfaces** | `interfaces.py` | Working | Exports `retrieve`, `remember`, `execute_action`, `emit_event` with fallback to keyword-overlap store. |
| **Orchestrator** | `orchestrator/agent.py`, `orchestrator/test_variants.py` | Working (Stand-alone) | Implements hypothesis generation, self-critique, and confidence extraction. Tested against 5 variant incidents. |
| **RAG Engine** | `rag/build_index.py`, `rag/retrieve.py`, `rag/store.py` | Working (Requires Index) | ChromaDB index persists to `rag/chroma_db/`. Fallback in `rag/store.py` uses token overlap against `backend/data/*.json`. |
| **Tools & Event Bus** | `tools/actions.py`, `tools/event_bus.py` | Working (Simulated) | Actions simulate 80–450ms latency and append to `tools/audit.log`. Event bus writes to `tools/events.jsonl` with threading lock. |
| **LLM Client & Router**| `llm/client.py`, `llm/router.py`, `llm/test_batch.py` | Working | Supports `mock` and `ollama` modes. Includes batching tests and complexity routing (`routine` vs `complex`). |

### 2.2 Frontend Architecture (`frontend/`)

| Directory / Layer | Tech Stack | Status | Observations |
| :--- | :--- | :--- | :--- |
| **UI Framework** | React 19, TypeScript 5.8, Vite 6.4 | Working & Tested | Production build passes in ~18s (`dist/`). |
| **Styling & Animation**| Tailwind CSS 4, GSAP 3.15, Lenis, Framer Motion | Working | Highly styled monochrome dark theme with custom portal animations. |
| **API Client** | `src/services/api.ts` | Working | Strongly typed client talking to `VITE_API_URL` or Render fallback (`https://agentic-ops-1.onrender.com/api`). |
| **Test Suite** | `tests/run_tests.ts` via `tsx` | 43 / 43 Passing | Covers CSS tokens, JSON serialization resilience, circular references, tag normalization, and incident scenarios. |

---

## 3. What Currently Works vs What is Mocked

### What Currently Works:
- Dense vector retrieval with ChromaDB across 35 technical documents (20 incidents, 15 runbooks).
- Keyword overlap fallback when ChromaDB is absent.
- Incident agent reasoning cycle with regex-based confidence extraction and self-critique discounting.
- Memory store persistence (`data/memory_store.jsonl`) appending resolved incidents.
- Thread-safe event bus with ISO timestamps and UUID v4 identifiers.
- Parameter validation for 8 predefined actions (`restart_service`, `rollback_deployment`, `restart_pod`, `restart_database`, `scale_deployment`, `create_ticket`, `notify_team`, `generate_postmortem`).
- End-to-end frontend build, typechecking, and test suite execution (43 test specs passing).

### What is Mocked / Simulated:
- **Infrastructure Execution:** All 8 actions in `tools/actions.py` return synthetic success messages after a `random.randint(80, 450)` millisecond delay. No actual Docker containers, Kubernetes pods, or cloud instances are mutated.
- **LLM Generation:** Defaults to `LLM_MODE=mock`, returning static canned strings for hypothesis and critique.
- **Telemetry:** In the UI, telemetry spikes (e.g. RPS, error rates, p99 latency) are hardcoded static numbers or simulated transitions, not real OpenTelemetry or Prometheus metrics.
- **Pipeline Orchestration in API:** The `/api/pipeline/run` endpoint is completely decoupled from the LLM and orchestrator, executing deterministic heuristics and immediate fake actions.

---

## 4. Architectural Gaps & Technical Debt

1. **Disconnected Control Flow:** `api_server.py` does not invoke `IncidentAgent` from `orchestrator/agent.py`. The web interface and backend API run a simplified mock rather than the true agentic self-critique loop.
2. **Absence of Infrastructure Topology:** The system has no concept of dependency graphs (e.g., Service → Database → Redis → Network Route). A database restart has no modeled blast radius.
3. **No Counterfactual Simulation (Digital Twin):** Actions are dispatched blindly without pre-flight simulation or impact prediction on downstream SLOs.
4. **No Multi-Objective Optimization:** Scale and remediation decisions lack scoring across cost, latency, reliability, carbon/energy, and change risk.
5. **No Workload Forecasting:** Scaling is purely reactive to static thresholds rather than predictive scale-ahead with uncertainty bounds.
6. **No Post-Action Verification:** The system assumes returning HTTP 200 / `status: "success"` guarantees remediation. It never measures post-action telemetry or checks whether SLOs actually recovered.
7. **No Automated Rollback on Degradation:** If a remediation makes a system state worse, there is no closed-loop mechanism to trigger a rollback.
8. **No Distributed Locking or Idempotency Keys:** Duplicate requests can trigger conflicting concurrent mutations (e.g., simultaneous scale-up and scale-down).
9. **Single Identity Execution:** All actions execute with an implicit monolithic agent identity; no user attribution or capability envelope exists.
10. **Fragile Action Gating:** Action risk is a static 4-item dictionary (`ACTION_RISK = {"restart_service": "low", "rollback_deployment": "high", ...}`). It does not account for environment, service tier, traffic volume, or replica availability.

---

## 5. Security & Reliability Vulnerabilities

| Vulnerability | Severity | Description |
| :--- | :--- | :--- |
| **Unauthenticated Mutating Endpoints** | **CRITICAL** | `POST /api/tools/action` allows arbitrary callers to trigger critical actions (including database restarts and deployment rollbacks) without auth tokens or identity checks. |
| **Prompt Injection via Retrieval** | **HIGH** | Retrieved RAG documents are concatenated directly into LLM prompts without isolation or boundary delimitation, allowing adversarial incident documents to inject instructions. |
| **Direct AI Mutation Code Path** | **HIGH** | If enabled with real LLM, an unconstrained LLM output could directly trigger execution without an independent deterministic policy gate. |
| **Lack of Action Idempotency** | **MEDIUM** | Network retries to `/api/tools/action` will execute multiple times, creating potential oscillation or duplicate disruptions. |
| **Tamperable Audit Trail** | **MEDIUM** | `tools/audit.log` is a plain text JSONL file with no hash chaining or integrity verification. |
| **Observability Coupling** | **MEDIUM** | The control plane assumes monitoring data is always available; there is no `OBSERVABILITY_DEGRADED` fallback mode when metrics fail. |

---

## 6. Current Test Coverage & Verification Baseline

- **Backend Pytest:**
  - `orchestrator/test_variants.py`: 2 test functions (`test_parser_robustness`, `test_low_confidence_gating`) passing.
  - 5 variant incident runs passing in mock mode.
  - `llm/test_batch.py`: Batch evaluation passing.
- **Frontend TSX Runner:**
  - 43 tests passing across Tier 1 (conformance), Tier 2 (boundary), Tier 3 (integration), Tier 4 (SRE scenarios), ADV (adversarial stress), Tier 6 (hero & responsive).
- **Build Verification:**
  - `npm run lint` (`tsc --noEmit`): Clean (0 errors).
  - `npm run build`: Vite production bundle compiles successfully in 17.9s.

---

## 7. Conclusion & Evolution Path

The existing codebase provides a solid prototype foundation—specifically its vector RAG pipeline, self-critique agent loop, event bus, and comprehensive frontend UI. 

To evolve this into **CORTEX Cloud Autopilot**, we must:
1. Reconnect the FastAPI control plane to a unified, deterministic policy and agent engine.
2. Build a local microservices cloud sandbox (Docker / Containerized) with real HTTP, health, and Prometheus telemetry.
3. Introduce the **State & Topology Graph** to model dependencies and compute blast radius.
4. Implement the **Dependency-Aware Counterfactual Digital Twin** for pre-execution impact simulation.
5. Create **CORTEX Guard** with capability contracts, temporal policies, and human approval gates.
6. Add **Workload Forecasting** (5m, 15m, 30m) with uncertainty estimation and hybrid predictive autoscaling.
7. Enforce **Closed-Loop Post-Action Verification** with automatic rollback upon degradation.
8. Implement an **Immutable Hash-Chained Evidence Ledger** for audit integrity.
