# Frontend implementation and feature coverage

## Scope and design

Frontend implementation followed by a backend readiness review. Backend source was not edited. Work started at `cea2c6c`; another process committed backend/frontend work during this session. The backend audit targets `266668c` (backend changes in `4c6e3a9`). A separate active entry/server preserves the legacy files restored by that process.

The initial implementation used the ShadcnStore Dashboard + Landing Page Vite direction named in `docs/FRONTEND_MIGRATION_PLAN.md`. Its MIT Card and Dialog components remain adapted into `src/control-plane/template`, with attribution retained. The user's subsequent Brilean reference supersedes that initial visual direction. The current interface adapts the reference's composition and motion to CORTEX; it does not claim identical brand assets or commercial fonts.

The current interface uses an off-white canvas, charcoal typography, lime accents, restrained semantic status colors, large editorial headings, numbered workspace titles, and a shared light shell across all 21 routes. The previous dark theme and corridor-photo landing have been superseded by a typographic landing, original metallic SVG stars, sticky service cards, and a scroll-driven control-loop presentation. Inter Tight substitutes for the reference's custom fonts. Data tables, topology/forecast diagrams, command search, responsive navigation, focus handling, confirmations, and explicit loading/error/empty states remain functional. Reduced-motion preference and a persistent pause control govern the new animation. See [BRILEAN_REDESIGN.md](BRILEAN_REDESIGN.md) for measured reference details and route-by-route coverage.

## Requested plugins

- **FLOWSTACK UI:** `@flowstack-ui/brick` pinned to **0.2.2**. Resolved and read exact installed Agent Knowledge, layer selection, interface composition, Button guidance, and coverage metadata. Brick Button uses its public entry; core/button styles load once. The user-requested ShadcnStore template supplies cards/dialogs alongside native tables/forms. This intentional interoperability is not an all-Brick composition or package certification.
- **Website Deploy Toolkit:** followed static-site constraints: relative assets, hash routes, dedicated `build:static` output. Python/API hosting stays separate. Prepared locally, not published.
- **AI Graphic Design:** reviewed the requested skill. Its canvas workflow concerns standalone graphic assets; the current redesign uses original SVG/CSS artwork and UI diagrams. The earlier project photograph is no longer the active landing artwork. No external canvas or AI-generated artwork was created or claimed.

## Backend feature → frontend

API paths below omit the common `/api` prefix.

