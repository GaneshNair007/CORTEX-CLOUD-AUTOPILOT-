# Backend readiness review

**Verdict: not ready for the expected verified, policy-governed autonomous cloud outcome.** Adding an AI key alone will not fix the execution and verification gaps.

Reviewed locally on 2026-09-17 against `266668cb8cb88c83135f66f3b63f995d41e7ff3f` (backend update `4c6e3a9`). Requirements source: the supplied project-details attachment, including the single mutation gateway, real telemetry, verified recovery, durable approvals/idempotency, trusted learning, discoverable topology and Docker-first execution requirements. No backend source was changed.

## What was actually checked

- Inventoried 276 tracked repository paths and inspected the API, active frontend, backend execution/guard/provider paths, telemetry, forecasting, twin, optimization, RAG, persistence, chaos, evaluation and tests. This is a targeted architectural and behavioral review, not a claim of exhaustive formal verification of every line or binary asset.
- Checked credential **presence only** in the current process and local root/backend/frontend environment files; no secret values were printed. Remote Render/Vercel/other deployment secrets were not accessible or checked.
- Copied 135 tracked backend/sandbox files under ignored `frontend/artifacts/backend-audit`. Original ledgers, memory files and databases were not modified by audit tests.
- Installed declared requirements into an isolated Python 3.12 environment with bundled base libraries; disabled user-site packages. Docker was directed to an unused local endpoint, and sandbox services were remapped to ports 31010–31017. No cloud resources were changed.
- Ran the unchanged test suite and targeted probes with a stub provider. Those probes exercise actual guard/gateway code but do not mutate infrastructure.
- At final handoff, an existing backend on localhost:8000 responded through the new frontend proxy. Ten read endpoints returned HTTP 200: health, topology, incidents, operations, policies, approvals, ledger, events, legacy audit logs and a five-minute forecast. Observed 11 nodes/13 edges, 14 incident records, 0 operation records and 4 policies. Its running environment was not inspected for private credentials. The clean-install failure below concerns the declared dependency list, not a claim that no separately prepared local environment can run the app.

## AI configuration

| Setting | Local finding |
| --- | --- |
| `GEMINI_API_KEY`, `GOOGLE_API_KEY` | Absent from the current process |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Absent from the current process |
| `OLLAMA_HOST`, `LLM_MODE` | Absent from the current process |
| Local `.env` files | Only example files found in the checked root/backend/frontend locations |
| `backend/.env.example` | Gemini value is a placeholder |
| Default `LLMClient().mode` | Reproduced as `mock` |

`backend/llm/client.py:52–69` selects a heuristic mode without keys/local-provider settings. Its output depends on keywords but retains fixed confidence scores (0.76 / 0.68); it is not a connected language model. There is no `load_dotenv` call in the backend source. The documented startup command does not load an environment file automatically.

Provider-specific HTTP adapters exist. A separate probe with dummy keys showed that explicitly choosing OpenAI while both Gemini/OpenAI variables exist still chooses the Gemini key (`client.py:69`). Credentials must be selected by provider before real integration testing. Adaptive routing currently records `selected_model` but does not apply it to the generation call (`orchestrator/agent.py:115–139`). No model API request, billing event or external credential validation was performed.

## Blocking findings

### P0 — Controls do not govern one shared executor

`api_server.py:36–42` imports `cortex.guard` / `cortex.gateway`, whereas `control_plane/pipeline.py:30–31` imports `backend.cortex.guard` / `backend.cortex.gateway`. Python creates separate module instances. Additionally, each gateway constructs its own guard (`cortex/gateway.py:41`).

Runtime probe: setting the API-facing guard to L0 left both execution guards at L2. Setting the API-facing freeze flag left the pipeline executor unfrozen. This reproduces the exact imports/assignments used by the API; a complete HTTP test is blocked by the missing RAG dependency below.

**Required:** one canonical import path, dependency-injected shared guard/gateway/store, and API-level tests proving L0 and freeze block both direct and pipeline mutations. The frontend now labels these as reported states and explains the enforcement limitation.

### P0 — Approval queues and authorization binding are inconsistent

The guard generates `APP-*` records with a 120-second TTL. The gateway independently generates `app_*` tokens with a 300-second TTL. The API lists/resolves the global guard queue, while execution uses gateway tokens (`api_server.py:202–227`, `guard.py:183–201`, `gateway.py:267–323`).

