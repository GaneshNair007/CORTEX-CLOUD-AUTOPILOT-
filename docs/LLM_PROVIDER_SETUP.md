# NVIDIA and multimodel provider setup

## Credential handling

Only process environment variables and `backend/.env` are configuration sources. Process values take precedence. Keep provider credentials on the backend. Never place them in `VITE_*`, browser storage, source code, logs or a prompt.

Revoke previously exposed credentials at their issuing provider. Removing a key from the latest commit does not remove historical copies. Use a newly issued NVIDIA credential for the live acceptance check; this repository must not reuse old conversation or Git-history keys.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.setup_local
```

Edit `backend/.env` locally:

```dotenv
LLM_PRIMARY_PROVIDER=nvidia
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
LLM_FALLBACK_PROVIDERS=heuristic
ALLOW_PAID_LLM_FALLBACK=false
```

Fill the blank credential only in your local file or hosting secret settings. The NVIDIA adapter accepts the official HTTPS endpoint and sends a bounded, non-streaming chat request with thinking disabled. See NVIDIA's [model card](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) and [Nemotron configuration guide](https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started-nemotron-3.5-lightning.html). Availability, rate limits and account charges depend on your account; CORTEX does not assume unlimited free inference.

## Configuration check and live proof

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.check_llm_provider --provider nvidia
```

This performs no inference. `credential: CONFIGURED` only means a credential is present, not that it is valid.

After configuring a newly issued credential:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.check_llm_provider --provider nvidia --live
```

Live mode makes a small request through the same provider client used by the incident agent. Successful proof requires all of:

- `status: SUCCESS` and `live_test: true`;
- `actual_provider: nvidia` and the requested model;
- `fallback_used: false`;
- the exact short response `CORTEX_OK`.

The report contains provider/model, timing, token counts when reported, and safe status only. It prints no key fragments or hidden reasoning. A heuristic fallback or a metadata health probe is not a successful NVIDIA inference test. A failed test exits nonzero.

## Purpose routing

The primary provider is selected by `LLM_PRIMARY_PROVIDER`. `LLM_PROVIDER` and `LLM_MODE` remain legacy compatibility settings; use the primary setting in new deployments.

Diagnosis, critique and optional semantic review may select distinct providers. Omit a purpose provider to inherit the primary:

```dotenv
DIAGNOSIS_PROVIDER=nvidia
CRITIQUE_PROVIDER=nvidia
# CRITIQUE_PROVIDER=gemini
DIAGNOSIS_MODEL=
CRITIQUE_MODEL=
ENABLE_SEMANTIC_REVIEW=false
# SEMANTIC_REVIEW_PROVIDER=nvidia
```

Overrides change the actual requested provider/model. They are not display-only labels. Configure each selected provider's own credential and a model available to that account.

| Provider | Credential | Model/base configuration |
| --- | --- | --- |
| NVIDIA | `NVIDIA_API_KEY` | `NVIDIA_MODEL`, `NVIDIA_BASE_URL` |
| Gemini | `GEMINI_API_KEY` | `GEMINI_MODEL` |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_MODEL`, `OPENAI_BASE_URL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` |
| CheaperInference | `CHEAPERINFERENCE_API_KEY` | `CHEAPERINFERENCE_MODEL`, `CHEAPERINFERENCE_BASE_URL` |
| Ollama | No cloud key | `OLLAMA_HOST`, `OLLAMA_MODEL`; local daemon/model must be running |
| Heuristic | No key | Deterministic degraded fallback; no external model was called |

Do not reuse an OpenAI or Gemini key as a CheaperInference/NVIDIA credential. `APP_URL` identifies the CORTEX server and is unrelated to inference endpoint routing.

## Bounds and status

```dotenv
CORTEX_LLM_TIMEOUT_SECONDS=30
CORTEX_LLM_MAX_RETRIES=2
CORTEX_LLM_MAX_OUTPUT_TOKENS=800
CORTEX_LLM_MAX_REQUESTS_PER_INCIDENT=4
ALLOW_PAID_LLM_FALLBACK=false
```

Each retry/fallback consumes a call reservation. Call limits, timeout bounds and the model allowlist constrain requests. Provider error categories distinguish missing/invalid credentials, rate limits, unavailable models and timeouts. Token/cost values remain unknown when the provider does not report enough information.

The authenticated `GET /api/v1/llm/status` response and console AI status show the latest actual route, provider/model, degraded state and fallback. Model output must satisfy a typed diagnosis/critique contract. Neither a plausible answer nor a healthy provider overrides deterministic execution authorization.

## Troubleshooting

| Observed state | Check |
| --- | --- |
| UNAVAILABLE / NOT_CONFIGURED | The intended backend process loaded the fresh credential, using only `backend/.env` or its environment. Restart after changing configuration. |
| INVALID_CREDENTIALS | Revoke/replace an invalid credential at its own provider; do not try another provider's key. |
| RATE_LIMITED / QUOTA_EXCEEDED | Inspect the account's limits and wait or adjust configuration; avoid retry loops. |
| MODEL_UNAVAILABLE | Confirm the exact model is enabled for that account. |
| DEGRADED with heuristic | External inference did not complete. Retrieval and policy can remain usable; live AI acceptance remains unproven. |
| Metadata probe succeeds, live call fails | Connectivity/model listing does not prove inference permission, quota or response validity. |