# CORTEX CLOUD AUTOPILOT
## Frontend Architecture & Migration Plan
**Foundation:** ShadcnStore Dashboard + Landing Page Template (Vite + React + TypeScript + Tailwind CSS)  
**Target Repository:** `https://github.com/GaneshNair007/CORTEX-CLOUD-AUTOPILOT-`  
**Date:** September 16, 2026  
**Status:** Approved Architectural Blueprint  

---

## 1. Executive Summary & Design Philosophy

The current frontend (`frontend/src`) implements an initial single-page dark-themed SRE console built with React 19, TypeScript, Tailwind CSS 4, GSAP, Lenis smooth scrolling, and an Express proxy server (`server.ts`). While visually striking with custom portal animations, its flat architecture forces disparate operational concepts into one long scroll or modal dialogs.

The new frontend architecture will migrate to a **Three-Layer Enterprise Cloud Control Plane** structured on top of the **ShadcnStore Dashboard + Landing Page Template (Vite version)**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CORTEX CLOUD AUTOPILOT                          │
├───────────────────┬──────────────────────────┬─────────────────────────┤
│ LAYER 1           │ LAYER 2                  │ LAYER 3                 │
│ Public Story      │ Operations Command       │ Deep Analysis Suites    │
│ (Landing Page)    │ (/console)               │ (/incidents, /topology, │
│ Cinematic Product │ Real-time Infrastructure │ /simulator, /cortex,    │
│ Explanation & Wow │ Graph & Active Decision  │ /optimizer, /chaos...)  │
└───────────────────┴──────────────────────────┴─────────────────────────┘
```

### Visual Direction & Aesthetics
* **Palette:** Ultra-clean monochrome foundation: `#09090b` (Deep Charcoal Background), `#18181b` (Surface Dark), `#27272a` (Border 1px Structural), `#fafafa` (Text Primary), `#a1a1aa` (Text Muted).
* **Strict Functional Accents Only:**
  * `Emerald (#10b981)`: Healthy state, Verified recovery, Action allowed.
  * `Amber (#f59e0b)`: Approvals required, Warning, Latency approaching SLO.
  * `Rose (#f43f5e)`: Blocked action, Critical incident, Circuit breaker trip.
  * `Sky (#0ea5e9)`: Workload forecast, Predictive scaling, Counterfactual simulation.
* **Typography:** `Geist Sans` / `Inter` for technical display hierarchy, `Geist Mono` / `JetBrains Mono` for telemetry, metrics, and code.
* **Motion with Purpose:** GSAP and Framer Motion are reserved for communicating *system behaviour*—request flow across nodes, failure cascades through dependencies, prediction curves advancing beyond real-time, and rollback direction reversal.

---

## 2. Layer 1 — The Public Product Story (Landing Page: `/`)

The landing page tells a cinematic story of why closed-loop autonomous cloud operations are necessary without overwhelming the user with raw dashboards.

