import type {
  Health,
  Topology,
  Incident,
  Operation,
  Event,
  Approval,
  Policy,
  Forecast,
  Optimization,
  Blast,
  Twin,
  EvidenceResponse,
  RetrievalContext,
  EvaluationReport,
  LlmStatus,
  Ledger,
  ActionResult,
  Pipeline,
  Experiment,
  RecordData,
} from "./contracts";

// Console access only. Provider credentials never belong in the browser.
let operatorAccess:
  { token: string; base: string; expiresAt: number } | undefined;
const ACCESS_TTL_MS = 30 * 60 * 1000;
export function clearOperatorToken() {
  operatorAccess = undefined;
}
export function setOperatorToken(value: string) {
  const token = value.trim();
  if (!token) return clearOperatorToken();
  if (!/^[\x21-\x7E]{8,4096}$/.test(token))
    throw new Error(
      "Use the server-issued console access token without spaces.",
    );
  if (/^(nvapi-|sk-|AIza|ci-)/.test(token))
    throw new Error(
      "AI provider API keys must stay on the backend. Enter a console access token here.",
    );
  operatorAccess = {
    token,
    base: getBase(),
    expiresAt: Date.now() + ACCESS_TTL_MS,
  };
}
export function hasOperatorToken(): boolean {
  if (
    operatorAccess &&
    (operatorAccess.base !== getBase() ||
      operatorAccess.expiresAt <= Date.now())
  )
    clearOperatorToken();
  return Boolean(operatorAccess);
}

export function normalizeBase(value: string): string {
  const clean = value
    .trim()
    .replace(/\/+$/, "")
    .replace(/\/api$/, "");
  if (!clean) return "";
  const url = new URL(clean);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  )
    throw new Error(
      "Use an HTTP or HTTPS backend address without credentials, query, or fragment.",
    );
  if (
    typeof location !== "undefined" &&
    location.protocol === "https:" &&
    url.protocol === "http:"
  )
    throw new Error("Use an HTTPS backend for this secure site.");
  return clean;
}
export function getBase() {
  return normalizeBase(
    sessionStorage.getItem("cortex.api.v1") ??
      import.meta.env.VITE_API_URL ??
      "",
  );
}
export function saveBase(value: string) {
  const base = normalizeBase(value);
  if (base !== getBase()) clearOperatorToken();
  sessionStorage.setItem("cortex.api.v1", base);
}
export async function request<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
  timeout = 20000,
): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) abort();
  signal?.addEventListener("abort", abort, { once: true });
  const timer = setTimeout(abort, timeout);
  try {
    const access = hasOperatorToken() ? operatorAccess : undefined;
    const response = await fetch(`${getBase()}/api${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        Accept: "application/json",
        "X-Correlation-ID": crypto.randomUUID(),
        ...(access ? { Authorization: `Bearer ${access.token}` } : {}),
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    const text = await response.text();
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(
        "The backend returned an unexpected response. Check the connection address.",
      );
    }
    if (!response.ok) {
      if (response.status === 401) {
        if (operatorAccess === access) clearOperatorToken();
        throw new Error(
          "Console access is required or has expired. Enter your server-issued access token in Connection settings.",
        );
      }
      if (response.status === 403)
        throw new Error(
          "Your console access does not allow this operation. An operator or administrator role is required.",
        );
      const error = data as {
        detail?: unknown;
        message?: string;
        error?: string;
      };
      throw new Error(
        typeof error.detail === "string"
          ? error.detail
          : error.message ||
              error.error ||
              `Request failed (${response.status}).`,
      );
    }
    return data as T;
  } catch (error) {
    if (controller.signal.aborted)
      throw new Error(
        "Request timed out or was cancelled. For an action, inspect operations before retrying.",
      );
    throw error instanceof Error
      ? error
      : new Error("Unable to reach the backend.");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}
export const client = {
  health: (s?: AbortSignal) => request<Health>("/health", undefined, s),
  llmStatus: (s?: AbortSignal) =>
    request<LlmStatus>("/v1/llm/status", undefined, s),
  topology: (s?: AbortSignal) => request<Topology>("/topology", undefined, s),
  incidents: (s?: AbortSignal) =>
    request<{ incidents: Incident[] }>("/incidents", undefined, s),
  operations: (s?: AbortSignal) =>
    request<{ operations: Operation[] }>("/operations", undefined, s),
  events: (s?: AbortSignal) =>
    request<{ events: Event[] }>("/events/list", undefined, s),
  emitNote: (message: string) =>
    request<{ status: string; message?: string }>("/events/emit", {
      type: "operator_note",
      payload: { message, source: "console" },
    }),
  clearEvents: () =>
    request<{ status: string; message?: string }>("/events/clear", {}),
  approvals: (s?: AbortSignal) =>
    request<{ pending_approvals: Approval[] }>(
      "/cortex/approvals",
      undefined,
      s,
    ),
  policies: (s?: AbortSignal) =>
    request<{ policies: Policy[] }>("/cortex/policies", undefined, s),
  ledger: (s?: AbortSignal) => request<Ledger>("/audit/ledger", undefined, s),
  logs: (s?: AbortSignal) =>
    request<{ logs: RecordData[] }>("/logs/audit", undefined, s),
  forecast: (horizon: number, s?: AbortSignal) =>
    request<Forecast>(`/forecast?horizon=${horizon}`, undefined, s),
  optimize: (mode: string, replicas: number, rps: number) =>
    request<Optimization>("/optimizer", {
      mode,
      current_replicas: replicas,
      forecast_rps: rps,
    }),
  twin: (action: string, params: RecordData) =>
    request<Twin>("/twin/simulate", { action_type: action, params }),
  blast: (action: string, params: RecordData) =>
    request<Blast>("/topology/blast-radius", { action_type: action, params }),
  retrieve: (query: string, k: number, context: RetrievalContext = {}) =>
    request<EvidenceResponse>(
      "/v1/evidence/retrieve",
      { query, context, options: { top_k: k } },
      undefined,
      90000,
    ),
  action: (action: string, params: RecordData) =>
    request<ActionResult>(
      "/tools/action",
      { action_type: action, params, actor: "console-operator" },
      undefined,
      120000,
    ),
  autonomy: (level: number) =>
    request<{ autonomy_level: number }>("/cortex/autonomy", { level }),
  freeze: (engaged: boolean) =>
    request<{ kill_switch_engaged: boolean }>("/cortex/kill-switch", {
      engaged,
      reason: "Operator request from CORTEX console",
    }),
  resolve: (approval_id: string, approved: boolean, approver: string) =>
    request<{
      status: string;
      message?: string;
      outcome?: string;
      execution_result?: RecordData;
    }>(
      "/cortex/approvals/resolve",
      { approval_id, approved, approver },
      undefined,
      120000,
    ),
  experiments: (s?: AbortSignal) =>
    request<{ experiments: Experiment[] }>("/chaos/experiments", undefined, s),
  chaos: (fault_type: string, target_service: string) =>
    request<RecordData>(
      "/chaos/inject",
      { fault_type, target_service },
      undefined,
      90000,
    ),
  clearChaos: (target_service: string) =>
    request<RecordData>(
      "/chaos/clear",
      { fault_type: "clear", target_service },
      undefined,
      90000,
    ),
  pipeline: (service: string, severity: string, symptom: string) =>
    request<Pipeline>(
      "/pipeline/run",
      { service, severity, symptom, simulate_dangerous: false },
      undefined,
      180000,
    ),
  benchmark: () =>
    request<EvaluationReport>(
      "/evaluation/benchmark",
      undefined,
      undefined,
      180000,
    ),
};
