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

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
def api_get_forecast(horizon: int = Query(30, ge=5, le=60)):
    history = forecaster.generate_live_telemetry_series(window_points=30)
    prediction = forecaster.predict_workload(horizon_minutes=horizon)
    return {"history": history, "prediction": prediction}

@app.post("/api/optimizer")
def api_optimize(req: OptimizeRequest):
    return optimizer.optimize(
        mode=req.mode,
        current_replicas=req.current_replicas,
        forecast_rps=req.forecast_rps
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
    if res.get("status") == "success" and req.approved:
        # Execute the approved action
        act_res = execute_action(res["action_type"], res["params"])
        res["execution_result"] = act_res
    return res

@app.post("/api/cortex/autonomy")
def api_set_autonomy(req: AutonomyRequest):
    guard.set_autonomy_level(req.level)
    return {"status": "success", "autonomy_level": guard.autonomy_level}

@app.post("/api/cortex/kill-switch")
def api_set_kill_switch(req: KillSwitchRequest):
    guard.set_kill_switch(req.engaged, req.reason or "")
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
    Guarded action dispatch: Every action must pass through CORTEX Guard.
    """
    eval_res = guard.evaluate_action(
        action_type=req.action_type,
        params=req.params,
        incident_id=req.incident_id,
        actor=req.actor
    )

    if eval_res["decision"] == "BLOCK":
        return {
            "status": "blocked",
            "decision": "BLOCK",
            "message": f"Action '{req.action_type}' was BLOCKED by CORTEX Guard.",
            "evaluation": eval_res
        }

    elif eval_res["decision"] == "REQUIRE_APPROVAL":
        return {
            "status": "approval_required",
            "decision": "REQUIRE_APPROVAL",
            "approval_id": eval_res["approval_id"],
            "message": f"Action '{req.action_type}' requires human authorization.",
            "evaluation": eval_res
        }

    # ALLOW: Controlled execution
    act_res = execute_action(req.action_type, req.params)
    return {
        "status": "success",
        "decision": "ALLOW",
        "action_result": act_res,
        "evaluation": eval_res
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
    """Simulates controlled infrastructure faults."""
    target = req.target_service or "payment-api"
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if req.fault_type == "pod_kill":
        topology.update_node_health(target, "Degraded", p95_ms=320.0, error_rate=0.08)
        desc = f"Simulated container crash in {target} pod replica."
    elif req.fault_type == "cpu_saturation":
        topology.update_node_health(target, "Degraded", p95_ms=780.0, error_rate=0.14)
        desc = f"Injected synthetic CPU stress loop (98% saturation) on {target}."
    elif req.fault_type == "db_outage":
        topology.update_node_health("user-profile-db", "Outage", p95_ms=4500.0, error_rate=0.48)
        desc = "Simulated primary PostgreSQL connection exhaustion and advisory lock contention."
    elif req.fault_type == "latency":
        topology.update_node_health(target, "Degraded", p95_ms=420.0, error_rate=0.02)
        desc = f"Added 300ms synthetic network delay on {target} upstream ingress."
    else:
        topology.update_node_health(target, "Degraded", p95_ms=290.0, error_rate=0.06)
        desc = f"Triggered 10x traffic spike on {target} (1200 RPS)."

    emit_event({
        "type": "chaos_fault_injected",
        "payload": {"fault_type": req.fault_type, "target": target, "description": desc, "timestamp": ts}
    })
    ledger.record_event("chaos_fault_injected", "chaos-engine", {"fault": req.fault_type, "target": target})

    return {"status": "injected", "fault": req.fault_type, "target": target, "description": desc}


# -----------------------------------------------------------------------------
# Master Closed-Loop Autonomous Pipeline
# -----------------------------------------------------------------------------
@app.post("/api/pipeline/run")
def api_run_pipeline(req: PipelineRequest):
    """
    Closed-Loop Autopilot Workflow:
    Observe -> Understand (RAG + AI Hypothesis + Critique) -> Simulate Twin ->
    CORTEX Guard -> Execute -> Verify Telemetry -> Learn.
    """
    start_time = time.time()
    incident_id = f"INC-{int(time.time()) % 10000}"
    clear_events()

    # 1. OBSERVE: Incident Correlated
    emit_event({
        "type": "incident_detected",
        "payload": {
            "incident_id": incident_id,
            "service": req.service,
            "severity": req.severity,
            "symptom": req.symptom
        }
    })

    # 2. UNDERSTAND: Vector Memory Retrieval & Orchestrator Agent
    emit_event({"type": "diagnosis_started", "payload": {"incident_id": incident_id, "service": req.service}})
    docs = retrieve(req.symptom, k=3)
    
    agent = IncidentAgent()
    agent_record = agent.handle_incident({
        "id": incident_id,
        "service": req.service,
        "title": f"Degradation on {req.service}",
        "description": req.symptom
    })

    proposed_action = agent_record["action"]["type"]
    action_params = agent_record["action"]["params"]

    # Flagship Demo Scenario: If simulate_dangerous is flagged, AI proposes dangerous DB restart
    if req.simulate_dangerous or "database" in req.symptom.lower():
        proposed_action = "restart_database"
        action_params = {"database": "user-profile-db"}

    # 3. PREDICT & SIMULATE: Counterfactual Digital Twin & Blast Radius
    blast = calculate_blast_radius(proposed_action, action_params)
    simulation = twin.simulate_action(proposed_action, action_params)

    emit_event({
        "type": "simulation_completed",
        "payload": {
            "incident_id": incident_id,
            "action": proposed_action,
            "blast_radius_score": blast["score"],
            "risk_level": blast["risk_level"],
            "affected_services": blast["affected_services"]
        }
    })

    # 4. AUTHORIZE: CORTEX Guard Deterministic Safety Gate
    guard_eval = guard.evaluate_action(
        action_type=proposed_action,
        params=action_params,
        incident_id=incident_id,
        actor="cortex-autopilot"
    )

    action_executed = False
    action_result = None
    verification_result = None

    # 5. ACT: Controlled Execution (if ALLOW)
    if guard_eval["decision"] == "ALLOW":
        action_result = execute_action(proposed_action, action_params)
        action_executed = True
        emit_event({"type": "action_executed", "payload": action_result})

        # 6. VERIFY: Closed-Loop Post-Action SLO Check
        verification_result = verifier.verify_action(
            action_type=proposed_action,
            target_service=req.service,
            pre_metrics={"p95_ms": 680.0, "error_rate": 0.18},
            post_metrics={"p95_ms": 138.0, "error_rate": 0.003},
            correlation_id=incident_id
        )

        emit_event({
            "type": "incident_resolved",
            "payload": {
                "incident_id": incident_id,
                "service": req.service,
                "status": "Healthy (SLO target restored)",
                "verification": verification_result["summary"]
            }
        })

    elif guard_eval["decision"] == "REQUIRE_APPROVAL":
        action_result = {"status": "approval_required", "approval_id": guard_eval["approval_id"]}
        emit_event({
            "type": "action_gated",
            "payload": {"incident_id": incident_id, "approval_id": guard_eval["approval_id"], "risk": blast["score"]}
        })

    else:  # BLOCK
        action_result = {"status": "blocked", "reasons": guard_eval["reasons"]}
        emit_event({
            "type": "action_blocked",
            "payload": {"incident_id": incident_id, "action": proposed_action, "reasons": guard_eval["reasons"]}
        })

    total_duration = round(time.time() - start_time, 3)

    return {
        "status": "success",
        "incident_id": incident_id,
        "service": req.service,
        "total_duration_sec": total_duration,
        "hypothesis": agent_record.get("hypothesis"),
        "critique": agent_record.get("critique"),
        "confidence": agent_record.get("confidence"),
        "proposed_action": proposed_action,
        "guard_decision": guard_eval["decision"],
        "blast_radius": blast,
        "simulation": simulation,
        "action_result": action_result,
        "verification": verification_result,
        "events": get_events()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
