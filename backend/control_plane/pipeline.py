"""
CORTEX Cloud Autopilot — Master Control Plane Loop
Executes the full closed-loop autonomous cycle:
Observe -> Understand -> Predict -> Simulate -> Optimize -> Authorize -> Act -> Verify -> Learn
Strict Invariant: All mutations execute strictly via CortexExecutionGateway.
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from backend.models.proposals import ActionProposal
    from backend.observability.metrics_collector import metrics_collector
    from backend.rag.retrieve import retrieve
    from backend.orchestrator.agent import IncidentAgent
    from backend.forecasting.forecaster import forecaster
    from backend.twin.simulator import twin
    from backend.topology.blast_radius import calculate_blast_radius
    from backend.optimization.optimizer import optimizer
    from backend.cortex.guard import guard
    from backend.cortex.gateway import execution_gateway
    from backend.verification.verifier import verifier
    from backend.persistence.database import db_manager
    from backend.tools.event_bus import emit_event, get_events, clear_events
    from backend.cortex.ledger import ledger
except ImportError:
    from models.proposals import ActionProposal
    from observability.metrics_collector import metrics_collector
    from rag.retrieve import retrieve
    from orchestrator.agent import IncidentAgent
    from forecasting.forecaster import forecaster
    from twin.simulator import twin
    from topology.blast_radius import calculate_blast_radius
    from optimization.optimizer import optimizer
    from cortex.guard import guard
    from cortex.gateway import execution_gateway
    from verification.verifier import verifier
    from persistence.database import db_manager
    from tools.event_bus import emit_event, get_events, clear_events
    from cortex.ledger import ledger


class ControlPlanePipeline:
    """
    Principal SRE control loop coordinator.
    Directs the 9 stages of autonomous cloud operations.
    """

    def __init__(self):
        self.agent = IncidentAgent()

    def run_control_loop(
        self,
        service: str = "payment-service",
        severity: str = "P1",
        symptom: str = "Elevated p95 response latency and HTTP 500 error burst",
        simulate_dangerous: bool = False,
        approval_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes one complete pass of the CORTEX closed-loop control plane.
        """
        start_time = time.time()
        incident_id = f"INC-{int(time.time() * 1000) % 1000000}"
        clear_events()

        # =========================================================================
        # 1. OBSERVE: Live Telemetry Collection & Persistence
        # =========================================================================
        obs_telemetry = metrics_collector.collect(service)
        db_manager.record_incident(
            incident_id=incident_id,
            service=service,
            severity=severity,
            title=f"Autonomous response to {service} degradation",
            root_cause=None,
            raw_telemetry=obs_telemetry.to_dict()
        )

        emit_event({
            "type": "incident_detected",
            "payload": {
                "incident_id": incident_id,
                "service": service,
                "severity": severity,
                "symptom": symptom,
                "telemetry": obs_telemetry.to_dict()
            }
        })

        # =========================================================================
        # 2. UNDERSTAND: RAG Retrieval + Agent Hypothesis & Self-Critique
        # =========================================================================
        emit_event({"type": "diagnosis_started", "payload": {"incident_id": incident_id, "service": service}})
        try:
            rag_docs = retrieve(symptom, k=3)
        except Exception:
            rag_docs = []

        agent_record = self.agent.handle_incident({
            "id": incident_id,
            "service": service,
            "title": f"Degradation on {service}",
            "description": symptom
        })

        proposed_action = agent_record["action"]["type"]
        action_params = dict(agent_record["action"]["params"])

        if simulate_dangerous or "database" in symptom.lower():
            proposed_action = "restart_database"
            action_params = {"database": "postgres"}

        # Normalize target service
        target_resource = action_params.get("service") or service

        # =========================================================================
        # 3. PREDICT: Multi-Horizon XGBoost Workload & Capacity Forecast
        # =========================================================================
        forecast_result = forecaster.predict_workload(horizon_minutes=15)
        emit_event({
            "type": "prediction_generated",
            "payload": {
                "incident_id": incident_id,
                "forecast_horizons": forecast_result.get("horizons"),
                "recommended_replicas": forecast_result.get("recommended_replicas"),
                "action_window_sec": forecast_result.get("action_window_sec")
            }
        })

        # =========================================================================
        # 4. SIMULATE: Digital Twin Counterfactual & Blast Radius
        # =========================================================================
        blast_info = calculate_blast_radius(proposed_action, action_params)
        twin_sim = twin.simulate_action(proposed_action, action_params)

        emit_event({
            "type": "simulation_completed",
            "payload": {
                "incident_id": incident_id,
                "action": proposed_action,
                "blast_score": blast_info.get("score"),
                "risk_level": blast_info.get("risk_level"),
                "twin_predicted_p95": twin_sim.get("predicted_p95_ms"),
                "twin_confidence": twin_sim.get("confidence")
            }
        })

        # =========================================================================
        # 5. OPTIMIZE: Multi-Objective Trade-Off (Cost vs Latency vs Risk)
        # =========================================================================
        opt_res = optimizer.optimize(
            mode="BALANCED",
            current_replicas=obs_telemetry.active_replicas or 6,
            forecast_rps=forecast_result.get("horizons", {}).get("15m", 350.0)
        )

        # =========================================================================
        # 6. AUTHORIZE: CORTEX Guard Governance Policy Evaluation
        # =========================================================================
        guard_eval = guard.evaluate_action(
            action_type=proposed_action,
            params=action_params,
            incident_id=incident_id,
            actor="cortex-autopilot"
        )
        guard_decision = guard_eval.get("decision", "BLOCK")

        # =========================================================================
        # 7. ACT: Structured Proposal Routed STRICTLY via CortexExecutionGateway
        # =========================================================================
        proposal = ActionProposal(
            incident_id=incident_id,
            action_type=proposed_action,
            target=target_resource,
            params=action_params,
            risk_score=guard_eval.get("risk_score", 50),
            reason=agent_record.get("hypothesis", symptom),
            generated_by="cortex-control-plane",
            dry_run=False
        )

        exec_result = execution_gateway.evaluate_and_execute(
            proposal=proposal,
            approval_id=approval_id
        )

        action_executed = exec_result.status in ("SUCCESS", "ROLLED_BACK")
        action_blocked = exec_result.status == "BLOCKED"

        if action_blocked:
            reason = exec_result.output.get("reason", "Blocked by safety guard")
            emit_event({
                "type": "action_blocked" if guard_decision == "BLOCK" else "action_gated",
                "payload": {
                    "incident_id": incident_id,
                    "action": proposed_action,
                    "status": exec_result.status,
                    "reason": reason,
                    "output": exec_result.output
                }
            })

        # =========================================================================
        # 8. VERIFY: Closed-Loop Verification (Executed inline by Gateway)
        # =========================================================================
        verification_data = None
        if action_executed:
            post_output = exec_result.output
            verification_data = {
                "outcome": post_output.get("outcome", "UNKNOWN"),
                "pre_metrics": post_output.get("pre_metrics"),
                "post_metrics": post_output.get("post_metrics"),
                "p95_delta_ms": post_output.get("p95_delta_ms"),
                "rollback": post_output.get("rollback")
            }

            if post_output.get("outcome") == "RECOVERED":
                emit_event({
                    "type": "incident_resolved",
                    "payload": {
                        "incident_id": incident_id,
                        "service": service,
                        "status": "Healthy (SLO restored)",
                        "verification": verification_data
                    }
                })

        # =========================================================================
        # 9. LEARN: Memory Persistence & Ledger Auditing
        # =========================================================================
        if exec_result.status == "SUCCESS":
            db_manager.resolve_incident(incident_id)

        ledger.record_event(
            event_type="control_loop_pass_completed",
            actor="cortex-control-plane",
            payload={
                "incident_id": incident_id,
                "service": service,
                "status": exec_result.status,
                "duration_sec": round(time.time() - start_time, 2)
            },
            correlation_id=incident_id
        )

        total_duration = round(time.time() - start_time, 3)

        return {
            "status": "success",
            "incident_id": incident_id,
            "service": service,
            "total_duration_sec": total_duration,
            "stages": {
                "observe": {
                    "telemetry": obs_telemetry.to_dict(),
                    "freshness": obs_telemetry.freshness
                },
                "understand": {
                    "hypothesis": agent_record.get("hypothesis"),
                    "critique": agent_record.get("critique"),
                    "confidence": agent_record.get("confidence"),
                    "retrieved_context_count": len(rag_docs)
                },
                "predict": {
                    "horizons": forecast_result.get("horizons"),
                    "adaptive_reserve_pct": forecast_result.get("adaptive_reserve_pct"),
                    "recommended_replicas": forecast_result.get("recommended_replicas"),
                    "eval_metrics": forecast_result.get("eval_metrics")
                },
                "simulate": {
                    "blast_radius": blast_info,
                    "twin": twin_sim
                },
                "optimize": opt_res,
                "authorize": {
                    "decision": guard_decision,
                    "risk_score": guard_eval.get("risk_score"),
                    "reasons": guard_eval.get("reasons")
                },
                "act": {
                    "status": exec_result.status,
                    "operation_id": exec_result.operation_id,
                    "execution_time_ms": exec_result.execution_time_ms,
                    "action_type": exec_result.action_type,
                    "target": exec_result.target
                },
                "verify": verification_data,
                "learn": {
                    "incident_resolved": exec_result.status == "SUCCESS",
                    "ledger_verified": ledger.verify_integrity()["valid"]
                }
            },
            "action_result": exec_result.model_dump(mode="json"),
            "events": get_events()
        }


control_plane = ControlPlanePipeline()
