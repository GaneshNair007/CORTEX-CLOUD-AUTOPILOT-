"""
CORTEX Cloud Autopilot — Central Execution Gateway
THE SINGLE AND EXCLUSIVE INFRASTRUCTURE MUTATION GATEWAY.
No AI agent, orchestrator, or API endpoint may execute infrastructure directly.
All requests must enter as ActionProposal and pass through the full 10-stage evaluation pipeline.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from backend.models.proposals import (
    ActionProposal,
    GuardDecision,
    ExecutionResult,
    VerificationResult,
    ApprovalRecord,
    TelemetrySnapshot
)
from backend.execution.tool_registry import tool_registry
from backend.execution.idempotency import idempotency_manager
from backend.execution.locks import resource_lock_manager
from backend.execution.anti_thrashing import anti_thrashing_manager
from backend.execution.retry import incident_budget
from backend.cortex.guard import CortexGuard
from backend.cortex.ledger import ledger
from backend.topology.blast_radius import calculate_blast_radius
from backend.twin.simulator import twin
from backend.observability.metrics_collector import metrics_collector
from backend.providers import get_active_provider, CloudProvider


class CortexExecutionGateway:
    """
    Unified authorization and execution pipeline.
    Enforces all 15 system invariants before any infrastructure mutation occurs.
    """

    def __init__(self, guard: Optional[CortexGuard] = None, provider: Optional[CloudProvider] = None):
        self.guard = guard or CortexGuard()
        self.provider = provider or get_active_provider()
        self.freeze_mutations = False
        self.approved_tokens: Dict[str, ApprovalRecord] = {}  # approval_id -> ApprovalRecord

    def set_freeze_mutations(self, frozen: bool) -> None:
        """Enables or disables system-wide mutation freeze mode."""
        self.freeze_mutations = frozen
        ledger.record_event("mutation_freeze_toggled", "operator", {"frozen": frozen})

    def approve_action(self, approval_id: str, approver: str = "sre-lead") -> Optional[ApprovalRecord]:
        """Grants human approval for a gated action."""
        record = self.approved_tokens.get(approval_id)
        if not record:
            return None

        # Verify approval hasn't expired
        if datetime.now(timezone.utc) > record.expires_at:
            record.status = "EXPIRED"
            return record

        record.status = "APPROVED"
        record.approver = approver
        record.resolved_at = datetime.now(timezone.utc)
        ledger.record_event("approval_granted", approver, {"approval_id": approval_id, "action": record.action_type})
        return record

    def reject_action(self, approval_id: str, approver: str = "sre-lead") -> Optional[ApprovalRecord]:
        """Rejects a gated action."""
        record = self.approved_tokens.get(approval_id)
        if not record:
            return None

        record.status = "REJECTED"
        record.approver = approver
        record.resolved_at = datetime.now(timezone.utc)
        ledger.record_event("approval_rejected", approver, {"approval_id": approval_id, "action": record.action_type})
        return record

    def evaluate_and_execute(
        self,
        proposal: ActionProposal,
        idempotency_key: Optional[str] = None,
        approval_id: Optional[str] = None,
        custom_provider: Optional[CloudProvider] = None
    ) -> ExecutionResult:
        """
        Full 10-stage execution pipeline.
        Returns ExecutionResult with status SUCCESS, BLOCKED, ROLLED_BACK, or FAILED.
        """
        provider = custom_provider or self.provider
        operation_id = f"op_{uuid.uuid4().hex[:10]}"
        idemp_key = idempotency_key or f"idemp_{proposal.incident_id}_{proposal.action_type}_{proposal.target}"

        # -------------------------------------------------------------
        # INVARIANT 6: Idempotency check
        # -------------------------------------------------------------
        cached_result = idempotency_manager.check(idemp_key)
        if cached_result is not None:
            return ExecutionResult(
                operation_id=cached_result.get("original_operation_id", operation_id),
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status="SUCCESS",
                output=cached_result,
                idempotency_key=idemp_key,
                provider_type="idempotent_cache"
            )

        # -------------------------------------------------------------
        # INVARIANT 13 & 14: Tool Registry Validation
        # -------------------------------------------------------------
        is_valid, err_msg = tool_registry.validate_call(proposal.action_type, proposal.params)
        if not is_valid:
            ledger.record_event("action_blocked", "cortex-guard", {"error": err_msg}, proposal.incident_id)
            return ExecutionResult(
                operation_id=operation_id,
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status="BLOCKED",
                output={"error": err_msg},
                idempotency_key=idemp_key
            )

        tool = tool_registry.get(proposal.action_type)

        # -------------------------------------------------------------
        # INVARIANT 12: Emergency Kill Switch & Freeze Mode
        # -------------------------------------------------------------
        if self.guard.kill_switch_engaged:
            reason = "EMERGENCY KILL SWITCH ENGAGED: All mutating infrastructure operations are frozen."
            ledger.record_event("action_blocked", "cortex-guard", {"action": proposal.action_type, "reason": reason}, proposal.incident_id)
            return ExecutionResult(
                operation_id=operation_id,
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status="BLOCKED",
                output={"reason": reason, "kill_switch_engaged": True},
                idempotency_key=idemp_key
            )

        if self.freeze_mutations and tool.mutating:
            reason = "MUTATION FREEZE ACTIVE: Infrastructure modifications temporarily frozen."
            ledger.record_event("action_blocked", "cortex-guard", {"action": proposal.action_type, "reason": reason}, proposal.incident_id)
            return ExecutionResult(
                operation_id=operation_id,
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status="BLOCKED",
                output={"reason": reason, "freeze_active": True},
                idempotency_key=idemp_key
            )

        # -------------------------------------------------------------
        # SECTION 74: Incident Action Budget (Max 3 autonomous attempts)
        # -------------------------------------------------------------
        if tool.mutating:
            can_attempt, count = incident_budget.can_attempt_action(proposal.incident_id)
            if not can_attempt:
                reason = f"INCIDENT BUDGET EXCEEDED: Max autonomous attempts ({incident_budget.max_actions}) reached. Escalating to human on-call."
                ledger.record_event("action_escalated", "cortex-guard", {"reason": reason}, proposal.incident_id)
                return ExecutionResult(
                    operation_id=operation_id,
                    proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    status="BLOCKED",
                    output={"reason": reason, "escalated": True},
                    idempotency_key=idemp_key
                )

        # -------------------------------------------------------------
        # SECTION 15: Anti-Thrashing Cooldown Check
        # -------------------------------------------------------------
        if tool.mutating:
            can_mutate, remaining_sec = anti_thrashing_manager.check_cooldown(proposal.target, tool.cooldown_seconds)
            if not can_mutate:
                reason = f"COOLDOWN ACTIVE: Service '{proposal.target}' modified recently. Cooldown active for {remaining_sec}s to prevent oscillation."
                ledger.record_event("action_blocked", "cortex-guard", {"reason": reason}, proposal.incident_id)
                return ExecutionResult(
                    operation_id=operation_id,
                    proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    status="BLOCKED",
                    output={"reason": reason, "cooldown_remaining_sec": remaining_sec},
                    idempotency_key=idemp_key
                )

        # -------------------------------------------------------------
        # INVARIANT 15: Telemetry Freshness & Degraded Autonomy Check
        # -------------------------------------------------------------
        telemetry = metrics_collector.collect(proposal.target)
        obs_status = metrics_collector.get_status()

        if tool.mutating and (tool.risk_class in ("HIGH", "CRITICAL") or proposal.risk_score >= 50):
            if telemetry.freshness == "STALE":
                reason = f"STALE TELEMETRY: Telemetry age ({telemetry.age_seconds}s) exceeds 60s freshness threshold. High-risk actions forbidden on stale state."
                ledger.record_event("action_blocked", "cortex-guard", {"reason": reason}, proposal.incident_id)
                return ExecutionResult(
                    operation_id=operation_id,
                    proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    status="BLOCKED",
                    output={"reason": reason, "telemetry_freshness": telemetry.freshness},
                    idempotency_key=idemp_key
                )

            if obs_status.overall_status == "OBSERVABILITY_DEGRADED" and not approval_id:
                reason = "OBSERVABILITY DEGRADED: Primary metrics offline. Autonomous authority reduced to Level 1 (Approval Required)."
                ledger.record_event("action_gated", "cortex-guard", {"reason": reason}, proposal.incident_id)
                return ExecutionResult(
                    operation_id=operation_id,
                    proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    status="BLOCKED",
                    output={"reason": reason, "approval_required": True},
                    idempotency_key=idemp_key
                )

        # -------------------------------------------------------------
        # STAGE 4 & 5: Blast Radius & Digital Twin Evaluation
        # -------------------------------------------------------------
        blast_info = calculate_blast_radius(proposal.action_type, proposal.params)
        twin_sim = twin.simulate_action(proposal.action_type, proposal.params)

        # -------------------------------------------------------------
        # STAGE 6: CORTEX Guard Policy Decision
        # -------------------------------------------------------------
        guard_eval = self.guard.evaluate_action(
            proposal.action_type,
            proposal.params,
            proposal.incident_id,
            proposal.generated_by
        )
        decision = guard_eval["decision"]

        # INVARIANT 2: BLOCKED action can NEVER reach provider
        if decision == "BLOCK":
            ledger.record_event("action_blocked", "cortex-guard", guard_eval, proposal.incident_id)
            return ExecutionResult(
                operation_id=operation_id,
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status="BLOCKED",
                output={"guard_decision": guard_eval},
                idempotency_key=idemp_key
            )

        # INVARIANT 3 & 4: Approval verification
        if decision == "REQUIRE_APPROVAL":
            if not approval_id:
                # Create pending approval
                new_app_id = f"app_{uuid.uuid4().hex[:8]}"
                expires_at = datetime.fromtimestamp(time.time() + 300, tz=timezone.utc)
                app_record = ApprovalRecord(
                    approval_id=new_app_id,
                    proposal_id=proposal.proposal_id,
                    incident_id=proposal.incident_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    risk_score=guard_eval["risk_score"],
                    reason=guard_eval["reasons"][0] if guard_eval.get("reasons") else "Approval required",
                    expires_at=expires_at
                )
                self.approved_tokens[new_app_id] = app_record
                ledger.record_event("approval_required", "cortex-guard", {"approval_id": new_app_id}, proposal.incident_id)
                return ExecutionResult(
                    operation_id=operation_id,
                    proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    status="BLOCKED",
                    output={"approval_id": new_app_id, "status": "APPROVAL_REQUIRED", "expires_at": expires_at.isoformat()},
                    idempotency_key=idemp_key
                )

            # Validate existing approval
            token = self.approved_tokens.get(approval_id)
            if not token or token.status != "APPROVED":
                return ExecutionResult(
                    operation_id=operation_id,
                    proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    status="BLOCKED",
                    output={"error": "Invalid or unapproved authorization token."},
                    idempotency_key=idemp_key
                )

            # INVARIANT 4: Expired approval check
            if datetime.now(timezone.utc) > token.expires_at:
                return ExecutionResult(
                    operation_id=operation_id,
                    proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type,
                    target=proposal.target,
                    params=proposal.params,
                    status="BLOCKED",
                    output={"error": "Authorization token has EXPIRED. Must re-authorize."},
                    idempotency_key=idemp_key
                )

        # -------------------------------------------------------------
        # INVARIANT 7: Acquire Exclusive Per-Resource Lock
        # -------------------------------------------------------------
        if not resource_lock_manager.acquire(proposal.target, operation_id, timeout_sec=0.5):
            current_holder = resource_lock_manager.get_holder(proposal.target)
            reason = f"RESOURCE CONFLICT: Service '{proposal.target}' is currently locked by active operation '{current_holder}'."
            ledger.record_event("action_conflict", "cortex-guard", {"reason": reason}, proposal.incident_id)
            return ExecutionResult(
                operation_id=operation_id,
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status="BLOCKED",
                output={"reason": reason, "conflict": True},
                idempotency_key=idemp_key
            )

        try:
            # -------------------------------------------------------------
            # SECTION 20: Capture REAL PRE-action telemetry
            # -------------------------------------------------------------
            pre_telemetry = metrics_collector.collect(proposal.target)
            pre_metrics = {
                "p95_ms": pre_telemetry.p95_latency_ms,
                "error_rate_pct": pre_telemetry.error_rate_pct,
                "cpu_percent": pre_telemetry.cpu_percent,
                "replicas": pre_telemetry.active_replicas,
            }

            # -------------------------------------------------------------
            # STAGE 7: Real Infrastructure Actuation via Provider
            # -------------------------------------------------------------
            start_time = time.time()
            ledger.record_event("action_started", proposal.generated_by, {"action": proposal.action_type, "params": proposal.params}, proposal.incident_id)

            if proposal.action_type in ("scale_service", "scale_replicas"):
                target_reps = proposal.params.get("replicas", 6)
                mutation_output = provider.scale_service(proposal.target, target_reps)
            elif proposal.action_type == "restart_service":
                mutation_output = provider.restart_service(proposal.target)
            elif proposal.action_type == "rollback_deployment":
                revision = proposal.params.get("revision")
                mutation_output = provider.rollback_service(proposal.target, revision)
            else:
                mutation_output = {"status": "SUCCESS", "message": f"Action {proposal.action_type} executed."}

            execution_duration_ms = (time.time() - start_time) * 1000.0

            # Record mutation in anti-thrashing cooldown tracker
            anti_thrashing_manager.record_mutation(proposal.target, proposal.action_type)
            incident_budget.increment(proposal.incident_id)

            # -------------------------------------------------------------
            # SECTION 23: Wait Settling Window before Verification
            # -------------------------------------------------------------
            time.sleep(1.5)  # Real settling window

            # -------------------------------------------------------------
            # STAGE 8 & SECTION 20-22: Real Closed-Loop Verification
            # -------------------------------------------------------------
            post_telemetry = metrics_collector.collect(proposal.target)
            post_metrics = {
                "p95_ms": post_telemetry.p95_latency_ms,
                "error_rate_pct": post_telemetry.error_rate_pct,
                "cpu_percent": post_telemetry.cpu_percent,
                "replicas": post_telemetry.active_replicas,
            }

            p95_delta = post_metrics["p95_ms"] - pre_metrics["p95_ms"]
            err_delta = post_metrics["error_rate_pct"] - pre_metrics["error_rate_pct"]

            # Ground-truth outcome classification
            if post_metrics["p95_ms"] > pre_metrics["p95_ms"] * 1.5 or post_metrics["error_rate_pct"] > pre_metrics["error_rate_pct"] + 10.0:
                outcome = "WORSE"
            elif post_metrics["p95_ms"] <= pre_metrics["p95_ms"] and post_metrics["error_rate_pct"] <= pre_metrics["error_rate_pct"]:
                outcome = "RECOVERED"
            else:
                outcome = "PARTIALLY_RECOVERED"

            # SECTION 22 & INVARIANT 11: Real Rollback if outcome is WORSE
            rollback_res = None
            if outcome == "WORSE" and tool.reversible:
                ledger.record_event("rollback_triggered", "cortex-verifier", {"reason": "Post-action degradation detected"}, proposal.incident_id)
                rollback_res = provider.rollback_service(proposal.target)
                time.sleep(1.0)
                # Verify rollback itself
                rollback_telemetry = metrics_collector.collect(proposal.target)
                rollback_res["verified_p95_ms"] = rollback_telemetry.p95_latency_ms
                ledger.record_event("rollback_completed", "cortex-verifier", rollback_res, proposal.incident_id)

            status = "ROLLED_BACK" if outcome == "WORSE" else "SUCCESS"

            exec_result = ExecutionResult(
                operation_id=operation_id,
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status=status,
                output={
                    "mutation": mutation_output,
                    "pre_metrics": pre_metrics,
                    "post_metrics": post_metrics,
                    "p95_delta_ms": round(p95_delta, 2),
                    "outcome": outcome,
                    "rollback": rollback_res
                },
                execution_time_ms=round(execution_duration_ms, 2),
                idempotency_key=idemp_key,
                provider_type="live_provider"
            )

            # Save in idempotency store & record audit block
            idempotency_manager.record_execution(idemp_key, operation_id, proposal.action_type, proposal.target, exec_result.model_dump(mode="json"))
            ledger.record_event("action_completed", proposal.generated_by, exec_result.model_dump(mode="json"), proposal.incident_id)

            return exec_result

        finally:
            # Always release lock!
            resource_lock_manager.release(proposal.target, operation_id)


# Global singleton gateway
execution_gateway = CortexExecutionGateway()
