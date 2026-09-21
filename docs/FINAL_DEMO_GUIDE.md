# Local demonstration and deployment guide

## What this guide verifies

The local demonstration checks the existing UI motion, authenticated API access, contextual retrieval, deterministic authorization and outcome reporting. A successful NVIDIA test is a separate acceptance condition. Do not describe an unavailable provider, heuristic fallback, modeled forecast or estimated saving as a verified live cloud result.

## 1. Prepare the backend

From the repository root, with Python 3.12 installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m backend.scripts.setup_local
```

If a usable root `.venv` already exists, reuse it. Setup preserves existing environment values and provider keys, adds missing console role tokens, and prints no secrets. It does not rotate old provider keys or claim they are safe.

Edit the ignored `backend/.env` privately. Configure a newly issued `NVIDIA_API_KEY`; keep `LLM_PRIMARY_PROVIDER=nvidia`. Leave `CORTEX_START_SANDBOX=true` for the local demonstration. The eight sandbox ports are 8010–8017; these are controlled HTTP service threads in one Python process.

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.check_llm_provider --provider nvidia
.\.venv\Scripts\python.exe -m backend.scripts.check_llm_provider --provider nvidia --live
```

Run the live command only after supplying the fresh credential. Require `SUCCESS`, `actual_provider: nvidia`, the correct model, `fallback_used: false`, and `CORTEX_OK`. Configuration-only output cannot satisfy this check.

Start the service:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api_server:app --host 127.0.0.1 --port 8000
```

The API startup imports canonical source records, initializes a missing/incompatible semantic index, and replays pending memory writes. A first embedding download requires network access. Subsequent cached startup does not need paid LLM inference for retrieval.

## 2. Start the UI and authenticate

In a second terminal:

```powershell
cd frontend
npm ci
```

If `frontend/.env` is missing, copy `.env.example` to `.env`. Preserve an existing file. Then:

```powershell
npm run dev
```

Open [CORTEX locally](http://127.0.0.1:3100/). In Connection settings, leave the backend address blank for the local proxy. Enter the local console access token from `backend/.env`. An administrator token enables governance controls; operator/viewer permissions are enforced by the backend.

Console access is kept in memory, expires after 30 minutes, and clears on reload or a changed backend address. The field accepts CORTEX role tokens, never NVIDIA/provider keys.

## 3. Check motion and data

1. Scroll the landing page and inspect section reveals, topology motion and navigation transitions. Open the console and switch routes. A normal-motion browser should animate; an operating-system reduced-motion preference intentionally reduces effects.
2. Inspect AI status in Connection settings. Compare configured and actual provider/model; a fallback must read as degraded.
3. Open Incident memory and search `HTTP 503 PostgreSQL connection pool saturation`. Inspect the retrieved incident/runbook IDs, scores and reasons. Change to `CrashLoopBackOff` and check exact-signature evidence.
4. Open Evaluation and run the retrieval benchmark. Inspect actual strategy results. Safety comparisons without measurements should remain unmeasured.
5. Inspect service status and telemetry provenance. Sandbox measurements, configured topology, unavailable services and estimates must retain their labels.
6. Use desktop and narrow/mobile widths. Controls must remain accessible and important status text must not be clipped.

A fresh checkout must run `npm ci` and rebuild its frontend. Opening source HTML without Vite/build output, using stale `dist`, a wrong entrypoint, or a reduced-motion setting can change the visible animation. The active UI entrypoint is `frontend/src/main.tsx` and the control-plane application; legacy view files are not the main console.

## 4. Check authorization and recovery

Use the local sandbox only. Inspect the proposed action and target before executing a demonstration.

- With no console token, protected requests should fail authentication.
- With a viewer token, attempted mutation must be denied.
- With administrator access, engage the kill switch. A remediation attempt must be blocked without a provider mutation. Disengage it explicitly when finished.
- For an approval-required proposal, inspect the pending record and resolve it with an authorized role. Approval must remain bound to the displayed proposal and expire/consume as designed; it is not a reusable override.
- Run the incident workflow against a local sandbox service. Follow the proposal, decision, operation and verification records. Report `UNKNOWN`, `NO_CHANGE`, `WORSE` or partial recovery honestly.
- Only a verified recovered outcome may resolve the incident. After such a result, search for the new memory without manually rebuilding. Verified failed outcomes should remain searchable as negative evidence.
- Inspect the audit ledger and record actual results rather than assuming that every scenario heals.

## 5. Repeatable checks

Run backend checks from the root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
.\.venv\Scripts\python.exe -m backend.scripts.scan_secrets
```

