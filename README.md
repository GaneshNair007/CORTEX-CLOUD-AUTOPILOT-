# CORTEX Cloud Autopilot

CORTEX combines an animated React operations console with a Python incident control plane. It retrieves operational evidence, produces an AI proposal, checks deterministic policy, executes through a controlled gateway, and verifies the resulting telemetry.

**Current scope:** an executable local service sandbox and a context-aware retrieval engine. External cloud adapters are not connected production integrations. Live NVIDIA inference requires a fresh, valid account credential and a successful provider test. Build and deployment configuration alone do not establish production readiness.

## Start locally

Use Python 3.12 and Node.js 22. Run backend commands from the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m backend.scripts.setup_local
.\.venv\Scripts\python.exe -m backend.scripts.check_llm_provider --provider nvidia
.\.venv\Scripts\python.exe -m uvicorn backend.api_server:app --host 127.0.0.1 --port 8000
```

Setup creates missing console access tokens in the ignored `backend/.env` without displaying them or replacing existing provider credentials. Configure only a newly issued `NVIDIA_API_KEY` in that file. An unavailable provider is reported honestly; deterministic retrieval and policy checks work without an LLM.

The API initializes its index during startup. The first run downloads the MiniLM embedding model if it is not cached. `CORTEX_START_SANDBOX=true` starts eight local FastAPI service processes on ports 8010–8017. They model operational services, including database/cache behavior; they are not actual PostgreSQL or Redis servers.

Open a second terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

Copy the frontend example only if `frontend/.env` does not already exist. Open [the console](http://127.0.0.1:3100/#/console), then Connection settings. Leave the backend address blank for the local proxy and enter a role token from your local backend configuration. Use an administrator token for governance controls. **Never enter an AI-provider API key in the browser.**

On Linux/macOS, activate `.venv/bin/activate` and use `python` for the equivalent commands.

## System boundaries

| Capability | What the implementation provides |
| --- | --- |
| UI and motion | React/TypeScript, GSAP, Lenis, responsive routes and reduced-motion handling; motion assets ship with the frontend build. |
| Incident retrieval | Deterministic context/fingerprint, metadata filtering, hierarchical scope expansion, Chroma MiniLM semantic retrieval, SQL FTS lexical search, explainable ranking. |
| Historical outcomes | SQL lifecycle records, verified positive/negative memory, Chroma upserts and retryable index write-back. |
| AI | NVIDIA primary provider; configurable purpose routing and bounded fallback. Status reports the actual provider/model and whether a fallback was used. |
| Authorization | Server-side bearer roles and deterministic CORTEX policy. Retrieval and model output never grant execution permission. |
| Execution | Local sandbox operations, durable approval binding and idempotency. Real cloud execution requires a separately connected adapter. |
| Verification | Post-action SLO checks distinguish command completion from incident recovery. |
| Audit | Hash-chained events support tamper detection; the file is not an immutable external audit service. |
| Forecast, topology, cost and carbon | Configured topology and modeled/estimated outputs; these are not measured cloud savings or certified production forecasts. |

## APIs and checks

- `GET /healthz`: process liveness.
- `GET /readyz`: database/index readiness, separate from AI inference availability.
- `GET /api/v1/llm/status`: safe provider health and actual call identity.
- `POST /api/v1/evidence/retrieve`: typed incident context and retrieval options.
- `POST /api/rag/retrieve`: deprecated, compatible `query/k` facade.

Most data routes require a role token by default. Mutations require operator access; autonomy, kill-switch and event clearing require administrator access. `CORTEX_PUBLIC_READS=true` is an explicit public-demo choice and does not authorize anonymous mutations.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
.\.venv\Scripts\python.exe -m backend.rag.rebuild_index
.\.venv\Scripts\python.exe -m backend.evaluation.retrieval_benchmark --output docs/retrieval_evaluation.json
.\.venv\Scripts\python.exe -m backend.scripts.scan_secrets
cd frontend
npm run lint
npm test
npm run build:static
npm run test:e2e
```

Stop the API before an intentional index rebuild. The rebuild preserves source documents and SQL memories, verifies a replacement collection, and retains the previous collection as a backup.

The evaluation report contains computed results for 20 labeled scenarios over the bundled 35-document corpus. It is a small-corpus retrieval measurement, not evidence of million-incident scale, guaranteed safety, reduced cloud bills or production MTTR. See the generated [evaluation report](docs/retrieval_evaluation.json) and the [implementation report](docs/FINAL_IMPLEMENTATION_REPORT.md) for actual verification status.

## Documentation and deployment

- [Architecture and operational boundaries](docs/ARCHITECTURE.md)
- [Local demo and deployment guide](docs/FINAL_DEMO_GUIDE.md)
- [NVIDIA and multimodel setup](docs/LLM_PROVIDER_SETUP.md)
- [Context-gated retrieval](docs/CONTEXT_GATED_RETRIEVAL.md)
- [Retrieval implementation report](docs/RETRIEVAL_IMPLEMENTATION_REPORT.md)

`backend/Dockerfile` uses the repository root as its build context and packages a CPU embedding runtime. `render.yaml` proposes one persistent backend instance; applying its compute plan and disk incurs hosting charges. It has not, by itself, deployed or validated a cloud instance. The Vercel project root is `frontend`, with `VITE_API_URL` set to the actual HTTPS backend URL.

Older design/audit documents describe previous snapshots and proposals. They are not proof that a current test, live-provider call or deployment has passed.