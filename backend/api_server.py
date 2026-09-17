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
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root and backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
PROJECT_ROOT = BACKEND_DIR

import interfaces
from rag.retrieve import retrieve
from tools.actions import execute_action, AUDIT_LOG_PATH
from tools.event_bus import emit_event, get_events, clear_events, EVENTS_FILE_PATH
from topology.graph import topology
from topology.blast_radius import calculate_blast_radius
from twin.simulator import twin
from cortex.guard import guard
from cortex.policies import ACTIVE_POLICIES
from cortex.ledger import ledger
from cortex.gateway import execution_gateway
from models.proposals import ActionProposal
from chaos.engine import chaos_engine
from control_plane.pipeline import control_plane
from persistence.database import db_manager
from forecasting.forecaster import forecaster
from forecasting.anomalies import anomaly_detector
from optimization.optimizer import optimizer
from verification.verifier import verifier
from orchestrator.agent import IncidentAgent
from evaluation.harness import EvaluationHarness

app = FastAPI(
    title="CORTEX Cloud Autopilot API",
    version="2.0.0",
    description="Predictive, Policy-Governed Autonomous Cloud Control Plane"
)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------
class RetrieveRequest(BaseModel):
    query: str
    k: Optional[int] = 5

class ActionRequest(BaseModel):
    action_type: str
    params: Dict[str, Any]
    incident_id: Optional[str] = "INC-MANUAL"
    actor: Optional[str] = "operator"

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
    horizon: Optional[int] = 30
    history: Optional[List[float]] = None

class ApprovalResolveRequest(BaseModel):
    approval_id: str
    approved: bool
    approver: Optional[str] = "sre-lead"

class AutonomyRequest(BaseModel):
    level: int

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

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "system": "CORTEX Cloud Autopilot",
        "autonomy_level": guard.autonomy_level,
        "kill_switch_engaged": guard.kill_switch_engaged,
        "active_incidents": 2,
        "system_health_pct": 99.96,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


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
    prediction = forecaster.predict_workload(horizon_minutes=horizon)
    return {"history": history, "prediction": prediction}

@app.post("/api/forecasting/predict")
def api_post_forecast(req: ForecastPredictRequest):
    history = req.history or forecaster.generate_live_telemetry_series(window_points=30)
    horizon = req.horizon or 30
    prediction = forecaster.predict_workload(horizon_minutes=horizon)
    return {"service": req.service, "history": history, "prediction": prediction}

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
    return {"pending_approvals": list(guard.pending_approvals.values())}

@app.post("/api/cortex/approvals/resolve")
def api_resolve_approval(req: ApprovalResolveRequest):
    res = guard.resolve_approval(req.approval_id, req.approved, req.approver)
    exec_res = None
    if req.approved:
        execution_gateway.approve_action(req.approval_id, req.approver)
        token = execution_gateway.approved_tokens.get(req.approval_id)
        if token:
            proposal = ActionProposal(
                proposal_id=token.proposal_id,
                incident_id=token.incident_id,
                action_type=token.action_type,
                target=token.target,
                params=token.params,
                risk_score=token.risk_score,
                reason=token.reason,
                generated_by="operator-approval"
            )
            exec_res = execution_gateway.evaluate_and_execute(proposal, approval_id=req.approval_id)
            res["execution_result"] = exec_res.model_dump(mode="json")
    else:
        execution_gateway.reject_action(req.approval_id, req.approver)
    return res

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
@app.post("/api/rag/retrieve")
def api_retrieve(req: RetrieveRequest):
    try:
        results = retrieve(req.query, k=req.k)
        return {"query": req.query, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/action")
def api_action(req: ActionRequest):
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
        reason=f"Invocation by {req.actor}",
        generated_by=req.actor or "operator"
    )

    exec_result = execution_gateway.evaluate_and_execute(proposal)

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
        "status": "success",
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
    return {"status": "injected", "fault": req.fault_type, "target": target, "details": res}

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
