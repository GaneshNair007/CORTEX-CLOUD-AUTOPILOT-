"""
CORTEX Cloud Autopilot — Closed-Loop Post-Action Verification & Rollback
Verifies that remediation actions objectively restore SLOs rather than relying on HTTP 200 return codes.
Automatically triggers rollback via the active cloud provider if post-action telemetry degrades.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from backend.models.proposals import VerificationResult
    from backend.slo.config import get_slo_for_service, SLOTarget
    from backend.providers import get_active_provider
    from backend.cortex.ledger import ledger
except ImportError:
    from models.proposals import VerificationResult
    from slo.config import get_slo_for_service, SLOTarget
    from providers import get_active_provider
    from cortex.ledger import ledger


class PostActionVerifier:
    """
    Closed-loop verifier:
    Captures pre vs post telemetry delta.
    Evaluates against explicit service SLO thresholds.
    Triggers immediate real rollback if degradation ('WORSE') is detected.
    """

    def __init__(self):
        pass

    def verify_action(
        self,
        operation_id: str,
        target_service: str,
        action_type: str,
        pre_metrics: Dict[str, float],
        post_metrics: Dict[str, float],
        settling_time_sec: float = 5.0,
        correlation_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Compares pre-remediation and post-remediation telemetry.
        Returns a strongly-typed VerificationResult.
        """
        cid = correlation_id or operation_id
        slo = get_slo_for_service(target_service)

        pre_err = float(pre_metrics.get("error_rate", pre_metrics.get("error_rate_pct", 0.0)))
        post_err = float(post_metrics.get("error_rate", post_metrics.get("error_rate_pct", 0.0)))
        pre_p95 = float(pre_metrics.get("p95_ms", pre_metrics.get("p95_latency_ms", 0.0)))
        post_p95 = float(post_metrics.get("p95_ms", post_metrics.get("p95_latency_ms", 0.0)))

        # Normalize percentages if given as 0-100 vs 0-1
        if pre_err > 1.0:
            pre_err_frac = pre_err / 100.0
            post_err_frac = post_err / 100.0
        else:
            pre_err_frac = pre_err
            post_err_frac = post_err

        error_change_pct = round(post_err - pre_err, 3)
        p95_change_ms = round(post_p95 - pre_p95, 2)

        err_slo_met = post_err_frac <= slo.max_error_rate
        lat_slo_met = post_p95 <= slo.max_p95_ms
        slo_satisfied = err_slo_met and lat_slo_met

        rollback_triggered = False
        rollback_result = None

        # Regression detection threshold:
        # If error rate increased by >20% or latency increased by >25%
        is_worse = False
        if post_err_frac > (pre_err_frac * 1.20) and post_err_frac > slo.max_error_rate:
            is_worse = True
        elif post_p95 > (pre_p95 * 1.25) and post_p95 > slo.max_p95_ms:
            is_worse = True

        if is_worse:
            outcome = "WORSE"
            rollback_triggered = True
            rollback_reason = (
                f"Automated verification triggered rollback: "
                f"Error rate changed by {error_change_pct:+.2f}%, "
                f"p95 latency changed by {p95_change_ms:+.1f}ms (SLO: {slo.max_p95_ms}ms)."
            )
            # Execute real rollback via provider
            rollback_result = self._execute_real_rollback(
                target_service=target_service,
                action_type=action_type,
                reason=rollback_reason,
                correlation_id=cid
            )

        elif slo_satisfied:
            outcome = "RECOVERED"

        elif (post_err_frac < pre_err_frac) or (post_p95 < pre_p95):
            outcome = "PARTIALLY_RECOVERED"

        elif abs(error_change_pct) < 0.05 and abs(p95_change_ms) < 5.0:
            outcome = "NO_CHANGE"

        else:
            outcome = "UNKNOWN"

        result = VerificationResult(
            operation_id=operation_id,
            service=target_service,
            outcome=outcome,
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            p95_change_ms=p95_change_ms,
            error_change_pct=error_change_pct,
            slo_satisfied=slo_satisfied,
            verified_at=datetime.now(timezone.utc),
            settling_time_sec=settling_time_sec,
            rollback_triggered=rollback_triggered,
            rollback_result=rollback_result
        )

        ledger.record_event(
            event_type=f"verification_{outcome.lower()}",
            actor="cortex-verifier",
            payload=result.model_dump(mode="json"),
            correlation_id=cid
        )

        return result

    def _execute_real_rollback(
        self,
        target_service: str,
        action_type: str,
        reason: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Dispatches an emergency rollback to the real cloud provider."""
        from backend.cortex.gateway import execution_gateway
        from backend.models.proposals import ActionProposal
        proposal = ActionProposal(incident_id=correlation_id, action_type="rollback_deployment",
            target=target_service, params={"service": target_service}, reason=reason, generated_by="cortex-verifier")
        execution = execution_gateway.evaluate_and_execute(proposal)
        prov_res = execution.model_dump(mode="json")

        rollback_record = {
            "action": "automated_rollback",
            "target_service": target_service,
            "original_action": action_type,
            "reason": reason,
            "provider_response": prov_res,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        ledger.record_event(
            event_type="automated_rollback_dispatched",
            actor="cortex-verifier",
            payload=rollback_record,
            correlation_id=correlation_id
        )

        return rollback_record


verifier = PostActionVerifier()
