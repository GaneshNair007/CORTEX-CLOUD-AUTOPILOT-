/**
 * AI SRE System — Typed API Client
 * Maps frontend UI calls directly to real FastAPI endpoints on port 8000.
 */

import {
  HealthResponse,
  RagRetrieveResponse,
  ActionResponse,
  EventListResponse,
  AuditLogResponse,
  PipelineRunResponse,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_URL ?? 'https://agentic-ops-1.onrender.com') + '/api';

class ApiClient {
  private async handleError(res: Response, defaultMessage: string): Promise<never> {
    let errorMessage = defaultMessage;
    try {
      const err = await res.json();
      if (err.detail) {
        if (Array.isArray(err.detail)) {
          // Pydantic validation error format
          errorMessage = err.detail.map((e: any) => `${e.loc?.join('.')} ${e.msg}`).join(', ');
        } else if (typeof err.detail === 'string') {
          errorMessage = err.detail;
        } else {
          errorMessage = JSON.stringify(err.detail);
        }
      }
    } catch (e) {
      errorMessage = res.statusText || defaultMessage;
    }
    throw new Error(errorMessage);
  }

  /**
   * Health Check
   * GET /api/health
   */
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, `Health check failed with HTTP ${res.status}`);
    }
    return res.json();
  }

  /**
   * Query RAG Vector Index
   * POST /api/rag/retrieve
   */
  async retrieve(query: string, k: number = 5): Promise<RagRetrieveResponse> {
    const res = await fetch(`${API_BASE}/rag/retrieve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, k }),
    });
    if (!res.ok) {
      await this.handleError(res, 'RAG retrieval failed');
    }
    return res.json();
  }

  /**
   * Execute Predefined Controlled Action
   * POST /api/tools/action
   */
  async executeAction(action_type: string, params: Record<string, any>): Promise<ActionResponse> {
    const res = await fetch(`${API_BASE}/tools/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action_type, params }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Action execution failed');
    }
    return res.json();
  }

  /**
   * List Events Timeline
   * GET /api/events/list
   */
  async listEvents(): Promise<EventListResponse> {
    const res = await fetch(`${API_BASE}/events/list`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, `Events list failed with HTTP ${res.status}`);
    }
    return res.json();
  }

  /**
   * Clear Session Events
   * POST /api/events/clear
   */
  async clearEvents(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/events/clear`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, `Clear events failed with HTTP ${res.status}`);
    }
    return res.json();
  }

  /**
   * Get Immutable Audit Logs
   * GET /api/logs/audit
   */
  async getAuditLogs(): Promise<AuditLogResponse> {
    const res = await fetch(`${API_BASE}/logs/audit`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, `Audit logs failed with HTTP ${res.status}`);
    }
    return res.json();
  }

  /**
   * Run Full Incident Pipeline
   * POST /api/pipeline/run
   */
  async runPipeline(service: string, severity: string, symptom: string, simulate_dangerous: boolean = false): Promise<PipelineRunResponse> {
    const res = await fetch(`${API_BASE}/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ service, severity, symptom, simulate_dangerous }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Pipeline execution failed');
    }
    return res.json();
  }

  /**
   * Get Live Infrastructure Topology
   * GET /api/topology
   */
  async getTopology(): Promise<{ nodes: any[]; edges: any[] }> {
    const res = await fetch(`${API_BASE}/topology`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to fetch topology');
    }
    return res.json();
  }

  /**
   * Calculate Blast Radius
   * POST /api/topology/blast-radius
   */
  async getBlastRadius(action_type: string, params: Record<string, any>): Promise<any> {
    const res = await fetch(`${API_BASE}/topology/blast-radius`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action_type, params }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Blast radius calculation failed');
    }
    return res.json();
  }

  /**
   * Simulate Action in Counterfactual Digital Twin
   * POST /api/twin/simulate
   */
  async simulateTwin(action_type: string, params: Record<string, any>): Promise<any> {
    const res = await fetch(`${API_BASE}/twin/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action_type, params }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Digital twin simulation failed');
    }
    return res.json();
  }

  /**
   * Get Workload Forecast
   * GET /api/forecast
   */
  async getForecast(horizon: number = 30): Promise<{ history: any[]; prediction: any }> {
    const res = await fetch(`${API_BASE}/forecast?horizon=${horizon}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to fetch forecast');
    }
    return res.json();
  }

  /**
   * Run Multi-Objective Optimizer
   * POST /api/optimizer
   */
  async getOptimizer(mode: string = 'BALANCED', current_replicas: number = 6, forecast_rps: number = 480): Promise<any> {
    const res = await fetch(`${API_BASE}/optimizer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, current_replicas, forecast_rps }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Optimizer execution failed');
    }
    return res.json();
  }

  /**
   * Get Active Policies
   * GET /api/cortex/policies
   */
  async getPolicies(): Promise<{ policies: any[] }> {
    const res = await fetch(`${API_BASE}/cortex/policies`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to fetch policies');
    }
    return res.json();
  }

  /**
   * Get Pending Approvals
   * GET /api/cortex/approvals
   */
  async getApprovals(): Promise<{ pending_approvals: any[] }> {
    const res = await fetch(`${API_BASE}/cortex/approvals`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to fetch approvals');
    }
    return res.json();
  }

  /**
   * Resolve Pending Approval
   * POST /api/cortex/approvals/resolve
   */
  async resolveApproval(approval_id: string, approved: boolean, approver: string = 'sre-lead'): Promise<any> {
    const res = await fetch(`${API_BASE}/cortex/approvals/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approval_id, approved, approver }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to resolve approval');
    }
    return res.json();
  }

  /**
   * Set Autonomy Level
   * POST /api/cortex/autonomy
   */
  async setAutonomy(level: number): Promise<any> {
    const res = await fetch(`${API_BASE}/cortex/autonomy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to set autonomy level');
    }
    return res.json();
  }

  /**
   * Set Emergency Kill Switch
   * POST /api/cortex/kill-switch
   */
  async setKillSwitch(engaged: boolean, reason: string = 'Manual operator trigger'): Promise<any> {
    const res = await fetch(`${API_BASE}/cortex/kill-switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ engaged, reason }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to toggle kill switch');
    }
    return res.json();
  }

  /**
   * Get Hash-Chained Evidence Ledger
   * GET /api/audit/ledger
   */
  async getLedger(): Promise<{ count: number; integrity: any; records: any[] }> {
    const res = await fetch(`${API_BASE}/audit/ledger`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to fetch evidence ledger');
    }
    return res.json();
  }

  /**
   * Get Benchmark Evaluation Results
   * GET /api/evaluation/benchmark
   */
  async getBenchmark(): Promise<any> {
    const res = await fetch(`${API_BASE}/evaluation/benchmark`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      await this.handleError(res, 'Failed to fetch benchmark');
    }
    return res.json();
  }

  /**
   * Inject Controlled Chaos Fault
   * POST /api/chaos/inject
   */
  async injectChaos(fault_type: string, target_service: string = 'payment-api'): Promise<any> {
    const res = await fetch(`${API_BASE}/chaos/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fault_type, target_service }),
    });
    if (!res.ok) {
      await this.handleError(res, 'Chaos injection failed');
    }
    return res.json();
  }
}

export const api = new ApiClient();