| Section | Identifier | Core Visual & Interactive Component | Backend / Data Connection |
| :--- | :--- | :--- | :--- |
| **01. Hero** | `HeroTopologySection` | Interactive live 8-service dependency graph with animated request particles. Live status rail showing 99.96% health. Dynamic narrative: Payment Load surge → Forecast +42% → Candidate scale 6→9 → CORTEX ALLOW → Latency restores. | Topology graph state, Real-time status stream. |
| **02. Why CORTEX** | `WhyCortexSection` | Fullscreen sequential scenes: (1) Reactive Scaling & SLO breach, (2) Blind Remediation (`restart_database` cascade), (3) Fragmented cloud intelligence convergence into CORTEX. | Ground-truth incident database (`rag/data/incidents/`). |
| **03. The Control Loop** | `ControlLoopSection` | Horizontal scroll illumination across all 9 stages: `Observe → Understand → Predict → Simulate → Optimize → Authorize → Act → Verify → Learn`. | Orchestrator pipeline lifecycle events. |
| **04. Observe** | `ObserveSection` | Live telemetry ribbon displaying multi-signal ingestion: CPU, RAM, RPS, p95/p99 latency, error rates, dependency health. | OpenTelemetry / Prometheus metric stream. |
| **05. Understand** | `UnderstandSection` | Incident forensic breakdown: Incident `INC-1042` with animated evidence lines linking Runbooks and historical postmortems to AI root-cause hypothesis and self-critique. | RAG retrieval (`/api/rag/retrieve`) + ChromaDB. |
| **06. Predict** | `PredictSection` | Interactive workload chart: solid line (actual traffic), dashed line with uncertainty band (predicted 30m), SLO boundary, action window countdown. | Forecast Engine (XGBoost / baseline models). |
| **07. Simulate** | `SimulateSection` | Counterfactual Digital Twin interactive explorer: toggle `SIMULATE` on proposed DB restart to watch dependency graph enter shadow state, illuminating 5 affected downstream services and calculating a 91/100 blast radius. | Digital Twin simulation engine. |
| **08. Optimize** | `OptimizeSection` | Multi-objective Pareto frontier comparison (6 pods vs 8 pods vs 10 pods) across Cost, Latency, Risk, and SLOs with mode toggle (`Balanced`, `Cost`, `Performance`, `Reliability`, `Green`). | Multi-objective optimizer. |
| **09. Authorize** | `AuthorizeSection` | CORTEX Guard security gate: Action proposal passing through Capability contract, Identity verification, Policy check, Blast radius filter, and Approval requirement. | CORTEX Guard policy engine. |
| **10. Act** | `ActSection` | Staged progressive rollout visualization: `Shadow → Canary 1 → Verify → 10% → Verify → 100%`, showing automatic rollback reversal upon simulated degradation. | Progressive rollout controller. |
| **11. Verify** | `VerifySection` | Split-screen Before vs After telemetry verification (Errors 28% → 1.7%, p95 812ms → 143ms, CPU 94% → 48%) proving closed-loop recovery. | Post-action verification engine. |
| **12. Learn** | `LearnSection` | Operational memory lineage: connecting historical incident `INC-088` resolution to new incident `INC-1042` via vector similarity. | Vector memory store (`data/memory_store.jsonl`). |
| **13. Chaos Lab** | `ChaosLabSection` | Interactive fault injection console: trigger Kill Pod, CPU Saturation, Network Latency, or DB Outage and observe real-time MTTR timeline. | Chaos experiment harness. |
| **14. Research / Results**| `EvaluationSection` | Empirically measured benchmarks: Recall@k, Root Cause Accuracy, Unsafe Action Prevention Rate, MTTR, comparing Static vs HPA vs CORTEX. | Evaluation harness benchmark logs. |
| **15. Final CTA** | `FinalCtaSection` | High-impact call to action: `Launch Command Center` (`/console`) and `Watch Autonomous Incident Demo` (`/demo`). | Navigation triggers. |

---

## 3. Layer 2 — Operations Command Center (`/console`)

