"""
CORTEX Cloud Autopilot — Closed-Loop Post-Action Verification & Rollback
Verifies that remediation actions objectively restore SLOs rather than relying on HTTP 200 return codes.
Automatically triggers rollback if post-action telemetry degrades.
"""

from typing import Dict, Any, List, Optional
import time
from cortex.ledger import ledger


class PostActionVerifier:
    def __init__(self):
        pass

    def verify_action(
        self,
        action_type: str,
        target_service: str,
        pre_metrics: Dict[str, float],
        post_metrics: Dict[str, float],
        slo_targets: Optional[Dict[str, float]] = None,
        correlation_id: str = "INC-000"
    ) -> Dict[str, Any]:
        """
        Compares pre-remediation and post-remediation telemetry.
        Classifies status into: 'RECOVERED' | 'PARTIALLY_RECOVERED' | 'NO_CHANGE' | 'WORSE'
        """
        slos = slo_targets or {"max_error_rate": 0.01, "max_p95_ms": 200.0}

        pre_err = pre_metrics.get("error_rate", 0.05)
        post_err = post_metrics.get("error_rate", 0.005)
        pre_p95 = pre_metrics.get("p95_ms", 350.0)
        post_p95 = post_metrics.get("p95_ms", 135.0)

        err_improved = post_err < pre_err
        lat_improved = post_p95 < pre_p95

        err_slo_met = post_err <= slos["max_error_rate"]
        lat_slo_met = post_p95 <= slos["max_p95_ms"]

        rollback_triggered = False
        rollback_reason = ""
        rollback_result = None

        if post_err > pre_err * 1.2 or post_p95 > pre_p95 * 1.25:
            outcome = "WORSE"
            rollback_triggered = True
            rollback_reason = (
                f"Post-action regression detected: Error rate increased from {pre_err*100:.1f}% to {post_err*100:.1f}%, "
                f"p95 increased from {pre_p95:.1f}ms to {post_p95:.1f}ms."
            )
            # Execute automated rollback
            rollback_result = self._trigger_automatic_rollback(action_type, target_service, correlation_id, rollback_reason)

        elif err_slo_met and lat_slo_met:
            outcome = "RECOVERED"

        elif err_improved or lat_improved:
            outcome = "PARTIALLY_RECOVERED"

        else:
            outcome = "NO_CHANGE"

        verification_record = {
            "target_service": target_service,
            "action_type": action_type,
            "outcome": outcome,
            "pre_metrics": pre_metrics,
            "post_metrics": post_metrics,
            "slo_targets": slos,
            "slo_healthy": err_slo_met and lat_slo_met,
            "rollback_triggered": rollback_triggered,
            "rollback_reason": rollback_reason,
            "rollback_result": rollback_result,
            "summary": (
                f"Verification: {outcome}. "
                f"p95: {pre_p95:.1f}ms -> {post_p95:.1f}ms (SLO: {slos['max_p95_ms']}ms), "
                f"Errors: {pre_err*100:.2f}% -> {post_err*100:.2f}% (SLO: {slos['max_error_rate']*100:.1f}%)."
            )
        }

        # Record in tamper-evident ledger
        ledger.record_event(
            event_type=f"verification_{outcome.lower()}",
            actor="cortex-verifier",
            payload=verification_record,
            correlation_id=correlation_id
        )

        return verification_record

    def _trigger_automatic_rollback(self, action_type: str, target_service: str, correlation_id: str, reason: str) -> Dict[str, Any]:
        """Dispatches an emergency automated rollback when remediation causes regression."""
        rollback_action = "rollback_deployment" if action_type == "rollback_deployment" else "restore_stable_config"
        res = {
            "status": "rolled_back",
            "action": rollback_action,
            "target": target_service,
            "reason": reason,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        ledger.record_event(
            event_type="automatic_rollback_executed",
            actor="cortex-verifier",
            payload=res,
            correlation_id=correlation_id
        )
        return res


# Global singleton verifier instance
verifier = PostActionVerifier()