The backend tests use isolated SQL/logs and sandbox service ports 28010–28017 rather than the operator's live demo ports. Tests use deterministic/offline provider behavior and do not count as a real NVIDIA call.

Stop the API before rebuilding the index:

```powershell
.\.venv\Scripts\python.exe -m backend.rag.rebuild_index
.\.venv\Scripts\python.exe -m backend.evaluation.retrieval_benchmark --output docs/retrieval_evaluation.json
```

Once MiniLM is cached, `$env:HF_HUB_OFFLINE='1'` avoids remote model checks for these commands. Do not set offline mode before the initial model download.

From `frontend`:

```powershell
npm run lint
npm test
npm run build:static
npm run test:e2e
```

Browser tests build the production bundle and serve it on isolated port 3117, leaving the user preview on 3100 untouched. They use API fixtures; the separate `python -m backend.scripts.verify_local_demo --output docs/local_demo_verification.json` harness exercises the real authenticated API and local HTTP sandbox on ports 29010–29017.

The evaluation measures 20 manually labeled scenarios over a small bundled corpus. Report computed values and warmup separately; do not infer throughput at large scale or production safety percentages.

## 6. Docker

From the repository root:

```powershell
docker build -f backend/Dockerfile -t cortex-backend .
docker volume create cortex-state
docker run --name cortex-backend --env-file backend/.env -e CORTEX_START_SANDBOX=false -e CORTEX_DATA_DIR=/app/runtime -e CORTEX_CHROMA_DIR=/app/runtime/chroma -e CORTEX_PERSISTENT_STORAGE=true -p 127.0.0.1:8000:8000 --mount source=cortex-state,target=/app/runtime cortex-backend
```

Keep local secrets out of the image. The Docker ignore rules exclude environment files, generated DBs/indexes/logs and agent workspaces. The image downloads a CPU embedding runtime and model during build; network/model failure fails the build clearly. A named volume retains SQL/Chroma across container replacement. Back up that volume separately. Set `CORTEX_START_SANDBOX=true` only when you intentionally want the local modeled sandbox inside the container.

Docker/image runtime verification requires a working Docker daemon. A reviewed Dockerfile is not proof that the image has been built and exercised on a target host.

## 7. Render backend and Vercel frontend

- Frontend: https://cortex-cloud-autopilot.vercel.app
- Backend: https://cortex-backend-ehye.onrender.com
- Render service: srv-daorch80cd8s73ao4760, free plan, one worker, no disk.
- Validated blueprint: render.yaml. See FREE_HOSTING.md for limitations.

The backend uses Chroma's all-MiniLM-L6-v2 ONNX export with one CPU thread and
one-document batches. No PyTorch is installed in the free deployment. The local
default remains SentenceTransformers. Free storage resets on sleep/restart/redeploy;
canonical evidence rebuilds, but learned runtime state is not durable.

Revoke the NVIDIA key exposed in commit 01c51d5. Enter a fresh NVIDIA_API_KEY in
https://dashboard.render.com/web/srv-daorch80cd8s73ao4760/env and redeploy.
Do not place it in Git or frontend build variables. AI remains unavailable until
an actual fresh-key inference succeeds.

For protected console actions, copy CORTEX_OPERATOR_TOKEN or CORTEX_ADMIN_TOKEN
from the private Render environment into the site's Connection settings > Console
access token. Never enter an AI-provider key there. Console access stays in memory.
Read-only pages and searches are public. Infrastructure execution is a local sandbox.

Vercel uses frontend as project root, npm ci, npm run build:static, dist-static,
and VITE_API_URL=https://cortex-backend-ehye.onrender.com. CORS permits that exact
frontend origin. No credentials are exposed through VITE variables.

Local free-runtime commands (PowerShell, repository root):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements-free.txt
$env:CORTEX_EMBEDDING_RUNTIME='onnx'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
.venv\Scripts\python.exe -m backend.scripts.prepare_embeddings
.venv\Scripts\python.exe -m backend.rag.rebuild_index
.venv\Scripts\python.exe -m pytest backend/tests -q
.venv\Scripts\python.exe -m backend.evaluation.retrieval_benchmark --output docs/free_hosting_evaluation.json
$env:CORTEX_START_SANDBOX='true'
.venv\Scripts\python.exe -m uvicorn backend.api_server:app --host 127.0.0.1 --port 8000
```

## Current acceptance record

Use [FINAL_IMPLEMENTATION_REPORT.md](FINAL_IMPLEMENTATION_REPORT.md) for the exact latest test totals, migration, evaluation results and remaining blockers. A missing fresh NVIDIA credential or an untested cloud deployment must remain explicit; do not substitute mock-provider tests or configuration review for those results.