# CORTEX CLOUD AUTOPILOT — Target System Architecture
**Document:** `docs/TARGET_ARCHITECTURE.md`  
**Date:** September 16, 2026  
**Status:** Approved Engineering Blueprint  

---

## 1. System Vision & Core Operating Loop

CORTEX Cloud Autopilot is a predictive, policy-governed autonomous cloud control plane that answers the continuous operational question:
> *Given the current infrastructure state, predicted workload, service objectives, dependency graph, cloud cost, failure risk, and security policy: what infrastructure configuration or remediation should be performed—if any—and can we prove it is safe enough before acting?*

The system replaces the legacy reactive automation model (`Alarm → Rule/AI → Mutate`) with an engineered 10-stage closed-loop architecture:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        THE CORTEX CONTROL LOOP                          │
├─────────┬────────────┬─────────┬──────────┬──────────┬───────────┬─────┤
│ OBSERVE │ UNDERSTAND │ PREDICT │ SIMULATE │ OPTIMIZE │ AUTHORIZE │ ACT │
└────┬────┴─────┬──────┴────┬────┴────┬─────┴────┬─────┴─────┬─────┴──┬──┘
     │          │           │         │          │           │        │
     ▼          ▼           ▼         ▼          ▼           ▼        ▼
 Telemetry   Causal RAG  Workload  Shadow Twin  Pareto    CORTEX Guard Progressive
 Multi-Mesh  Self-Crit   Forecast  Blast Radius Scoring   Enforcement  Rollout
     │
     └───────────────────────────────┬───────────────────────────────┘
                                     ▼
                                  VERIFY
                          Closed-Loop SLO Check
                                     │
                                     ▼
                                   LEARN
                        Tamper-Evident Memory Ledger
```

---

## 2. High-Level Architecture Diagram

```
                             OPERATORS / SREs
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  CORTEX COMMAND UI  │
                         │  (Vite+React 19)    │
                         └──────────┬──────────┘
                                    │ REST / SSE
                                    ▼
                         ┌─────────────────────┐
                         │  API / CONTROL PLANE│
                         │  (FastAPI Daemon)   │
                         └──────────┬──────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌───────────────┐           ┌───────────────┐            ┌───────────────┐
│ OBSERVABILITY │           │ INCIDENT BRAIN│            │FORECAST ENGINE│
│ TelemetryMesh │           │ Vector RAG    │            │ 5m/15m/30m ML │
│ Health Probes │           │ Self-Critique │            │ Uncertainty   │
│ Degraded State│           │ Pydantic Triage            │ Anomaly Detect│
└───────┬───────┘           └───────┬───────┘            └───────┬───────┘
        │                           │                            │
        └───────────────────────────┼────────────────────────────┘
                                    ▼
                        ┌───────────────────────┐
                        │ STATE / TOPOLOGY GRAPH│
                        │ Multi-Tier Dependency │
                        │ Critical Path Mapping │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ COUNTERFACTUAL TWIN   │
                        │ Shadow State Cloner   │
                        │ Blast Radius Estimator│
                        │ Downstream SLO Impact │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ MULTI-OBJ OPTIMIZER   │
                        │ Cost vs Latency vs Risk│
                        │ Pareto Frontier Engine│
                        │ Operating Modes       │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │     CORTEX GUARD      │
                        │ Policy Engine         │
                        │ Capability Envelope   │
                        │ Blast Radius Gate     │
                        │ Approval Interceptor  │
                        └───────────┬───────────┘
                                    │
                    ALLOW / CONSTRAIN / APPROVE / BLOCK
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ CONTROLLED EXECUTION  │
                        │ Progressive Rollout   │
                        │ Idempotency & Locks   │
                        │ Docker / K8s Adapters │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   POST VERIFICATION   │
                        │ Pre/Post Telemetry    │
                        │ Automated Rollback    │
                        │ Escalation Protocol   │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ EVIDENCE LEDGER & RAG │
                        │ Hash-Chained Audit Log│
                        │ Memory Write-Back     │
                        └───────────────────────┘