The primary operations cockpit designed for live site reliability engineers and operators:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TOP STATUS RAIL: Health 99.95% | Autonomy: GUARDED | Incidents: 2     │
├───────────────────────────────────────────┬────────────────────────────┤
│ LIVE INFRASTRUCTURE TOPOLOGY GRAPH        │ CURRENT CORTEX DECISION    │
│                                           │                            │
│   API Gateway ──┬── Auth ── Redis         │ Incident: INC-1042         │
│                 ├── Orders ── DB          │ Proposal: Rollback v4.6    │
│                 └── Payments ── DB        │ Risk: 63/100 (Moderate)    │
│                                           │ Blast Radius: 3 Services   │
│ (React Flow graph with live traffic glow, │ Decision: [REQUIRE APPROV] │
│  health node borders, click-to-inspect)   │ Evidence: RB-001, INC-005  │
├───────────────────────────────────────────┴────────────────────────────┤
│ LOWER TELEMETRY & EVENT STRIP                                          │
│ [30-Min Forecast Ribbon]   [Active Incident Timeline]   [Verification] │
└────────────────────────────────────────────────────────────────────────┘
```

* **Top Status Rail:** Global health status, active autonomy level, active incident count, SLO compliance, estimated hourly run rate, and CORTEX guard state.
* **Main Left/Center:** Interactive Infrastructure Graph built with React Flow, displaying service nodes, database clusters, caches, message queues, and dependency arrows with animated request flows. Clicking any node opens the **Global Service Inspector**.
* **Right Panel:** Live CORTEX Decision Card detailing current proposals, risk assessment, calculated blast radius, counterfactual evaluation, and required approvals.
* **Lower Strip:** Workload forecast band, real-time event bus timeline, and pre/post action verification metrics.

---

## 4. Layer 3 — Deep Analysis Suites (Dedicated Routes)

All specialized investigative features live in dedicated, purpose-built pages using ShadcnStore data tables, sheet drawers, and dialog primitives:

1. **`/incidents` (Incident Command & Forensic Detail):**
   * Advanced TanStack data table of all historical and active incidents (ID, Timestamp, Service, Severity, Root Cause, Confidence, Decision, Recovery, MTTR).
   * Detailed Incident View: Summary, telemetry snapshot, retrieved RAG evidence cards, LLM hypothesis, self-critique rebuttal, proposed actions, and complete event timeline.
2. **`/topology` (Full-Screen Dependency Graph):**
   * Fullscreen topology explorer with filters (Region, AZ, Service Tier, Health, Criticality).
   * **Blast Radius Simulation Mode:** Select any service or database mutation to visualize the reach of potential outages across the downstream dependency graph.
3. **`/predictions` (Workload Forecast Engine):**
   * Actual vs predicted request rates, CPU, and memory across 5-minute, 15-minute, and 30-minute horizons.
   * Uncertainty bounds, SLO breach probability, and model evaluation metrics (MAE, RMSE).
4. **`/optimizer` (Multi-Objective CloudPilot):**
   * Interactive Pareto Frontier charting Cost vs Latency vs Risk.
   * Candidate infrastructure configurations (e.g., 6 pods vs 8 pods vs 11 pods) scored against competing objectives.
   * Mode toggles: `Balanced`, `Cost`, `Performance`, `Reliability`, `Green`.
5. **`/memory` (Incident Knowledge Base & RAG):**
   * Searchable semantic index over past incidents and operational runbooks.
   * Relevance scores, tag filtering, full markdown viewer, and memory write-back inspector.
6. **`/cortex` (CORTEX Guard & Live Interception Stream):**
   * Autonomy level switcher (Level 0: Observe, Level 1: Recommend, Level 2: Guarded, Level 3: Autonomous).
   * Live interception stream: inspect incoming proposals and policy evaluations (`ALLOW`, `CONSTRAIN`, `APPROVE`, `BLOCK`).
   * Capability contracts and provenance trust scoring.
7. **`/simulator` (Dependency-Aware Counterfactual Digital Twin):**
   * Side-by-side comparison of `Current State` vs `Shadow Simulated State`.
   * Action builder allowing operators to simulate any mutation (e.g., node drain, DB restart, replica cut) before execution.
8. **`/approvals` (Human-in-the-Loop Governance Queue):**
   * Pending high-risk actions requiring human authorization.
   * Displays full context: AI proposal, why proposed, confidence, blast radius, expected latency change, and safer alternatives with 1-click `Approve`, `Reject`, or `Simulate`.
9. **`/policies` (Policy-as-Code Engine):**
   * Version-controlled policy rules (e.g., "Production DB restart requires approval if failover unavailable", "Cannot scale below SLO reserve").
   * Interactive policy tester and rule validator.
10. **`/chaos` (Chaos Engineering Lab):**
    * Controlled fault injection presets: Pod Kill, CPU Saturation, Network Delay (300ms), DB Connection Failure, 10x Traffic Spike.
    * Live telemetry and MTTR stopwatch measuring detection, diagnosis, authorization, action, and recovery times.
11. **`/reliability` (SLO & Error Budget Management):**
    * Service reliability tracking, p95/p99 targets vs actuals, error budget burn rates, and multi-window burn rate alerts.
12. **`/cost` (FinOps Intelligence & Cost Guardrails):**
    * Real-time estimated spend, candidate state cost comparisons, monthly projections, and budget conflict alerts.
13. **`/sustainability` (Green Cloud & Carbon Modeling):**
    * Estimated compute energy (kWh), regional carbon intensity, and capacity efficiency metrics for GREEN optimization mode.
14. **`/audit` (Tamper-Evident Evidence Ledger):**
    * Immutable chronological event stream. Expandable JSON payloads, actor attribution, correlation IDs, and SHA-256 hash chaining.
15. **`/evaluation` (Research Benchmarks & Baseline Comparisons):**
    * Ground-truth experimental results comparing Static vs HPA vs Predictive-only vs CORTEX across SLO violations, cost waste, and safety block rates.
16. **`/providers` (Multi-Cloud Abstraction Hub):**
    * Neutral provider statuses: Local Kubernetes (Connected), AWS (Simulated/Read-Only), Azure (Simulated), GCP (Simulated).
17. **`/demo` (Flagship Interactive Demonstration):**
    * Single-click guided walkthrough for hackathon judges and evaluators showcasing both autonomous recovery and safety interception of dangerous mutations.

---

## 5. Global Shared Primitives & Real-Time UX

* **Global Command Palette (`Cmd/Ctrl + K`):** Reusable shortcut to quickly jump to any incident, service node, policy, or simulator scenario. High-risk actions cannot be dispatched directly from the palette.
* **Global Incident Drawer:** Clicking any incident tag or ID across the entire UI opens a right-hand sheet drawer with live diagnostic summary and direct navigation to the forensic view.
* **Global Service Inspector:** Clicking any node in the topology opens a slide-over panel displaying real-time metrics, active replicas, downstream dependencies, and recent events.
* **Defensive Connection & System States:**
  * `BACKEND_OFFLINE`: Visible non-blocking banner when the FastAPI daemon is unreachable, preserving cached telemetry.
  * `OBSERVABILITY_DEGRADED`: Warning banner and automatic reduction of autonomous authority when primary telemetry probes fail.
  * `STALE_DATA`: Explicit timestamp indicators when data has not refreshed within the expected polling or stream window.

---

## 6. Template Component Reuse & Mapping Matrix

| Existing CORTEX Need | Required UI Pattern | ShadcnStore Template Component to Reuse |
| :--- | :--- | :--- |
| Application Shell | Collapsible sidebar, top header, breadcrumbs, user status | `src/components/layout/sidebar.tsx`, `header.tsx` |
| Navigation Shell | Route-based navigation with active indicators | Template Nav Menu & Sidebar items |
| Incident & Audit Lists | Searchable, paginated, sortable data tables | `src/components/ui/data-table.tsx` (TanStack Table) |
| Metrics & Telemetry | Live metric cards, trend sparklines, time-series charts | `src/components/ui/card.tsx`, Recharts chart wrappers |
| Approval & Interception | Action confirmation, risk warning modals | `src/components/ui/dialog.tsx`, `alert-dialog.tsx` |
| Node & Incident Inspection| Slide-over drawer for node/incident details | `src/components/ui/sheet.tsx` |
| Command Palette | Quick switcher across routes, services, incidents | `src/components/ui/command.tsx` |
| Policy & Action Forms | Validated JSON/form builders for policies & scenarios | `src/components/ui/form.tsx`, `input.tsx`, `select.tsx` |
| Mode & Autonomy Control | Segmented pill toggles (Balanced / Cost / Green) | `src/components/ui/tabs.tsx`, `toggle-group.tsx` |
| System Notifications | Real-time toast alerts on incident detection & action | `src/components/ui/sonner.tsx` / `toast.tsx` |

---

## 7. Migration Execution Phases

1. **Phase 1: Scaffolding & Shared Primitives**
   * Integrate Shadcn UI primitives (`button`, `card`, `dialog`, `sheet`, `table`, `tabs`, `badge`, `command`, `tooltip`, `sonner`).
   * Configure Lucide React icons, Tailwind CSS monochrome tokens, and Geist font family.
   * Set up React Router for deep linkable routes (`/`, `/console`, `/incidents`, `/topology`, `/predictions`, `/optimizer`, `/cortex`, `/simulator`, `/approvals`, `/policies`, `/chaos`, `/reliability`, `/cost`, `/audit`, `/evaluation`, `/demo`).
2. **Phase 2: Layer 1 — The Public Landing Page**
   * Recompose the landing page with 15 scroll-driven cinematic sections.
   * Build the interactive Hero topology with request flow animation and live status strip.
   * Implement the scroll-linked narrative: Why CORTEX, The Control Loop, Simulate, Authorize, and Verify.
3. **Phase 3: Layer 2 — Operations Command Center (`/console`)**
   * Build the React Flow interactive service topology graph with live health status, traffic glows, and click-to-inspect.
   * Implement the Top Status Rail and Right CORTEX Decision Card.
   * Connect live polling / SSE stream to backend event bus and audit logs.
4. **Phase 4: Layer 3 — Dedicated Deep Analysis Pages**
   * Implement `/incidents`, `/topology`, `/predictions`, `/optimizer`, `/cortex`, `/simulator`, `/approvals`, `/policies`, `/chaos`, `/reliability`, `/cost`, `/audit`, `/evaluation`, and `/demo`.
5. **Phase 5: Global Drawers, Command Palette & Defensive States**
   * Wire `Cmd + K` Command Palette, Global Incident Drawer, and Global Service Inspector.
   * Enforce `BACKEND_OFFLINE` and `OBSERVABILITY_DEGRADED` fallback states.
6. **Phase 6: Verification, Type-Checking & End-to-End Testing**
   * Run full test suite, linting (`tsc --noEmit`), and Vite production build (`dist/`).
   * Conduct live browser verification on `http://localhost:3000`.