Probe: the gateway token was absent from its guard's pending queue. A token approved for scaling one service was accepted for a different proposal, incident, action and target. The gateway checks status and expiry but not proposal/parameter/target binding and does not consume the token.

**Required:** one durable approval record and ID, actor authorization, binding to the exact canonical proposal and state version, expiry, single-use consumption, and re-evaluation immediately before execution.

### P0 — Failed or ineffective actions can be called successful recovery

`gateway.py:358–438` does not reject a provider response with `status: FAILED`. It classifies equal pre/post latency and errors as `RECOVERED`, without applying service SLOs. The pipeline resolves incidents whenever gateway status is `SUCCESS` (`pipeline.py:242–243`), including partial/no-effect situations.

Controlled probe result:

```json
{
  "provider_status": "FAILED",
  "reported_status": "SUCCESS",
  "reported_outcome": "RECOVERED",
  "post_p95_ms": 30000.0,
  "post_error_pct": 100.0
}
```

The separate SLO verifier exists but is not used for gateway classification. Its percentage conversion also relies on the *pre-action value* instead of explicit units (`verification/verifier.py:64–76`).

**Required:** propagate provider failure; verify against explicit SLO windows, freshness and sample sufficiency; preserve `NO_CHANGE`/`UNKNOWN`/`PARTIALLY_RECOVERED`; resolve only verified recovery. Unimplemented tool branches must fail, rather than the generic success at `gateway.py:368`.

### P0 — Dry-run does not prevent actuation

`ActionProposal.dry_run` exists, but the gateway never checks it. A `dry_run=True` probe reached the stub provider.

**Required:** a tested dry-run boundary before any provider call. The existing test named `test_gateway_dry_run` does not actually set `dry_run=True`, so its passing result does not cover this defect.

### P1 — Declared installation cannot start the API

`rag/retrieve.py:25` imports `chromadb`, and its embedding path requires sentence-transformers; neither is declared in `backend/requirements.txt`. Using the declared dependencies, importing `api_server` fails with `ModuleNotFoundError: No module named 'chromadb'`. The full suite stops at `test_pipeline.py` collection for the same reason.

The original workspace has a `backend/rag/chroma_db` directory; its existence does not supply the missing Python packages or prove index validity. The disposable fresh-install copy intentionally used tracked files, not that ignored local index. The existing running local backend may have additional installed dependencies.

**Required:** declare/pin compatible RAG dependencies, build the index reproducibly, and verify startup from a clean environment. Report missing index/model states through readiness instead of concealing them. API startup was not patched around during this review.

### P1 — No API authentication or enforceable operator identity

Mutation, approval, autonomy, chaos and event-clear endpoints have no authentication dependency. `actor` and `approver` are caller-supplied strings. CORS allows all origins (`api_server.py:57–64`). This does not meet authenticated operational authorization.

**Required:** authenticated identity and role checks at the API/gateway boundary, controlled CORS, and audit attribution from verified credentials. UI confirmation is not backend authorization.

## Other expected outcomes still incomplete

