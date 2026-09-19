# CORTEX LLM Provider Setup

## Security first

Never commit real API keys. `backend/.env` is ignored by Git. If a key was ever committed or pasted publicly, revoke it at the provider and create a new one; deleting it from the latest commit does not remove it from Git history.

## Option A — CheaperInference

Create `backend/.env` locally with:

```env
LLM_MODE=openai
OPENAI_API_KEY=REPLACE_WITH_NEW_CHEAPERINFERENCE_KEY
OPENAI_BASE_URL=https://api.cheaperinference.com/v1
OPENAI_MODEL=gemini-2.5-flash
```

Do not put a CheaperInference key in `GEMINI_API_KEY`. CORTEX uses the OpenAI-compatible provider path for CheaperInference.

`APP_URL` is the public URL of the CORTEX application itself. It is not the inference provider base URL.

## Option B — Direct Google Gemini

Create `backend/.env` locally with:

```env
LLM_MODE=gemini
GEMINI_API_KEY=REPLACE_WITH_REAL_GOOGLE_AI_STUDIO_KEY
GEMINI_MODEL=gemini-2.5-flash
```

## Check configuration without spending credit

```bash
python backend/scripts/check_llm_provider.py
```

This validates environment variables only and does not perform an inference request.

## Perform one tiny live test

```bash
python backend/scripts/check_llm_provider.py --live
```

The live mode sends a very small request through the same `LLMClient` used by CORTEX. It prints provider mode, model, latency and response, but never prints the API key.

Expected success output includes:

```text
Provider mode : openai
Model         : gemini-2.5-flash
Response      : CORTEX_OK
RESULT        : LIVE PROVIDER CALL SUCCESS
```

For direct Gemini, provider mode will be `gemini` instead.

## How CORTEX chooses a provider

Prefer setting `LLM_MODE` explicitly in deployment environments.

- `openai` — OpenAI-compatible API, including CheaperInference when `OPENAI_BASE_URL=https://api.cheaperinference.com/v1`
- `gemini` — direct Google Gemini API
- `anthropic` — direct Anthropic API
- `ollama` — local Ollama
- `mock` / `heuristic` — offline fallback

For production or demo verification, confirm telemetry reports the expected provider and model rather than the offline mock/heuristic provider.
