export type Json =
  null | boolean | number | string | Json[] | { [key: string]: Json };
export type RecordData = Record<string, Json>;
export interface Health {
  status: string;
  system: string;
  autonomy_level: number;
  kill_switch_engaged: boolean;
  timestamp: string;
  system_health_pct?: number | null;
  storage?: string;
}
export interface LlmStatus {
  primary: {
    provider: string;
    model?: string;
    status: string;
    credential_present?: boolean;
  };
  active_provider: string;
  active_model: string;
  status: string;
  fallback_used: boolean;
  latency_ms?: number | null;
  last_call?: {
    provider: string;
    model: string;
    fallback_used: boolean;
    completed_at?: number;
    latency_ms?: number;
  } | null;
  configured_fallbacks: string[];
  deterministic_safety: string;
}
export interface Service {
  id: string;
  name: string;
  tier: string;
  health: string;
  replicas: number;
  rps: number;
  p95_ms: number;
  error_rate: number;
  slo_ms: number;
  region: string;
  criticality: number;
  is_stateful: boolean;
  failover_available?: boolean;
}
export interface Topology {
  nodes: Service[];
  edges: { id: string; source: string; target: string; protocol?: string }[];
}
export interface Incident {
  id: string;
  service: string;
  severity: string;
  title: string;
  root_cause: string | null;
  status: string;
  detected_at: string | null;
  resolved_at: string | null;
}
export interface Operation {
  proposal_id: string;
  action_type: string;
  target: string;
  status: string;
  risk_score: number;
  guard_decision: string | null;
  verification_outcome: string | null;
  created_at: string;
  executed_at: string | null;
}
export interface Event {
  event_id: string;
  timestamp: string;
  type: string;
  payload: RecordData;
}
export interface Approval {
  approval_id: string;
  incident_id?: string;
  action_type: string;
  params: RecordData;
  risk_score: number;
  created_at: number;
  ttl_seconds: number;
  status: string;
}
export interface Policy {
  code: string;
  name: string;
  description: string;
}
export interface Forecast {
  history: {
    timestamp: string;
    actual_rps: number;
    cpu_percent: number;
    p95_ms: number;
  }[];
  prediction: {
    current_rps: number;
    model: string;
    forecast_series: {
      timestamp: string;
      predicted_rps: number;
      low_bound: number;
      high_bound: number;
      minute_offset: number;
      slo_threshold_rps: number;
    }[];
    recommended_replicas: number;
    current_replicas: number;
    adaptive_reserve_pct: number;
    eval_metrics: RecordData | null;
    model_metadata: RecordData;
  };
}
export interface Candidate {
  name: string;
  replicas: number;
  estimated_cost_per_hr: number;
  expected_p95_ms: number;
  reliability_risk_score: number;
  slo_violation_probability: number;
  energy_kwh_per_hr: number;
  carbon_gco2_per_hr: number;
  composite_loss: number;
  is_pareto: boolean;
  slo_status: string;
}
export interface Optimization {
  candidates: Candidate[];
  selected_candidate: Candidate;
  selection_rationale: string;
  mode: string;
  pareto_count: number;
}
export interface Blast {
  score: number;
  risk_level: string;
  directly_affected: string;
  affected_services: string[];
  critical_paths: string[][];
  explanation: string;
  failover_ready: boolean;
}
export interface Twin {
  action_type: string;
  target: string;
  blast_radius: Blast;
  projected_downtime_sec: number;
  reversibility: string;
  predicted_p95_ms: number;
  predicted_error_rate: number;
  simulated_p95_delta_ms: number;
  slo_breaches: string[];
  simulated_nodes: Service[];
  summary: string;
}
export interface Evidence {
  id: string;
  title: string;
  document_type: string;
  score: number;
  tags: string[];
  content?: string;
  text?: string;
  filename?: string;
  final_score?: number;
  semantic_score?: number;
  lexical_score?: number;
  context_score?: number;
  recency_score?: number;
  trust_score?: number;
  outcome_score?: number;
  why_retrieved?: string[];
  retrieval_stage?: string;
  verification_outcome?: string;
  historical_action?: string;
  simulated?: boolean;
  environment?: string;
  memory_status?: string;
  rollback_performed?: boolean;
  slo_recovered?: boolean;
  mttr?: number;
}
export interface EvidenceResponse {
  results: Evidence[];
  status?: string;
  warnings?: string[];
  retrieval_stage?: string;
  retrieval_time_ms?: number;
  candidate_count?: number;
  stages_attempted?: string[];
  relaxed_filters?: string[];
  filters_applied?: RecordData;
  semantic_available?: boolean;
}
export interface RetrievalContext {
  service?: string;
  environment?: string;
  technologies?: string[];
  failure_mode?: string;
}
export interface RetrievalMetrics {
  strategy: string;
  scenarios: number;
  hit_at_1: number;
  hit_at_3: number;
  recall_at_5: number;
  mrr: number;
  ndcg_at_5: number;
  mean_latency_ms: number;
  p95_latency_ms: number;
}
export interface EvaluationReport {
  status: string;
  timestamp: string;
  corpus_size: number;
  embedding_model: string;
  model_index_warmup_ms: number;
  retrieval: RetrievalMetrics;
  baselines: RetrievalMetrics[];
  limitations: string[];
  safety: { status: string; reason: string };
}
export interface Ledger {
  count: number;
  integrity: {
    valid: boolean;
    total_events?: number;
    reason?: string;
    latest_hash?: string;
  };
  records: {
    timestamp: string;
    event_type: string;
    actor: string;
    correlation_id: string;
    payload: RecordData;
    hash: string;
    previous_hash: string;
  }[];
}
export interface Execution {
  status: string;
  output?: RecordData;
  operation_id?: string;
  target?: string;
  action_type?: string;
}
export interface ActionResult {
  status: string;
  decision?: string;
  message?: string;
  approval_id?: string;
  action_result?: Execution;
  execution_result?: Execution;
  verification?: RecordData;
}
export interface Pipeline {
  status: string;
  incident_id: string;
  total_duration_sec: number;
  stages: Record<string, RecordData>;
  action_result: Execution;
  events: Event[];
}
export interface Experiment {
  experiment_id: string;
  target_service: string;
  fault_type: string;
  status: string;
  expires_at?: number;
  duration_sec?: number;
}