| Feature | Console view | Contract and limits |
| --- | --- | --- |
| Health | Command center / connection banner | `GET /health`; reachability and confirmed guard state. Counts use persisted records, not constant health totals. |
| Incident store | Incidents | `GET /incidents`; search, filters, details and original payload. |
| Topology | Infrastructure | `GET /topology`; returned nodes/edges and inspection, labeled as modeled. |
| Blast radius | Infrastructure / Digital twin | `POST /topology/blast-radius`; editable target/action. |
| Counterfactual twin | Digital twin | `POST /twin/simulate`; proposal, simulation and separate execution review. |
| Execution gateway | Digital twin | `POST /tools/action`; nested blocked/approval/execution outcomes retained. Simulation alone never executes. |
| Forecasting | Predictions | `GET /forecast?horizon=...`; graph, bounds, accessible data table and model metadata. Generated input history labeled. `/forecasting/predict` is an alternate API; custom-history input is not exposed because the backend ignores it in prediction. |
| Optimization | Optimizer | `POST /optimizer`; mode, demand, replicas, candidates and selected plan. No automatic mutation. `/optimizer/solve` is an alias. |
| Cost/carbon | Cost planner / Sustainability | Optimizer contract with purpose-specific modes. Estimates remain explicitly modeled. |
| RAG retrieval | Incident memory | `POST /rag/retrieve`; query, count, relevance and original sources/text. |
| Autonomy | CORTEX Guard | `POST /cortex/autonomy`; review and confirmed response. Backend wiring gap recorded separately. |
| Emergency freeze | Header / CORTEX Guard | `POST /cortex/kill-switch`; response/error handling, resume confirmation. Backend pipeline scope gap recorded separately. |
| Policies | Policies | `GET /cortex/policies`; read-only because no edit API exists. |
| Human approval | Approvals | `GET /cortex/approvals`, `POST /cortex/approvals/resolve`; review, operator attribution, TTL and approve/reject. Backend queues currently differ. |
| Events | Activity stream | `GET /events/list`; search, timestamps and payloads. |
| Event emission | Activity stream / Operator notes | `POST /events/emit`; operator note and server-list refresh. |
| Event maintenance | Activity stream / Maintenance | `POST /events/clear`; explicit destructive confirmation and errors. |
| Evidence ledger | Evidence ledger | `GET /audit/ledger`; integrity, records and export. |
| Legacy audit log | Evidence ledger | `GET /logs/audit`; original audit details. |
| Operation store | Execution history | `GET /operations`; status, guard and verification where recorded. Backend write-path gap recorded separately. |
| Control pipeline | Control loop | `POST /pipeline/run`; reviewed inputs, nine stages, actual action outcome and evidence. This is a completed response, not live streaming. |
| Chaos | Chaos lab | `POST /chaos/inject`, `GET /chaos/experiments`, `POST /chaos/clear`; sandbox explanation, confirmation, results and cleanup. |
| Reliability | Reliability | Modeled topology p95/SLO comparison. Live SLO windows and error budgets lack an API. |
| Evaluation | Evaluation | `GET /evaluation/benchmark`; retrieval separated from illustrative safety/baseline values. |
| Cloud adapters | Cloud providers | Explicit placeholder/runtime-unknown states. No discover/connect/manage API exists. |
| API connection | Connection settings | Validated API address, session scope and retry. No browser AI-key collection. |

The cascading-failure method has no API route. Continuous monitoring, provider discovery, authentication management, policy editing and live SLO history also need backend contracts before they can become functional controls.

## Verification

- Final Brilean design and motion browser run: **26 passed in 1.4 minutes**, including all 21 routes at 390px and 1440px, scroll navigation, metallic story progression, all four pinned phases, keyboard selection, persistent pause/resume, and reduced motion. An isolated initial connection-form failure did not reproduce in five focused repeats or the clean full run; assertions were preserved.
- All 21 console views rendered without uncaught browser errors.
- Coverage: incident search/details, unavailable state, rejected mutations, approval expiry, confirmations, twin/gateway requests, optimizer inputs, RAG escaping, actual pipeline outcomes, stale snapshots, keyboard navigation, provider states, and 390px layouts.
- Final checks after the Brilean motion changes passed: project TypeScript, strict console TypeScript, Node production build, and static production build. The bundler requires normal process access outside the restricted process sandbox.
- Preserved legacy source/string checks: **43 passed**. These do not validate the new interface or real backend execution.
- Fixtures are isolated under `tests/browser`; production imports none.
- npm audit after compatible fixes reported zero vulnerabilities at the time checked.
- Inspected the redesigned landing, scrolling motion, offline behavior, desktop and mobile views in Chromium. During the earlier backend audit, an existing local backend answered ten read endpoints through the new proxy: health, topology, incidents, operations, policies, approvals, ledger, events, legacy logs and forecast. This does not establish a reproducible clean install or safe live mutation. No cloud mutation or connected AI request was verified.
- That earlier read-only browser pass against the running backend rendered all 21 console routes with zero uncaught browser errors or route error-boundary failures. Historical connected screenshot: `artifacts/console-connected-desktop.png`. This smoke check did not submit any operational actions. Current design screenshots include `artifacts/cortex-motion-hero.png`, `artifacts/cortex-mobile-process.png`, and the explicitly fixture-backed `artifacts/console-fixture-desktop.png`.

Backend evidence and remediation priorities: `BACKEND_READINESS_REPORT.md`.
