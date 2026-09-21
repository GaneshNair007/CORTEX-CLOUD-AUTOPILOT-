"""Pure SLO outcome classification shared by execution and verification."""
import math
from backend.slo.config import get_slo_for_service


def classify_outcome(service: str, pre: dict, post: dict) -> tuple[str, bool]:
    """An unchanged unhealthy service is never a recovery; missing data is unknown."""
    def extract(metrics: dict):
        latency = metrics.get("p95_ms", metrics.get("p95_latency_ms"))
        error = metrics.get("error_rate_pct")
        error = error / 100 if isinstance(error, (float, int)) else metrics.get("error_rate")
        if not all(isinstance(v, (float, int)) and math.isfinite(v) and v >= 0 for v in (latency, error)):
            return None
        return latency, error
    before, after = extract(pre), extract(post)
    if before is None or after is None:
        return "UNKNOWN", False
    pre_p95, pre_err = before
    post_p95, post_err = after
    slo = get_slo_for_service(service)
    healthy = post_p95 <= slo.max_p95_ms and post_err <= slo.max_error_rate
    if (post_p95 > pre_p95 * 1.25 and post_p95 > slo.max_p95_ms) or (post_err > pre_err * 1.2 and post_err > slo.max_error_rate):
        return "WORSE", healthy
    if healthy:
        return "RECOVERED", True
    if post_p95 < pre_p95 or post_err < pre_err:
        return "PARTIALLY_RECOVERED", False
    return "NO_CHANGE", False
