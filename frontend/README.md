# CORTEX frontend

React 19 / TypeScript / Vite console and landing page, redesigned around the Brilean reference: an off-white canvas, charcoal text, lime accents, oversized editorial typography, and scroll-driven landing sections. The same presentation extends across all 21 console views while preserving their backend interactions. Inter Tight substitutes for the reference's commercial fonts; the metallic stars are original SVG artwork. FLOWSTACK Brick 0.2.2 buttons and accessible Radix dialogs remain in use. See [the design analysis and route mapping](BRILEAN_REDESIGN.md).

## Run locally

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. The local server forwards `/api/*` to `http://localhost:8000`. Start Python separately; see `BACKEND_READINESS_REPORT.md` for current startup blockers.

```powershell
# Optional alternative port/backend
$env:PORT = '3100'
$env:PYTHON_BACKEND_URL = 'http://localhost:8000'
npm run dev
```

The active entry is `src/main.tsx` → `src/control-plane/Application.tsx`; the active server is `console-server.ts`. Legacy `App.tsx`, `server.ts`, and older components remain preserved but are not the active entry. Their old mock responses are not used by this console.

## API configuration

- Same origin: leave `VITE_API_URL` empty and use the Node proxy.
- Separate deployment: set `VITE_API_URL=https://your-backend.example` before building, or set the backend address in **Connection settings**. The latter lasts for the browser session.
- An address ending in `/api` is normalized. HTTPS pages require an HTTPS API and appropriate CORS configuration.
- AI keys belong in the backend environment. Never put them in `VITE_*` variables or browser storage. This frontend does not need an AI key.

An unreachable backend produces an unavailable state. Production code never substitutes fixtures or fabricated action successes. Action timeouts instruct the operator to inspect execution history before retrying.

## Builds

```powershell
npm run build
$env:NODE_ENV = 'production'
npm start
```

This serves `dist` through the Node proxy. For a static host, including Website Deploy Toolkit:

```powershell
$env:VITE_API_URL = 'https://your-backend.example'
npm run build:static
```

Upload the **contents** of `dist-static`. Assets use relative paths; console navigation uses hash routes. A static host cannot run Python or the Node proxy. No public deployment was performed.

## Verification

```powershell
npm run lint
npm run lint:console
npx playwright install chromium
npm run test:e2e
```

Browser tests use port 3100 and explicit network fixtures under `tests/browser`. They verify frontend contracts and interactions, not production backend health. HTML results are under `playwright-report`; local screenshots/audit environments under `artifacts` are ignored by Git.

`npm test` remains the pre-existing legacy source/string-check suite. It does not replace active-console browser tests.

See [Brilean redesign](BRILEAN_REDESIGN.md) for the measured reference, visual mapping, and motion behavior; [frontend implementation](FRONTEND_IMPLEMENTATION_REPORT.md) for API feature coverage; [backend readiness](BACKEND_READINESS_REPORT.md) for the subsequent backend review; and [third-party licenses](THIRD_PARTY_LICENSES.md) for attribution. The redesign does not resolve the backend limitations documented in that review.
