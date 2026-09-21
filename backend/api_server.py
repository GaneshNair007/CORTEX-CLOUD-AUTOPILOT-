"""
CORTEX Cloud Autopilot — FastAPI Backend Control Plane
Exposes RAG retrieval, infrastructure topology, counterfactual digital twin,
multi-objective optimizer, CORTEX Guard governance, and closed-loop verification.

Launch:
    python api_server.py
"""

import sys
import json
import time
import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root and backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
PROJECT_ROOT = BACKEND_DIR

# settings.py loads .env for both repo root and backend dir at import time.
# Do NOT call load_dotenv() here again — process env always wins over .env.
from backend.config.settings import settings  # noqa: E402  (must come after sys.path setup)

from backend import interfaces
from backend.rag.retrieve import retrieve
from backend.tools.actions import execute_action, AUDIT_LOG_PATH
from backend.tools.event_bus import emit_event, get_events, clear_events, EVENTS_FILE_PATH
from backend.topology.graph import topology
from backend.topology.blast_radius import calculate_blast_radius
from backend.twin.simulator import twin
from backend.cortex.guard import guard
from backend.cortex.policies import ACTIVE_POLICIES
from backend.cortex.ledger import ledger
from backend.cortex.gateway import execution_gateway
from backend.models.proposals import ActionProposal
from backend.chaos.engine import chaos_engine
from backend.control_plane.pipeline import control_plane
from backend.persistence.database import db_manager
from backend.forecasting.forecaster import forecaster
from backend.forecasting.anomalies import anomaly_detector
from backend.optimization.optimizer import optimizer
from backend.verification.verifier import verifier
from backend.orchestrator.agent import IncidentAgent
from backend.evaluation.harness import EvaluationHarness
from backend.retrieval.models import EvidenceRequest, RetrievalContext, RetrievalOptions
from backend.retrieval.engine import get_engine
from backend.retrieval.config import get_config
from backend.observability.metrics_collector import metrics_collector
from backend.slo.config import SERVICE_SLOS, calculate_burn_rate, get_slo_for_service

get_config()  # Reject invalid deployment configuration at startup.

# ---------------------------------------------------------------------------
# RAG index auto-build: if the ChromaDB collection is empty, rebuild it once
# at startup so the app works out of the box without a manual step.
# ---------------------------------------------------------------------------
from contextlib import asynccontextmanager
import asyncio
import logging

@asynccontextmanager
async def lifespan(app):
    from backend.retrieval.startup import initialize
    try:
        await asyncio.to_thread(initialize)
    except Exception as exc:
        logging.getLogger(__name__).warning("Semantic startup degraded: %s; lexical retrieval remains available", type(exc).__name__)
    if os.environ.get("CORTEX_START_SANDBOX", "false").lower() == "true":
        from sandbox.manager import sandbox_manager
        sandbox_manager.start_all()
    yield
    if os.environ.get("CORTEX_START_SANDBOX", "false").lower() == "true":
        sandbox_manager.stop_all()

app = FastAPI(
    title="CORTEX Cloud Autopilot API",
    lifespan=lifespan,
    version="2.0.0",
    description="Predictive, Policy-Governed Autonomous Cloud Control Plane"
)

from backend.security.api_auth import install_security
install_security(app)
# CORS wraps auth, so protected failures remain visible to permitted frontends.
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
    allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"], expose_headers=["X-Correlation-ID"])

# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------
class RetrieveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=12000)
    k: int = Field(default=5, ge=1, le=20, strict=True)

class ActionRequest(BaseModel):
    action_type: str
    params: Dict[str, Any]
    incident_id: Optional[str] = "INC-MANUAL"
    actor: Optional[str] = "operator"
    reason: str | None = Field(default=None, max_length=4000)
    dry_run: bool = False
    idempotency_key: str | None = Field(default=None, max_length=128)

class EventRequest(BaseModel):
    type: str
    payload: Dict[str, Any]

class PipelineRequest(BaseModel):
    service: Optional[str] = "payment-api"
    severity: Optional[str] = "P1"
    symptom: Optional[str] = "HTTP 504 Gateway Timeout spike on /v1/checkout"
    simulate_dangerous: Optional[bool] = False

class SimulateRequest(BaseModel):
    action_type: str
    params: Dict[str, Any]

