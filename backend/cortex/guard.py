"""
CORTEX Cloud Autopilot — CORTEX Guard Engine
The central deterministic governance and safety gate between AI proposals and cloud execution.
Evaluates capability envelopes, blast radius, policy rules, and human-in-the-loop approvals.
"""

from typing import Dict, Any, List, Optional
import time
import uuid
from cortex.policies import ACTIVE_POLICIES
from cortex.ledger import ledger
from topology.blast_radius import calculate_blast_radius
from twin.simulator import twin


class CortexGuard:
    def __init__(self):
        # Autonomy Level:
        # 0 = Observe (No actions allowed)
        # 1 = Recommend (AI recommends, human executes)
        # 2 = Guarded (Low-risk auto-executes, high-risk requires approval)
        # 3 = Autonomous (Wider action envelope, bounded blast radius)
        self.autonomy_level = 2
        self.kill_switch_engaged = False
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def set_autonomy_level(self, level: int) -> None:
        """Updates the operational autonomy level."""
        if level in [0, 1, 2, 3]:
            self.autonomy_level = level
            ledger.record_event(
                event_type="autonomy_level_changed",
                actor="operator",
                payload={"new_level": level}
            )

    def set_kill_switch(self, engaged: bool, reason: str = "") -> None:
        """Engages or disengages the global emergency kill switch."""
        self.kill_switch_engaged = engaged
        ledger.record_event(
            event_type="kill_switch_toggled",
            actor="operator",
            payload={"engaged": engaged, "reason": reason}
        )

    def get_capability_envelope(self, incident_severity: str = "P1") -> Dict[str, List[str]]:
        """Returns the task-specific allowed, approval_required, and blocked operations."""
        return {
            "allowed": [
                "inspect_metrics",
                "inspect_logs",
                "inspect_topology",
                "create_ticket",
                "notify_team",
                "generate_postmortem",
                "restart_service",
                "restart_pod"
            ],
            "approval_required": [
                "rollback_deployment",
                "scale_deployment"
            ],
            "blocked": [
                "restart_database",
                "delete_resource",
                "truncate_table",
                "drop_index"
            ]
        }

    def evaluate_action(
        self,
        action_type: str,
        params: Dict[str, Any],
        incident_id: str = "INC-000",
        actor: str = "cortex-ai-agent"
    ) -> Dict[str, Any]:
        """
        Evaluates an infrastructure mutation request.
        Returns:
            decision: 'ALLOW' | 'CONSTRAIN' | 'REQUIRE_APPROVAL' | 'BLOCK'
            risk_score: int (0 to 100)
            blast_radius: Dict[str, Any]
            reasons: List[str]
            safer_alternatives: List[str]
            approval_id: Optional[str]
            ttl_seconds: int
        """
        # Invariant 1: Emergency Kill Switch
        if self.kill_switch_engaged:
            decision = "BLOCK"
            reasons = ["EMERGENCY KILL SWITCH ENGAGED: All mutating infrastructure operations are frozen."]
            ledger.record_event("action_blocked", actor, {"action": action_type, "reason": reasons[0]}, incident_id)
            return {
                "decision": decision,
                "risk_score": 100,
                "blast_radius": {"score": 100, "risk_level": "CRITICAL"},
                "reasons": reasons,
                "safer_alternatives": ["Wait for incident commander to disengage kill switch."],
                "approval_id": None,
                "ttl_seconds": 0
            }

        # Invariant 2: Level 0 Autonomy (Observe Only)
        if self.autonomy_level == 0:
            reasons = ["Autonomy Level 0 (OBSERVE): Control plane operates in read-only observation mode."]
            return {
                "decision": "BLOCK",
                "risk_score": 50,
                "blast_radius": {"score": 50, "risk_level": "MODERATE"},
                "reasons": reasons,
                "safer_alternatives": ["Promote autonomy level to Level 1 or Level 2."],
                "approval_id": None,
                "ttl_seconds": 0
            }

        # Step 1: Blast Radius & Digital Twin Simulation
        blast = calculate_blast_radius(action_type, params)
        sim_res = twin.simulate_action(action_type, params)

        # Step 2: Policy Rule Evaluation
        context = {
            "blast_radius_score": blast["score"],
            "failover_ready": blast["failover_ready"],
            "downstream_services": blast["affected_services"]
        }

        reasons = []
        policy_decision = "ALLOW"

        for policy in ACTIVE_POLICIES:
            triggered, dec, reason = policy.evaluate(action_type, params, context)
            if triggered:
                reasons.append(reason)
                if dec == "BLOCK":
                    policy_decision = "BLOCK"
                    break
                elif dec == "REQUIRE_APPROVAL" and policy_decision != "BLOCK":
                    policy_decision = "REQUIRE_APPROVAL"

        # Step 3: Autonomy Level & Capability Envelope Constraints
        envelope = self.get_capability_envelope()
        safer_alternatives = []

        if action_type in envelope["blocked"] or policy_decision == "BLOCK":
            final_decision = "BLOCK"
            if action_type == "restart_database":
                safer_alternatives.append("restart_unhealthy_replica")
                safer_alternatives.append("kill_idle_connections")
                safer_alternatives.append("scale_connection_pool")

        elif self.autonomy_level == 1:
            # Level 1 requires human approval for all mutations
            final_decision = "REQUIRE_APPROVAL"
            reasons.append("Autonomy Level 1 (RECOMMEND): All infrastructure changes require human confirmation.")

        elif policy_decision == "REQUIRE_APPROVAL" or action_type in envelope["approval_required"] or blast["score"] >= 60:
            final_decision = "REQUIRE_APPROVAL"
            if action_type == "rollback_deployment":
                safer_alternatives.append("canary_rollback_1_replica")

        else:
            final_decision = "ALLOW"

        # If approval required, record in pending queue
        approval_id = None
        if final_decision == "REQUIRE_APPROVAL":
            approval_id = f"APP-{str(uuid.uuid4())[:8]}"
            self.pending_approvals[approval_id] = {
                "approval_id": approval_id,
                "incident_id": incident_id,
                "action_type": action_type,
                "params": params,
                "risk_score": blast["score"],
                "created_at": time.time(),
                "ttl_seconds": 120,
                "status": "pending"
            }

        # Step 4: Record Decision in Tamper-Evident Ledger
        ledger.record_event(
            event_type=f"cortex_guard_{final_decision.lower()}",
            actor=actor,
            payload={
                "action_type": action_type,
                "target": blast["directly_affected"],
                "decision": final_decision,
                "blast_radius_score": blast["score"],
                "reasons": reasons
            },
            correlation_id=incident_id
        )

        return {
            "decision": final_decision,
            "risk_score": blast["score"],
            "blast_radius": blast,
            "simulation": sim_res,
            "reasons": reasons if reasons else ["Action evaluated within safe operational limits."],
            "safer_alternatives": safer_alternatives,
            "approval_id": approval_id,
            "ttl_seconds": 120
        }

    def resolve_approval(self, approval_id: str, approved: bool, approver: str = "sre-lead") -> Dict[str, Any]:
        """Resolves a pending human approval decision."""
        if approval_id not in self.pending_approvals:
            return {"status": "error", "message": f"Approval {approval_id} not found or expired"}

        appr = self.pending_approvals[approval_id]
        if time.time() - appr["created_at"] > appr["ttl_seconds"]:
            del self.pending_approvals[approval_id]
            return {"status": "expired", "message": "Approval expired (TTL 120s passed). Re-evaluation required."}

        status = "approved" if approved else "rejected"
        appr["status"] = status
        appr["approver"] = approver

        ledger.record_event(
            event_type=f"approval_{status}",
            actor=approver,
            payload={"approval_id": approval_id, "action_type": appr["action_type"]},
            correlation_id=appr["incident_id"]
        )

        return {
            "status": "success",
            "approval_id": approval_id,
            "outcome": status,
            "action_type": appr["action_type"],
            "params": appr["params"]
        }


# Global singleton cortex guard instance
guard = CortexGuard()