```

---

## 3. Subsystem Specifications

### 3.1 Observability Mesh & Out-of-Band Health (`backend/observability/`)
* **Primary Telemetry:** Collects RPS, p50/p95/p99 latency, error rates, CPU/memory saturation, queue depths, and pod replica states via OpenTelemetry and Prometheus standards.
* **Secondary Out-of-Band Probes:** Independent synthetic HTTP health checks that ping services directly without passing through intermediary telemetry aggregators.
* **Observability Degraded State:** If primary metric feeds stall or diverge from synthetic probes, the system immediately asserts `OBSERVABILITY_DEGRADED`. Under this state, autonomous execution permissions are revoked, and all mutations require explicit human approval.

### 3.2 Incident Brain & Structured Reasoning (`backend/incidents/`, `backend/rag/`, `backend/llm/`)
* **Deterministic Correlation:** Symptoms (e.g., 504 spikes, connection timeouts) are first correlated deterministically via rules and threshold triggers before invoking AI models.
* **Evidence Retrieval:** ChromaDB vector index (`rag/retrieve.py`) fetches top-k runbooks and past incidents with source metadata, cosine similarity scores, and trust ratings.
* **Validated Structured Output:** LLM outputs must strictly validate against Pydantic models (`RootCauseHypothesis`, `RemediationProposal`). Malformed schemas trigger immediate rejection (`REJECT`).
* **Self-Critique & Abstention:** A secondary prompt acts as a skeptical senior SRE seeking counter-evidence. If revised confidence falls below `0.60`, the system formally asserts `INSUFFICIENT_EVIDENCE` and withholds autonomous execution.

### 3.3 Workload Forecast Engine & Adaptive Reserve (`backend/forecasting/`)
* **Horizon Forecasting:** Predicts demand curves at 5-minute, 15-minute, and 30-minute horizons using moving averages, baseline trend models, and gradient boosting (XGBoost/LightGBM).
* **Uncertainty Bounds:** Every forecast output includes a confidence band `[\hat{y} - \sigma, \hat{y} + \sigma]`. High variance reduces autonomous authority.
* **Adaptive Capacity Reserve:** Maintains dynamic capacity buffers based on forecast uncertainty, container startup latency, and recent volatility (e.g., 5% reserve during stable workloads, 25% during volatile regimes).
* **Hybrid Scale Controller:** Fast reactive HPA serves as the baseline safety floor, while CORTEX predictive scaling scales out ahead of demand.

### 3.4 State & Topology Graph (`backend/topology/`)
* **Graph Representation:** Directed acyclic graph (DAG) modeled in NetworkX capturing services, API gateways, databases, caches, queues, and network routes.
* **Blast Radius Calculation:** Computes the blast radius of any mutating operation:
  $$\text{BlastRadius} = \sum_{n \in \text{Downstream}(v)} \text{Criticality}(n) \times \text{DependencyWeight}(v, n)$$
  Returns both a normalized numeric score (0–100) and an explainable list of impacted paths.

### 3.5 Counterfactual Digital Twin (`backend/twin/`)
* **Shadow State Cloner:** Clones an in-memory snapshot of current infrastructure state without altering live production.
* **Impact Propagation:** Applies the candidate action (e.g., restart node, cut replicas, restart database) to the shadow state, evaluates upstream backpressure, and projects expected SLO violations and recovery times.
* **Reversibility Assessment:** Assesses whether the candidate mutation can be safely rolled back in under 30 seconds.

### 3.6 Multi-Objective Optimizer (`backend/optimization/`)
Evaluates candidate configurations against a composite objective function subject to hard constraints:
$$\text{CostObjective} = w_c \cdot \text{Cost} + w_l \cdot \text{LatencyPenalty} + w_r \cdot \text{ReliabilityRisk} + w_s \cdot \text{SLORisk} + w_e \cdot \text{EnergyEst} + w_x \cdot \text{ChangeRisk}$$
* **Hard Constraints:** Availability $\ge \text{Target}$; Capacity $\ge \text{Forecast Demand} + \text{Reserve}$; Budget $\le \text{Configured Limit}$.
* **Pareto Frontier:** Identifies non-dominated candidate configurations and selects the optimal candidate based on the active operating mode:
  * `BALANCED`: Equalized trade-off between cost, performance, and risk.
  * `COST`: Aggressive rightsizing while strictly respecting hard SLO limits.
  * `PERFORMANCE`: Maximizes headroom and minimizes p99 latency.
  * `RELIABILITY`: Maximizes redundancy and preserves failover replicas.
  * `GREEN`: Minimizes estimated energy and regional carbon intensity.
  * `EMERGENCY`: Bypasses cost constraints to restore degraded availability.

### 3.7 CORTEX Guard & Governance Engine (`backend/cortex/`)
* **Zero Direct AI Mutation:** No LLM output ever communicates directly with cloud infrastructure.
* **Capability Contracts:** Dynamically generates an execution envelope per incident specifying allowed actions, required approval actions, and blocked actions.
* **Temporal Sequence Policies:** Prevents unsafe sequences of operations over time (e.g., "cannot execute scale-down within 15 minutes of scale-up on the same service").
* **Risk-Adaptive Autonomy:**
  * *Level 0 (Observe):* Telemetry and monitoring only.
  * *Level 1 (Recommend):* AI produces recommendations; human operator executes.
  * *Level 2 (Guarded):* Low-risk actions auto-execute; medium/high-risk require human approval.
  * *Level 3 (Autonomous):* Bounded set of high-confidence actions execute autonomously within pre-verified blast radius limits.
* **Emergency Kill Switch:** Global hardware/software kill switch that immediately freezes all mutating operations while allowing read-only triage to continue.

### 3.8 Controlled Execution & Progressive Rollout (`backend/execution/`)
* **Staged Rollout Pipeline:**
  $$\text{Proposed} \longrightarrow \text{Shadow Sim} \longrightarrow \text{Canary (1 replica)} \longrightarrow \text{Verify} \longrightarrow 10\% \longrightarrow \text{Verify} \longrightarrow 100\%$$
* **Idempotency & Distributed Locking:** Every mutation requires an `operation_id` and `idempotency_key`. Concurrent conflicting operations on the same service are locked and rejected.
* **Provider Adapters:** Clean interface abstraction (`CloudProvider`) with implementations for Local Docker/Sandbox, Kubernetes API, and simulated AWS/Azure/GCP adapters.

### 3.9 Closed-Loop Verification & Rollback (`backend/verification/`)
* **Mandatory Settling Period:** After dispatching an action, the verifier waits for a configured settling window (10–30s).
* **Pre/Post Telemetry Delta:** Compares error rates, latency, and throughput before and after the action.
* **Outcome States:** Classified into `RECOVERED`, `PARTIALLY_RECOVERED`, `NO_CHANGE`, `WORSE`, or `UNKNOWN`.
* **Automatic Rollback:** If telemetry shows `WORSE` or triggers a critical SLO breach, the verifier immediately executes the pre-computed rollback plan.

### 3.10 Tamper-Evident Evidence Ledger (`backend/audit/`, `backend/memory/`)
* **Append-Only Event Sourcing:** Every incident event, proposal, risk score, approval, mutation, and verification is recorded as an immutable JSONL event.
* **Cryptographic Hash Chaining:**
  $$\text{Hash}_i = \text{SHA-256}(\text{Event}_i \,||\, \text{Hash}_{i-1})$$
  Ensures the audit log cannot be modified or truncated without detection.
* **Operational Memory:** Verified incident resolutions are written back to the RAG memory store (`data/memory_store.jsonl`) to accelerate future triage.

---

## 4. Architectural Invariants (Enforced by Automated Tests)

1. **AI Isolation Invariant:** An AI model cannot invoke cloud APIs or execute shell commands directly. All actions pass through CORTEX Guard.
2. **Blocked Action Invariant:** Any action classified as `BLOCK` by CORTEX Guard cannot reach the execution layer under any condition.
3. **Approval Invariant:** Actions marked `REQUIRE_APPROVAL` cannot execute without an authentic human cryptographic token.
4. **Idempotency Invariant:** Submitting the same `operation_id` multiple times produces exactly one infrastructure mutation.
5. **Audit Invariant:** Every mutating operation emits a corresponding audit ledger event before and after execution.
6. **Verification Invariant:** No remediation can be classified as `SUCCESS` without quantitative telemetry proving SLO recovery.
7. **Decision Expiry Invariant:** An authorization decision older than its Time-To-Live (TTL = 120s) expires and cannot be executed without re-evaluation.
8. **Observability Fallback Invariant:** If telemetry is unavailable or degraded, the system automatically lowers autonomy to Level 1 (Recommend).
