"""
CORTEX Cloud Autopilot — Central Execution Gateway
THE SINGLE AND EXCLUSIVE INFRASTRUCTURE MUTATION GATEWAY.
No AI agent, orchestrator, or API endpoint may execute infrastructure directly.
All requests must enter as ActionProposal and pass through the full 10-stage evaluation pipeline.
"""

import time
import uuid
import hashlib
import json
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
from backend.cortex.guard import CortexGuard, guard as shared_guard
from backend.verification.outcomes import classify_outcome
from backend.cortex.ledger import ledger
from backend.persistence.authorization import ApprovalStore, binding
from backend.persistence.database import db_manager
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
        self.approved_tokens = ApprovalStore()

    def set_freeze_mutations(self, frozen: bool) -> None:
        """Enables or disables system-wide mutation freeze mode."""
        self.freeze_mutations = frozen
        ledger.record_event("mutation_freeze_toggled", "operator", {"frozen": frozen})

    def approve_action(self, approval_id: str, approver: str = "operator") -> Optional[ApprovalRecord]:
        """Resolve a pending durable token; an expired/rejected/consumed token stays terminal."""
        record = self.approved_tokens.resolve(approval_id, True, approver)
        ledger.record_event("approval_resolved", approver, {"approval_id": approval_id, "status": record.status if record else "NOT_FOUND"})
        return record

    def reject_action(self, approval_id: str, approver: str = "operator") -> Optional[ApprovalRecord]:
        record = self.approved_tokens.resolve(approval_id, False, approver)
        ledger.record_event("approval_resolved", approver, {"approval_id": approval_id, "status": record.status if record else "NOT_FOUND"})
        return record

    @staticmethod
    def resource_version(provider: CloudProvider, target: str) -> str:
        state = provider.get_resource_state(target)
        stable = {key: state[key] for key in ("version", "revision", "replicas", "generation", "status", "ready") if key in state}
        if state.get("state_available") is False or not stable:
            raise ValueError("Resource state unavailable for approval binding")
        return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()

    def evaluate_and_execute(self, proposal: ActionProposal, idempotency_key: Optional[str] = None,
                             approval_id: Optional[str] = None, custom_provider: Optional[CloudProvider] = None) -> ExecutionResult:
        """Persist every attempt and fail closed on provider or authorization errors."""
        proposal = proposal.model_copy(deep=True)
        proposal.params.setdefault("service", proposal.target)
        if proposal.params["service"] != proposal.target:
            return ExecutionResult(operation_id=f"op_{uuid.uuid4().hex}", proposal_id=proposal.proposal_id,
                action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="BLOCKED",
                output={"error": "Target and service parameter must match"}, idempotency_key=idempotency_key or "invalid")
        db_manager.record_operation(proposal.proposal_id, proposal.action_type, proposal.target, parameters=proposal.params)
        try:
            result = self._evaluate_and_execute(proposal, idempotency_key, approval_id, custom_provider)
        except Exception as exc:
            # Provider exceptions can contain URLs/credentials. Only disclose the error class.
            result = ExecutionResult(operation_id=f"op_{uuid.uuid4().hex}", proposal_id=proposal.proposal_id,
                action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="FAILED",
                output={"error": type(exc).__name__, "outcome": "UNKNOWN"}, idempotency_key=idempotency_key or "failed")
        if result.output.get("verification") and result.output["verification"].get("outcome") != "UNKNOWN":
            from backend.retrieval.lifecycle import learn_verified_execution
            try:
                memory = learn_verified_execution(proposal, result)
                if memory:
                    result.output["memory"] = memory
            except Exception as exc:
                # Execution is complete even if indexing/storage needs repair.
                result.output["memory_warning"] = f"Memory write failed ({type(exc).__name__}); operation remains in SQL"
        if not result.output.get("idempotent_replay"):
            idempotency_manager.record_execution(result.idempotency_key, result.operation_id, proposal.action_type, proposal.target, result.model_dump(mode="json"))
        db_manager.update_operation_result(proposal.proposal_id, result.status, result.model_dump(mode="json"), result.output.get("outcome"))
        ledger.record_event("gateway_attempt_completed", proposal.generated_by, result.model_dump(mode="json"), proposal.incident_id)
        return result

    def _evaluate_and_execute(
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
        normalizer = getattr(provider, "normalize_target", None)
        lock_target = normalizer(proposal.target) if callable(normalizer) else proposal.target
        if not isinstance(lock_target, str):
            lock_target = proposal.target
        operation_id = f"op_{uuid.uuid4().hex[:10]}"
        parameter_hash = hashlib.sha256(json.dumps(proposal.params, sort_keys=True).encode()).hexdigest()[:16]
        idemp_key = idempotency_key or f"idemp_{proposal.incident_id}_{proposal.action_type}_{proposal.target}_{parameter_hash}"

        if approval_id:
            existing = self.approved_tokens.get(approval_id)
            if existing and existing.status == "EXPIRED":
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="BLOCKED",
                    output={"error": "Authorization token has EXPIRED"}, idempotency_key=idemp_key)

        # -------------------------------------------------------------
        # INVARIANT 6: Idempotency check
        # -------------------------------------------------------------
        cached_result = idempotency_manager.check(idemp_key)
        if cached_result is not None:
            if (cached_result.get("action_type"), cached_result.get("target"), cached_result.get("params")) != (proposal.action_type, proposal.target, proposal.params):
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="BLOCKED",
                    output={"error": "Idempotency key belongs to different inputs"}, idempotency_key=idemp_key)
            return ExecutionResult(
                operation_id=cached_result.get("original_operation_id", operation_id),
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status=cached_result["status"],
                output={**cached_result.get("output", {}), "idempotent_replay": True},
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
        if proposal.dry_run:
            decision = self.guard.evaluate_action(proposal.action_type, proposal.params, proposal.incident_id, proposal.generated_by)
            return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                                   action_type=proposal.action_type, target=proposal.target, params=proposal.params,
                                   status="BLOCKED" if decision["decision"] == "BLOCK" else "SUCCESS",
                                   output={"dry_run": True, "guard_decision": decision, "outcome": "UNKNOWN"},
                                   idempotency_key=idemp_key, provider_type="dry_run")

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
            can_mutate, remaining_sec = anti_thrashing_manager.check_cooldown(lock_target, tool.cooldown_seconds)
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
        if decision != "BLOCK" and tool.mutating and (obs_status.overall_status == "OBSERVABILITY_DEGRADED" or tool.requires_approval):
            decision = "REQUIRE_APPROVAL"
            guard_eval["decision"] = decision
            guard_eval["reasons"].append("Approval required by tool policy or degraded observability")

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
                    expires_at=expires_at,
                    state_version=proposal.state_version,
                    resource_version=self.resource_version(provider, proposal.target)
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
                    output={"approval_id": new_app_id, "status": "APPROVAL_REQUIRED", "expires_at": expires_at.isoformat(), "approval_required": True, "guard_decision": guard_eval},
                    idempotency_key=idemp_key
                )

            # Validate existing approval
            token = self.approved_tokens.get(approval_id)
            if not token or token.status != "APPROVED" or binding(token) != binding(proposal):
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
        if not resource_lock_manager.acquire(lock_target, operation_id, timeout_sec=0.5):
            current_holder = resource_lock_manager.get_holder(lock_target)
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
            # Recheck policy under the resource lock, immediately before any mutation.
            if self.guard.kill_switch_engaged or self.freeze_mutations or self.guard.autonomy_level == 0:
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="BLOCKED",
                    output={"reason": "Governance changed before execution"}, idempotency_key=idemp_key)
            current_policy = self.guard.evaluate_action(proposal.action_type, proposal.params,
                                                        proposal.incident_id, proposal.generated_by)
            current_approval_required = tool.mutating and (
                current_policy["decision"] == "REQUIRE_APPROVAL" or tool.requires_approval
                or metrics_collector.get_status().overall_status == "OBSERVABILITY_DEGRADED")
            if current_policy["decision"] == "BLOCK" or (current_approval_required and not approval_id):
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="BLOCKED",
                    output={"reason": "Current policy requires a new authorization", "guard_decision": current_policy},
                    idempotency_key=idemp_key)
            previous = idempotency_manager.check(idemp_key)
            if previous:
                return ExecutionResult.model_validate({key: value for key, value in previous.items() if key not in {"original_operation_id", "idempotent_replay"}})
            if approval_id and not self.approved_tokens.consume(approval_id, proposal, self.resource_version(provider, proposal.target)):
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="BLOCKED",
                    output={"error": "Approval consumed, mismatched, expired, or resource state changed"}, idempotency_key=idemp_key)
            if not idempotency_manager.reserve(idemp_key, operation_id, proposal):
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                    action_type=proposal.action_type, target=proposal.target, params=proposal.params, status="BLOCKED",
                    output={"reason": "Operation already in progress or requires reconciliation"}, idempotency_key=idemp_key)
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
            elif proposal.action_type in ("chaos_inject", "chaos_clear"):
                from backend.execution.sandbox_actions import execute_chaos
                mutation_output = execute_chaos(proposal, provider)
            elif proposal.action_type == "get_service_health":
                mutation_output = {"status": "SUCCESS", "health": provider.health_check(proposal.target)}
            elif proposal.action_type == "create_ticket":
                mutation_output = {"status": "SUCCESS", "ticket_id": proposal.proposal_id, "storage": "local_sql_operation", "external_ticket": False}
            else:
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                                       action_type=proposal.action_type, target=proposal.target, params=proposal.params,
                                       status="BLOCKED", output={"reason": "No execution adapter registered for this action", "outcome": "UNKNOWN"},
                                       idempotency_key=idemp_key)

            if str(mutation_output.get("status", "")).upper() not in ("SUCCESS", "OK"):
                return ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
                                       action_type=proposal.action_type, target=proposal.target, params=proposal.params,
                                       status="FAILED", output={"mutation": mutation_output, "outcome": "UNKNOWN"},
                                       idempotency_key=idemp_key)

            execution_duration_ms = (time.time() - start_time) * 1000.0

            # Record mutation in anti-thrashing cooldown tracker
            if tool.mutating and not proposal.action_type.startswith("chaos_"):
                anti_thrashing_manager.record_mutation(lock_target, proposal.action_type)
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

            def delta(key):
                before, after = pre_metrics[key], post_metrics[key]
                return after - before if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None
            p95_delta = delta("p95_ms")
            err_delta = delta("error_rate_pct")

            outcome, slo_satisfied = classify_outcome(proposal.target, pre_metrics, post_metrics)
            from backend.providers.sandbox_provider import LocalSandboxProvider
            allowed_sources = {"sandbox_model"} if isinstance(provider, LocalSandboxProvider) else {"prometheus"}
            if (not tool.mutating or proposal.action_type.startswith("chaos_")
                    or any(t.freshness != "FRESH" or t.source not in allowed_sources for t in (pre_telemetry, post_telemetry))):
                outcome, slo_satisfied = "UNKNOWN", False

            # SECTION 22 & INVARIANT 11: Real Rollback if outcome is WORSE
            rollback_res = None
            if outcome == "WORSE" and tool.reversible:
                ledger.record_event("rollback_triggered", "cortex-verifier", {"reason": "Post-action degradation detected"}, proposal.incident_id)
                if self.guard.kill_switch_engaged or self.freeze_mutations or self.guard.autonomy_level < 2:
                    rollback_res = {"status": "BLOCKED", "reason": "Current governance forbids automatic rollback"}
                else:
                    # Bounded compensation is part of the authorized reversible action.
                    rollback_res = provider.rollback_service(proposal.target)
                time.sleep(1.0)
                # Verify rollback itself
                rollback_telemetry = metrics_collector.collect(proposal.target)
                rollback_metrics = {"p95_ms": rollback_telemetry.p95_latency_ms, "error_rate_pct": rollback_telemetry.error_rate_pct}
                rollback_outcome, rollback_slo = classify_outcome(proposal.target, post_metrics, rollback_metrics)
                rollback_res.update(verification_outcome=rollback_outcome, slo_recovered=rollback_slo and rollback_telemetry.source in allowed_sources and rollback_telemetry.freshness == "FRESH", verified_p95_ms=rollback_telemetry.p95_latency_ms)
                ledger.record_event("rollback_completed", "cortex-verifier", rollback_res, proposal.incident_id)

            rollback_succeeded = bool(rollback_res and str(rollback_res.get("status", "")).upper() == "SUCCESS")
            status = "ROLLED_BACK" if rollback_succeeded else "FAILED" if outcome == "WORSE" else "SUCCESS"
            verification = VerificationResult(operation_id=operation_id, service=proposal.target, outcome=outcome,
                                              pre_metrics=pre_metrics, post_metrics=post_metrics,
                                              p95_change_ms=p95_delta, error_change_pct=err_delta,
                                              slo_satisfied=slo_satisfied, settling_time_sec=1.5,
                                              rollback_triggered=rollback_res is not None, rollback_result=rollback_res,
                                              simulated=post_telemetry.simulated, telemetry_source=post_telemetry.source)

            exec_result = ExecutionResult(
                operation_id=operation_id,
                proposal_id=proposal.proposal_id,
                action_type=proposal.action_type,
                target=proposal.target,
                params=proposal.params,
                status=status,
                output={
                    "mutation": mutation_output,
                    "guard_decision": guard_eval,
                    "pre_metrics": pre_metrics,
                    "post_metrics": post_metrics,
                    "p95_delta_ms": round(p95_delta, 2) if p95_delta is not None else None,
                    "outcome": outcome,
                    "verification": verification.model_dump(mode="json"),
                    "rollback": rollback_res
                },
                execution_time_ms=round(execution_duration_ms, 2),
                idempotency_key=idemp_key,
                provider_type=type(provider).__name__
            )

            # Save in idempotency store & record audit block
            idempotency_manager.record_execution(idemp_key, operation_id, proposal.action_type, proposal.target, exec_result.model_dump(mode="json"))
            ledger.record_event("action_completed", proposal.generated_by, exec_result.model_dump(mode="json"), proposal.incident_id)

            return exec_result

        finally:
            # Always release lock!
            resource_lock_manager.release(lock_target, operation_id)


# Global singleton gateway
execution_gateway = CortexExecutionGateway(guard=shared_guard)