class OptimizeRequest(BaseModel):
    mode: Optional[str] = "BALANCED"
    current_replicas: Optional[int] = 6
    forecast_rps: Optional[float] = 480.0
    target_service: Optional[str] = "payment-service"
    predicted_traffic: Optional[float] = None

class ForecastPredictRequest(BaseModel):
    service: Optional[str] = "payment-service"
    horizon: int = Field(default=30, ge=5, le=60)
    history: Optional[List[float]] = Field(default=None, min_length=30, max_length=5000)

class ApprovalResolveRequest(BaseModel):
    approval_id: str
    approved: bool
    approver: Optional[str] = "sre-lead"

class AutonomyRequest(BaseModel):
    level: int = Field(ge=0, le=3)

class KillSwitchRequest(BaseModel):
    engaged: bool
    reason: Optional[str] = "Manual operator intervention"

class ChaosRequest(BaseModel):
    fault_type: str  # 'pod_kill' | 'cpu_saturation' | 'db_outage' | 'latency' | 'traffic_spike'
    target_service: Optional[str] = "payment-api"


# -----------------------------------------------------------------------------
# Core Health & System Endpoints
# -----------------------------------------------------------------------------
@app.get("/")
def read_root():
    index_path = PROJECT_ROOT / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"system": "CORTEX Cloud Autopilot Control Plane", "version": "2.0.0", "status": "active"}

@app.get("/api/ping")
def ping():
    """Lightweight keep-alive endpoint. No DB or LLM calls. Used by uptime monitors."""
    return {"pong": True, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


@app.get("/healthz")
def liveness():
    """Process liveness only, suitable for hosting probes without credentials."""
    return {"status": "alive"}


@app.get("/readyz")
def readiness():
    """Check SQL and index readiness without making an LLM request."""
    from sqlalchemy import text
    from backend.persistence.database import engine
    from backend.retrieval.startup import index_status
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        rag = index_status()
        ready = rag["status"] == "ready"
        return JSONResponse(status_code=200 if ready else 503,
            content={"status": "ready" if ready else "degraded", "sql": "ready", "retrieval": rag})
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "unavailable", "reason": type(exc).__name__})


