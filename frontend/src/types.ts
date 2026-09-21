/**
 * AI SRE — Agentic Incident Risk Triage & Response System
 * Core Data Models & API Interfaces
 */

export type SeverityLevel = 'P1' | 'P2' | 'P3';

export type ActionCategory = 'neutral' | 'review_required' | 'high_impact';

export type ActiveView = 'overview' | 'simulator' | 'evidence' | 'actions' | 'audit';

export interface HealthResponse {
  status: string;
  system?: string;
  python_backend?: string;
  timestamp?: string;
}

export interface RagResultItem {
  id: string;
  title: string;
  score: number;
  text: string;
  document_type?: 'incident' | 'runbook' | string;
  kind?: string;
  filename?: string;
  tags?: string[] | string;
  metadata?: Record<string, any>;
}

export interface RagRetrieveResponse {
  query: string;
  count: number;
  results: RagResultItem[];
}

export interface ActionResponse {
  action_id?: string;
  action?: string;
  action_type?: string;
  status: 'success' | 'failed' | string;
  message?: string;
  result?: string;
  success?: boolean;
  timestamp?: string;
  execution_time_ms?: number;
  params?: Record<string, any>;
}

export interface EventItem {
  id?: string;
  event_id?: string;
  type: string;
  payload: Record<string, any>;
  timestamp?: string;
}

export type SystemEvent = EventItem;

export interface EventListResponse {
  count: number;
  events: EventItem[];
}

export interface AuditLogItem {
  action_id?: string;
  timestamp: string;
  action_type?: string;
  action?: string;
  status: string;
  message?: string;
  execution_time_ms?: number;
  params?: Record<string, any>;
  details?: string;
}

export interface AuditLogResponse {
  count: number;
  logs: AuditLogItem[];
}

export interface PipelineRunResponse {
  status: 'success' | 'failed' | string;
  service: string;
  total_duration_sec: number;
  retrieved_docs: RagResultItem[];
  action_result: ActionResponse;
  events: EventItem[];
  incident_id?: string;
  diagnosis?: any;
  plan?: string;
  action_executed?: string;
  verification?: string;
}

export interface ActionDefinition {
  type: string;
  name: string;
  description: string;
  category: ActionCategory;
  defaultParams: Record<string, any>;
}

export interface ServiceHealthItem {
  id: string;
  name: string;
  rps: number;
  errorRate: number;
  p99LatencyMs?: number;
  p95LatencyMs?: number;
  status: 'Stable' | 'Degraded' | 'Critical' | 'Healthy' | 'Warning' | string;
  region?: string;
  tier?: string;
  cpuPercent?: number;
  memoryPercent?: number;
  replicas?: number;
  dependencies?: string[];
  recentEvents?: string[];
}

export interface AutonomousAction {
  id: string;
  icon: string;
  title: string;
  timeAgo: string;
  reason: string;
  type: 'scaling' | 'maintenance' | 'security' | 'failover' | string;
}

export interface SimulationScenario {
  id: string;
  code: string;
  title: string;
  description: string;
  targetService: string;
  impactLevel: string;
  databaseOrTech: string;
}

export interface Incident {
  id: string;
  service: string;
  severity: SeverityLevel;
  timestamp: string;
  duration: string;
  outcome: string;
  summary: string;
  rootCause?: string;
  mitigationSteps?: string[];
  metricsSnapshot?: {
    rps: number;
    errorRate: number;
    latencyMs: number;
  };
}

export interface KnowledgeDoc {
  id: string;
  code: string;
  title: string;
  lastUpdated: string;
  docId: string;
  matchScore: number;
  source: 'Runbooks' | 'Post-Mortems' | 'Scripts' | string;
  tags: string[];
  summary: string;
  aiRecommendation: string;
  context: string;
  prerequisites: string[];
  codeLanguage: string;
  codeSnippet: string;
}

export interface SystemLog {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | string;
  service: string;
  message: string;
  traceId?: string;
}

export interface KpiMetrics {
  documentCount: string;
  documentCountChange: string;
  avgRetrievalMs: number;
  p99RetrievalMs: number;
  executionLatencyMs: number;
  systemReadiness: string;
}

/** LLM provider health status (from /api/v1/llm/status) */
export interface LLMProviderInfo {
  provider: string;
  configured?: boolean;
  credential_present?: boolean;
  credential_validated?: boolean;
  model?: string;
  model_available?: boolean | null;
  status: string;
  circuit_state?: string;
  is_paid?: boolean;
  cost_type?: string;
  latency_ms?: number | null;
  last_error_code?: string | null;
}

export interface LLMStatusResponse {
  primary: LLMProviderInfo;
  fallbacks: LLMProviderInfo[];
  active_provider: string;
  active_model: string;
  fallback_used: boolean;
  allow_paid_fallback: boolean;
  cost_controls: {
    max_output_tokens: number;
    timeout_seconds: number;
    max_retries: number;
    max_requests_per_incident: number;
  };
}



/** LLM provider health status (from /api/v1/llm/status) */
export interface LLMProviderInfo {
  provider: string;
  configured?: boolean;
  credential_present?: boolean;
  credential_validated?: boolean;
  model?: string;
  model_available?: boolean | null;
  status: string;
  circuit_state?: string;
  is_paid?: boolean;
  cost_type?: string;
  latency_ms?: number | null;
  last_error_code?: string | null;
}

export interface LLMStatusResponse {
  primary: LLMProviderInfo;
  fallbacks: LLMProviderInfo[];
  active_provider: string;
  active_model: string;
  fallback_used: boolean;
  allow_paid_fallback: boolean;
  cost_controls: {
    max_output_tokens: number;
    timeout_seconds: number;
    max_retries: number;
    max_requests_per_incident: number;
  };
}