| Requirement | Evidence / gap | Needed outcome |
| --- | --- | --- |
| Single mutation gate | Chaos calls `sandbox_manager` directly; the standalone verifier calls provider rollback directly. | Route every mutation through a verified gateway capability, including chaos/rollback. |
| Durable operation history | `record_operation` is defined but has no caller in backend execution paths. | Persist every proposal/decision/attempt/result and expose that history. |
| Durable approvals/idempotency | Runtime approvals and idempotency use dictionaries; SQLite models do not make those paths durable. Idempotency keys omit action parameters and replay is labeled `SUCCESS` regardless of stored status. | Restart-safe storage, atomic claims, request binding and original outcome replay. |
| Trusted learning | Agent writes `resolved_at` and calls `remember` before gateway execution/verification (`agent.py:187–199`). | Unverified proposal memory separated from trusted recovered incidents. |
| Shared event history | Pipeline clears all events at the start; mixed import paths also instantiate separate in-memory event stores. | Incident-scoped append-only history, consistent event identity and retention. |
| Real telemetry | Sandbox HTTP endpoints exist, but p95/replicas are modeled state; secondary probes manufacture fixed RPS/latency values. Collector labels HTTP data `prometheus` and defaults to optimal status. | Real measured histograms/counters, explicit source/freshness, unknown values when unavailable. |
| Discoverable topology | Graph constructs fixed nodes/health/metrics (`topology/graph.py:15–90`). | Discover resources/dependencies; distinguish configured topology from observed health. |
| Forecast from observed history | History is randomly generated (`forecaster.py:49–64`). GET creates separate display and prediction histories; POST accepts history but does not pass it to prediction (`api_server.py:165–177`). | One measured history and service identity flowing into model prediction. |
| Cost/energy truth | Optimizer uses fixed $0.08/pod-hour, 22 watts/pod and 380 gCO2/kWh (`optimizer.py:65–68`). | Calibrated provider/region measurements or clearly identified estimates. Frontend labels estimates. |
| Chaos fidelity | Crash/process kill is an HTTP state flag; scaling changes an integer rather than worker count. Cascades explicitly inject each listed fault instead of demonstrating causal dependency propagation. Failure responses can still be wrapped as active experiments. | Measured local-process/container faults and verified cleanup, with failed injection distinguished. |
| Docker-first execution | Docker restarts can use Docker, but scaling/rollback and app metrics delegate to the sandbox. Cloud/Kubernetes classes remain placeholders. | Verified Docker lifecycle/scaling/rollback before cloud claims. |
| Continuous L3 autonomy | L3 changes a guard decision branch. No scheduled observe/reconcile loop or background controller start exists. | Persistent controlled reconcile loop with bounded actions and operator stop. |
| Real evaluation | Safety totals are literal 50/15/15 (`evaluation/harness.py:69–71`); baseline comparisons are configured examples. | Report measured test outcomes and datasets with provenance. |
| Bounded tool contracts | Registry checks types only for supplied fields; missing required fields, numeric bounds, capabilities and environment restrictions are not comprehensively enforced. | Strict immutable proposals and enforced per-tool schemas/capabilities. |
| Readiness | `/health` returns constant incident count 2 and health 99.96, with no LLM/index/provider readiness. | Component readiness, actual counters and honest degraded states. |

The hash-chain ledger, typed proposals, guard blocks, locking/cooldown tests, forecast artifacts, and local HTTP sandbox provide useful foundations. Their presence does not demonstrate a verified end-to-end autonomous recovery system.

## Test results and interpretation

| Check | Observed result |
| --- | --- |
| Full unchanged backend suite | Collection stopped: missing `chromadb` in `test_pipeline.py` |
| Suite excluding `test_pipeline.py` | **45 passed**, 30.97 seconds |
| API import with declared dependencies | Failed: missing `chromadb` |
| Existing local backend read integration | Ten read endpoints returned HTTP 200 through the frontend proxy |
| Frontend against existing backend | All 21 routes rendered without uncaught errors; read-only check |
| Default AI mode | `mock` |
| Shared controls probe | Failed expected invariant: L0/freeze did not reach all executors |
| Approval binding probe | Failed expected invariant: changed proposal reached stub provider |
| Failed-provider verification probe | Failed expected invariant: failure reported as recovered success |
| Dry-run probe | Failed expected invariant: provider called |

The 45 passing tests are useful unit-level evidence, not proof that all 47 tests or the full application pass. Several tests assert permissive statuses or isolated classes and do not exercise API wiring. Original suite files were not edited. Probe source and JSON results are retained under ignored `frontend/artifacts/backend-audit/` for local reproduction; provider calls in probes are stubs.

## Repair order and acceptance criteria

1. Make dependency installation and API startup reproducible; expose component readiness and AI mode. Configure a real backend-only credential or an explicitly selected local model after provider-key selection is fixed.
2. Unify guard/gateway/imports and approvals. Prove API-level L0/freeze, token binding/expiry/single-use, dry-run and authorization before enabling mutations.
3. Propagate provider failure and apply measured SLO verification. Prove failed/no-change/unknown actions never resolve incidents or enter trusted recovery memory.
4. Persist operations, approvals, idempotency and scoped events. Prove correct behavior across process restarts and concurrent requests.
5. Complete the Docker/local fault → diagnosis → approved remediation → measured recovery → persisted evidence scenario. Then expand live telemetry, discovery, forecasting and continuous autonomy.

No backend repair, credential creation, public deployment or production mutation was performed as part of this frontend-only task.
