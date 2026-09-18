import type { Page } from "@playwright/test";
// Fixtures exist only in browser tests; they are never imported by the application.
export const health = {
  status: "ok",
  system: "CORTEX",
  autonomy_level: 2,
  kill_switch_engaged: false,
  timestamp: new Date().toISOString(),
};
export const topology = {
  nodes: [
    {
      id: "api-gateway",
      name: "API Gateway",
      tier: "edge",
      criticality: 5,
      replicas: 3,
      is_stateful: false,
      health: "Healthy",
      rps: 250,
      p95_ms: 30,
      error_rate: 0.001,
      slo_ms: 80,
      region: "local",
    },
    {
      id: "payment-api",
      name: "Payment API",
      tier: "tier-1",
      criticality: 5,
      replicas: 6,
      is_stateful: false,
      health: "Degraded",
      rps: 380,
      p95_ms: 242,
      error_rate: 0.025,
      slo_ms: 200,
      region: "local",
    },
    {
      id: "user-profile-db",
      name: "PostgreSQL",
      tier: "stateful",
      criticality: 5,
      replicas: 1,
      is_stateful: true,
      health: "Healthy",
      rps: 120,
      p95_ms: 22,
      error_rate: 0.001,
      slo_ms: 50,
      region: "local",
    },
  ],
  edges: [
    { id: "a-b", source: "api-gateway", target: "payment-api" },
    { id: "b-c", source: "payment-api", target: "user-profile-db" },
  ],
};
export const incidents = [
  {
    id: "INC-TEST-101",
    service: "payment-api",
    severity: "P1",
    title: "Checkout latency above threshold",
    root_cause: "Connection pool exhausted",
    status: "OPEN",
    detected_at: "2026-09-17T10:00:00Z",
    resolved_at: null,
  },
];
export const operation = {
  proposal_id: "PROP-TEST-101",
  action_type: "scale_service",
  target: "payment-api",
  status: "BLOCKED",
  risk_score: 45,
  guard_decision: "REQUIRE_APPROVAL",
  verification_outcome: null,
  created_at: "2026-09-17T10:01:00Z",
  executed_at: null,
};
export const approval = {
  approval_id: "APP-TEST-101",
  incident_id: "INC-TEST-101",
  action_type: "scale_service",
  params: { service: "payment-api", replicas: 8 },
  risk_score: 45,
  created_at: Date.now() / 1000,
  ttl_seconds: 120,
  status: "pending",
};
export const blast = {
  score: 75,
  risk_level: "CRITICAL",
  directly_affected: "user-profile-db",
  affected_services: ["payment-api", "api-gateway"],
  critical_paths: [["api-gateway", "payment-api", "user-profile-db"]],
  explanation: "Database has no failover.",
  failover_ready: false,
};
export const twin = {
  action_type: "scale_service",
  target: "payment-api",
  blast_radius: blast,
  projected_downtime_sec: 0,
  reversibility: "REVERSIBLE",
  predicted_p95_ms: 170,
  predicted_error_rate: 0.005,
  simulated_p95_delta_ms: -72,
  slo_breaches: [],
  simulated_nodes: topology.nodes,
  summary: "Modeled scaling reduces latency.",
};
export const candidate = {
  name: "8 Replicas",
  replicas: 8,
  estimated_cost_per_hr: 0.64,
  expected_p95_ms: 150,
  reliability_risk_score: 20,
  slo_violation_probability: 0.005,
  energy_kwh_per_hr: 0.202,
  carbon_gco2_per_hr: 76.8,
  composite_loss: 0.3,
  is_pareto: true,
  slo_status: "PASS",
};
export async function mockApi(page: Page) {
  await page.route("https://fonts.googleapis.com/**", (r) => r.abort());
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api", "");
    const table: Record<string, unknown> = {
      "/health": health,
      "/topology": topology,
      "/incidents": { incidents },
      "/operations": { operations: [operation] },
      "/events/list": {
        events: [
          {
            event_id: "evt-1",
            timestamp: "2026-09-17T10:00:00Z",
            type: "incident_detected",
            payload: { service: "payment-api", incident_id: "INC-TEST-101" },
          },
        ],
      },
      "/cortex/approvals": { pending_approvals: [approval] },
      "/cortex/policies": {
        policies: [
          {
            code: "P-001",
            name: "Protect primary database",
            description: "Primary database restarts require review.",
          },
        ],
      },
      "/audit/ledger": {
        count: 1,
        integrity: { valid: true, total_events: 1 },
        records: [
          {
            timestamp: "2026-09-17T10:01:00Z",
            event_type: "action_blocked",
            actor: "guard",
            correlation_id: "INC-TEST-101",
            payload: { decision: "BLOCK" },
            hash: "test-hash",
            previous_hash: "0000",
          },
        ],
      },
      "/logs/audit": { logs: [] },
      "/chaos/experiments": { experiments: [] },
      "/twin/simulate": twin,
      "/topology/blast-radius": blast,
      "/forecast": {
        history: Array.from({ length: 30 }, (_, i) => ({
          timestamp: `10:${i}`,
          actual_rps: 250 + i * 3,
          cpu_percent: 40,
          p95_ms: 110,
        })),
        prediction: {
          current_rps: 337,
          model: "Test forecast",
          forecast_series: Array.from({ length: 30 }, (_, i) => ({
            timestamp: `11:${i}`,
            minute_offset: i + 1,
            predicted_rps: 337 + i * 2,
            low_bound: 310 + i,
            high_bound: 380 + i * 2,
            slo_threshold_rps: 520,
          })),
          recommended_replicas: 8,
          current_replicas: 6,
          adaptive_reserve_pct: 18,
          eval_metrics: { mae: 12 },
          model_metadata: { sample_count: 1000 },
        },
      },
      "/optimizer": {
        candidates: [candidate],
        selected_candidate: candidate,
        selection_rationale: "Eight replicas satisfy modeled constraints.",
        mode: "BALANCED",
        pareto_count: 1,
      },
      "/rag/retrieve": {
        results: [
          {
            id: "RB-001",
            title: "Connection pool recovery",
            document_type: "runbook",
            score: 0.92,
            tags: ["postgres"],
            content: "Review connection limits.",
          },
        ],
      },
      "/evaluation/benchmark": {
        retrieval: { mean_mrr: 0.8 },
        safety: { unsafe_prevention_rate: 100 },
        baselines: [],
      },
      "/tools/action": {
        status: "blocked",
        decision: "BLOCK",
        message: "Blocked by test policy.",
        execution_result: { status: "BLOCKED" },
      },
      "/cortex/approvals/resolve": { status: "success", outcome: "approved" },
      "/chaos/inject": { status: "injected", details: { status: "ACTIVE" } },
      "/chaos/clear": { status: "CLEARED" },
      "/pipeline/run": {
        status: "success",
        incident_id: "INC-TEST-101",
        total_duration_sec: 2.5,
        stages: Object.fromEntries(
          [
            "observe",
            "understand",
            "predict",
            "simulate",
            "optimize",
            "authorize",
            "act",
            "verify",
            "learn",
          ].map((s) => [s, { status: s === "act" ? "BLOCKED" : "recorded" }]),
        ),
        action_result: { status: "BLOCKED" },
        events: [],
      },
    };
    if (!(path in table)) {
      await route.fulfill({
        status: 404,
        json: { detail: `Unhandled fixture ${path}` },
      });
      return;
    }
    await route.fulfill({ json: table[path] });
  });
}