@app.get("/api/health")
def health_check():
    """
    Real component readiness check.
    Never returns fake static percentages.
    LLM status is truthful: shows actual provider, model, and fallback state.
    """
    from backend.retrieval.startup import index_status
    llm_status = api_llm_status()
    rag = index_status()
    integrity = ledger.verify_integrity().get("valid", False)
    return {
        "status": "ok" if rag["status"] == "ready" and integrity else "degraded",
        "system": "CORTEX Cloud Autopilot", "version": "2.1.0",
        "autonomy_level": guard.autonomy_level, "kill_switch_engaged": guard.kill_switch_engaged,
        "active_incidents": len(db_manager.list_incidents(status="OPEN", limit=100000)),
        "system_health_pct": None,
        "components": {"llm": llm_status, "rag": rag,
                       "executor": {"provider": type(execution_gateway.provider).__name__, "environment": "sandbox"},
                       "ledger": {"status": "healthy" if integrity else "degraded", "integrity": integrity}},
        "storage": "persistent" if os.environ.get("CORTEX_PERSISTENT_STORAGE") == "true" else "DEMO EPHEMERAL STORAGE",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# -----------------------------------------------------------------------------
# LLM Provider Status (detailed, operator-facing)
# -----------------------------------------------------------------------------
@app.get("/api/v1/llm/status")
def api_llm_status():
    """
    Detailed LLM provider health status.
    No secret values are ever included in this response.
    Wallet balance is NOT included (requires authenticated operator endpoint).
    """
    from backend.llm.health import llm_health_monitor
    cfg = settings.llm
    primary = llm_health_monitor.get_health(cfg.provider)
    last = llm_health_monitor.last_route()
    active = last.get("provider", cfg.provider)
    active_health = llm_health_monitor.get_health(active)
    status = "DEGRADED" if active == "heuristic" else active_health.status.value if active_health else "UNAVAILABLE"
    return {
        "primary": primary.to_api_dict() if primary else {"provider": cfg.provider, "model": cfg.active_model, "status": "CONFIGURED" if cfg.credential_present else "UNAVAILABLE", "credential_present": cfg.credential_present},
        "active_provider": active, "active_model": last.get("model", cfg.active_model),
        "model": last.get("model", cfg.active_model), "status": status,
        "fallback_used": last.get("fallback_used", False), "last_call": last or None,
        "latency_ms": last.get("latency_ms"),
        "fallbacks": [h.to_api_dict() for name, h in llm_health_monitor.get_all_health().items() if name != cfg.provider],
        "configured_fallbacks": cfg.fallback_providers,
        "allow_paid_fallback": cfg.allow_paid_llm_fallback,
        "cost_controls": {"max_output_tokens": cfg.max_output_tokens, "timeout_seconds": cfg.timeout_seconds,
                          "max_retries": cfg.max_retries, "max_requests_per_incident": cfg.max_requests_per_incident},
        "deterministic_safety": "ONLINE",
    }


@app.get("/api/v1/llm/provider-health")
def api_llm_provider_health():
    """
    Non-billable provider health probe (uses metadata endpoints, not inference).
    Suitable for readiness checks. Does NOT generate text.
    """
    from backend.llm.client import _build_provider
    llm_cfg = settings.llm

    provider = _build_provider(llm_cfg.provider)
    if provider is None:
        return {
            "provider": llm_cfg.provider,
            "status": "UNAVAILABLE",
            "error_code": "MISSING_CREDENTIAL",
            "model": llm_cfg.active_model,
        }

    result = provider.health_check()
    # Metadata reachability does not prove that an inference request succeeded.
    return result


# -----------------------------------------------------------------------------
# Topology & Digital Twin Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/topology")
def api_get_topology():
    return topology.get_topology_data()

@app.post("/api/topology/blast-radius")
def api_blast_radius(req: SimulateRequest):
    return calculate_blast_radius(req.action_type, req.params)

@app.post("/api/twin/simulate")
def api_simulate_twin(req: SimulateRequest):
    return twin.simulate_action(req.action_type, req.params)


# -----------------------------------------------------------------------------
# Forecasting & Optimization Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/forecast")
@app.get("/api/forecasting/predict")
def api_get_forecast(horizon: int = Query(30, ge=5, le=60)):
    history = forecaster.generate_live_telemetry_series(window_points=30)
    prediction = forecaster.predict_workload(horizon_minutes=horizon, history_series=history)
    return {"history": history, "prediction": prediction, "source": "generated_workload_model", "simulated": True}

@app.post("/api/forecasting/predict")
def api_post_forecast(req: ForecastPredictRequest):
    history = [{"actual_rps": value} for value in req.history] if req.history else forecaster.generate_live_telemetry_series(window_points=30)
    horizon = req.horizon or 30
    prediction = forecaster.predict_workload(horizon_minutes=horizon, history_series=history)
    return {"service": req.service, "history": history, "prediction": prediction, "source": "supplied_history" if req.history else "generated_workload_model", "simulated": req.history is None}

@app.post("/api/optimizer")
@app.post("/api/optimizer/solve")
def api_optimize(req: OptimizeRequest):
    rps = req.forecast_rps if req.predicted_traffic is None else req.predicted_traffic
    return optimizer.optimize(
        mode=req.mode or "BALANCED",
        current_replicas=req.current_replicas or 6,
        forecast_rps=rps or 480.0
    )


# -----------------------------------------------------------------------------
# CORTEX Guard & Governance Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/cortex/policies")
def api_list_policies():
    return {
        "policies": [
            {"code": p.code, "name": p.name, "description": p.description}
            for p in ACTIVE_POLICIES
        ]
    }

@app.get("/api/cortex/approvals")
def api_list_approvals():
    return {"pending_approvals": [
        {**r.model_dump(mode="json"), "status": r.status.lower(),
         "created_at": r.created_at.timestamp(),
         "ttl_seconds": (r.expires_at - r.created_at).total_seconds()}
        for r in execution_gateway.approved_tokens.values() if r.status == "PENDING"
    ]}

@app.post("/api/cortex/approvals/resolve")
def api_resolve_approval(req: ApprovalResolveRequest, request: Request):
    actor = request.state.actor
    token = (execution_gateway.approve_action if req.approved else execution_gateway.reject_action)(req.approval_id, actor)
    if token is None:
        raise HTTPException(404, "Approval not found")
    response = {"status": token.status.lower(), "approval_id": req.approval_id}
    if req.approved and token.status == "APPROVED":
        proposal = ActionProposal(proposal_id=token.proposal_id, incident_id=token.incident_id,
            action_type=token.action_type, target=token.target, params=token.params,
            risk_score=token.risk_score, state_version=token.state_version, generated_by=actor)
        response["execution_result"] = execution_gateway.evaluate_and_execute(proposal, approval_id=req.approval_id).model_dump(mode="json")
    return response

@app.post("/api/cortex/autonomy")
def api_set_autonomy(req: AutonomyRequest):
    guard.set_autonomy_level(req.level)
    return {"status": "success", "autonomy_level": guard.autonomy_level}

@app.post("/api/cortex/kill-switch")
def api_set_kill_switch(req: KillSwitchRequest):
    guard.set_kill_switch(req.engaged, req.reason or "")
    execution_gateway.set_freeze_mutations(req.engaged)
    return {"status": "success", "kill_switch_engaged": guard.kill_switch_engaged}


# -----------------------------------------------------------------------------
# RAG Knowledge Base & Actions
# -----------------------------------------------------------------------------
@app.post("/api/v1/evidence/retrieve")
def api_evidence_retrieve(req: EvidenceRequest):
    context = RetrievalContext(query_text=req.query, incident_id=req.incident_id, **req.context.model_dump())
    return get_engine().retrieve(context, req.options).public_response()


@app.post("/api/rag/retrieve", deprecated=True)
def api_retrieve(req: RetrieveRequest):
    bundle = get_engine().retrieve(RetrievalContext(query_text=req.query), RetrievalOptions(top_k=req.k))
    result = bundle.public_response()
    return {**result, "query": req.query, "count": len(result["results"])}

@app.post("/api/tools/action")
def api_action(req: ActionRequest, request: Request):
    """
    Guarded action dispatch: Every action must pass through CortexExecutionGateway.
    """
    target = req.params.get("service") or req.params.get("target") or "payment-service"
    proposal = ActionProposal(
        incident_id=req.incident_id or "INC-MANUAL",
        action_type=req.action_type,
        target=target,
        params=req.params,
        risk_score=50,
        reason=req.reason or f"Manual {req.action_type} requested for {target}",
        generated_by=request.state.actor, dry_run=req.dry_run
    )

    exec_result = execution_gateway.evaluate_and_execute(proposal, idempotency_key=req.idempotency_key)

    if exec_result.status == "BLOCKED":
        if "approval_id" in exec_result.output:
            return {
                "status": "approval_required",
                "decision": "REQUIRE_APPROVAL",
                "approval_id": exec_result.output["approval_id"],
                "message": f"Action '{req.action_type}' requires human authorization.",
                "execution_result": exec_result.model_dump(mode="json")
            }
        return {
            "status": "blocked",
            "decision": "BLOCK",
            "message": f"Action '{req.action_type}' was BLOCKED by CORTEX Execution Gateway: {exec_result.output.get('reason', 'Blocked by policy')}",
            "execution_result": exec_result.model_dump(mode="json")
        }

    return {
        "status": exec_result.status.lower(),
        "decision": "ALLOW",
        "action_result": exec_result.model_dump(mode="json"),
        "verification": exec_result.output
    }


# -----------------------------------------------------------------------------
# Events, Audit Ledger & Verification
# -----------------------------------------------------------------------------
@app.post("/api/events/emit")
def api_emit_event(req: EventRequest):
    emit_event({"type": req.type, "payload": req.payload})
    return {"status": "success", "message": "Event emitted"}

@app.get("/api/events/list")
def api_list_events():
    return {"count": len(get_events()), "events": get_events()}

@app.post("/api/events/clear")
def api_clear_events():
    clear_events()
    return {"status": "success", "message": "Events timeline cleared"}

@app.get("/api/logs/audit")
def api_audit_logs():
    if not AUDIT_LOG_PATH.exists():
        return {"count": 0, "logs": []}
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f.readlines()]
    return {"count": len(logs), "logs": logs}

@app.get("/api/audit/ledger")
def api_get_ledger():
    records = ledger.list_records(limit=100)
    integrity = ledger.verify_integrity()
    return {"count": len(records), "integrity": integrity, "records": records}

@app.get("/api/evaluation/benchmark")
def api_get_benchmark():
    harness = EvaluationHarness()
    return harness.run_full_evaluation()


# -----------------------------------------------------------------------------
# Chaos Engineering Fault Injection
# -----------------------------------------------------------------------------
@app.post("/api/chaos/inject")
def api_chaos_inject(req: ChaosRequest):
    """Executes real controlled chaos fault injection in sandbox."""
    target = req.target_service or "payment-service"
    fault_map = {
        "pod_kill": "crash",
        "cpu_saturation": "cpu_stress",
        "db_outage": "db_outage",
        "latency": "latency",
        "traffic_spike": "traffic_flood"
    }
    actual_fault = fault_map.get(req.fault_type, req.fault_type)
    try:
        res = chaos_engine.inject_fault(
            target_service=target,
            fault_type=actual_fault,
            duration_sec=30,
            intensity=200.0 if actual_fault == "latency" else 1.0,
            environment="sandbox"
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    emit_event({
        "type": "chaos_fault_injected",
        "payload": {"fault_type": req.fault_type, "target": target, "result": res}
    })
    return {"status": "injected" if res.get("status") == "ACTIVE" else res.get("status", "FAILED").lower(),
            "fault": req.fault_type, "target": target, "details": res}

@app.get("/api/chaos/experiments")
def api_list_chaos_experiments():
    return {"experiments": chaos_engine.list_active_experiments()}

@app.post("/api/chaos/clear")
def api_clear_chaos(req: ChaosRequest):
    target = req.target_service or "payment-service"
    return chaos_engine.clear_faults(target, environment="sandbox")


# -----------------------------------------------------------------------------
# Persistence: Incidents & Operations
# -----------------------------------------------------------------------------
@app.get("/api/incidents")
def api_list_incidents(status: Optional[str] = None):
    return {"incidents": db_manager.list_incidents(status=status)}

@app.get("/api/operations")
def api_list_operations():
    return {"operations": db_manager.list_operations()}


# -----------------------------------------------------------------------------
# Master Closed-Loop Autonomous Pipeline
# -----------------------------------------------------------------------------
@app.post("/api/pipeline/run")
def api_run_pipeline(req: PipelineRequest):
    """
    Closed-Loop Autopilot Workflow:
    Observe -> Understand -> Predict -> Simulate -> Optimize -> Authorize -> Act -> Verify -> Learn.
    Executed through master ControlPlanePipeline and CortexExecutionGateway.
    """
    return control_plane.run_control_loop(
        service=req.service or "payment-service",
        severity=req.severity or "P1",
        symptom=req.symptom or "HTTP 500 error spike",
        simulate_dangerous=bool(req.simulate_dangerous)
    )


# -----------------------------------------------------------------------------
# LLM Cost / Telemetry (operator-facing, not public)
# -----------------------------------------------------------------------------
@app.get("/api/v1/llm/cost/{incident_id}")
def api_llm_cost(incident_id: str):
    """Per-incident LLM cost summary. No prompt content included."""
    from backend.llm.telemetry import incident_cost_tracker
    data = incident_cost_tracker.get(incident_id)
    if not data:
        return {"incident_id": incident_id, "calls": 0, "message": "No LLM data for this incident"}
    return {"incident_id": incident_id, **data}


# -----------------------------------------------------------------------------
# NEW: Incident detail by ID
# -----------------------------------------------------------------------------
@app.get("/api/incidents/{incident_id}")
def api_get_incident(incident_id: str):
    """Returns a single incident record by ID."""
    incidents = db_manager.list_incidents(limit=1000)
    match = next((i for i in incidents if i["id"] == incident_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return match


# -----------------------------------------------------------------------------
# NEW: Live service health list (all 8 sandbox microservices)
# -----------------------------------------------------------------------------
@app.get("/api/services")
def api_list_services():
    """Returns live telemetry snapshot for all monitored microservices."""
    services = []
    for name, t in metrics_collector.collect_all().items():
        slo = get_slo_for_service(name)
        measured = t.metrics_available and t.freshness == "FRESH"
        error = t.error_rate_pct
        latency = t.p95_latency_ms
        status = ("Unknown" if not measured else "Critical" if error > slo.max_error_rate * 500
                  else "Degraded" if error > slo.max_error_rate * 100 else "Warning" if latency > slo.max_p95_ms else "Healthy")
        services.append({"id": name, "name": name.replace("-", " ").title(), "status": status,
            "rps": t.rps, "errorRate": error, "p95LatencyMs": latency, "p99LatencyMs": t.p99_latency_ms,
            "cpuPercent": t.cpu_percent, "memoryPercent": t.memory_percent, "replicas": t.active_replicas,
            "freshness": t.freshness, "source": t.source, "simulated": t.simulated, "warnings": t.warnings,
            "slo": {"max_error_rate_pct": slo.max_error_rate * 100, "max_p95_ms": slo.max_p95_ms,
                    "burn_rate": calculate_burn_rate(error / 100, slo) if measured else None}})
    return {"count": len(services), "services": services}


# -----------------------------------------------------------------------------
# NEW: LLM provider health check
# -----------------------------------------------------------------------------
@app.get("/api/llm/health")
def api_llm_health():
    """Returns LLM provider status, circuit-breaker state, and config (no secrets)."""
    return api_llm_status()


# -----------------------------------------------------------------------------
# NEW: Sandbox microservice status
# -----------------------------------------------------------------------------
@app.get("/api/sandbox/status")
def api_sandbox_status():
    """Returns running state of all 8 sandbox microservices."""
    from sandbox.manager import sandbox_manager
    statuses = {name: sandbox_manager.get_health(name) for name in sandbox_manager.specs}
    return {"running": all(value.get("status") == "UP" for value in statuses.values()),
            "simulated": True, "services": statuses}


# -----------------------------------------------------------------------------
# NEW: SLO summary — real burn rates from live telemetry
# -----------------------------------------------------------------------------
@app.get("/api/slo/summary")
def api_slo_summary():
    """Computes real SLO burn rates for all services from live telemetry."""
    results = []
    for service, telemetry in metrics_collector.collect_all().items():
        slo = get_slo_for_service(service)
        measured = telemetry.metrics_available and telemetry.freshness == "FRESH"
        error = telemetry.error_rate_pct / 100 if measured else None
        burn = calculate_burn_rate(error, slo) if error is not None else None
        results.append({"service": service, "target_pct": slo.min_availability * 100,
            "current_pct": (1 - error) * 100 if error is not None else None,
            "p95_ms": telemetry.p95_latency_ms, "p95_target_ms": slo.max_p95_ms,
            "error_rate_pct": telemetry.error_rate_pct, "instantaneous_burn_rate": burn,
            "burn_rate_1h": None, "error_budget_remaining_pct": None,
            "status": "UNKNOWN" if not measured else "BURNING" if burn > 1 else "HEALTHY",
            "simulated": telemetry.simulated, "source": telemetry.source,
            "note": "Snapshot ratio only; no rolling SLO window or accumulated error-budget history is available"})
    return {"count": len(results), "slos": results}


# -----------------------------------------------------------------------------
# NEW: Cost summary — real hourly run rate derived from live replica counts
# -----------------------------------------------------------------------------
@app.get("/api/cost/summary")
def api_cost_summary():
    """
    Returns real-time cost estimates derived from live replica/CPU telemetry.
    Uses AWS us-east-1 on-demand c5.xlarge pricing as reference.
    """
    unit_rate = float(os.environ.get("CORTEX_ESTIMATED_REPLICA_HOURLY_USD", "0.08"))
    breakdown = []
    for name, telemetry in metrics_collector.collect_all().items():
        if telemetry.active_replicas is not None:
            hourly = round(telemetry.active_replicas * unit_rate, 4)
            breakdown.append({"service": name, "replicas": telemetry.active_replicas,
                "hourly_usd": hourly, "monthly_usd": round(hourly * 730, 2), "simulated": True})
    total = sum(item["hourly_usd"] for item in breakdown)
    return {"total_hourly_usd": total if breakdown else None,
            "total_monthly_usd": round(total * 730, 2) if breakdown else None,
            "dynamic_services": breakdown, "fixed_infrastructure": [], "currency": "USD",
            "source": "configured_unit_rate_estimate", "billing_connected": False,
            "unit_rate_usd": unit_rate, "note": "Hypothetical replica model; no cloud bill or current vendor pricing is connected"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
