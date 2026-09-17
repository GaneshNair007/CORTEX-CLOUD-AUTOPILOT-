"""
CORTEX Cloud Autopilot — Service Level Objective (SLO) Package
"""

try:
    from backend.slo.config import SLOTarget, SERVICE_SLOS, get_slo_for_service, calculate_burn_rate, calculate_error_budget_remaining
except ImportError:
    from slo.config import SLOTarget, SERVICE_SLOS, get_slo_for_service, calculate_burn_rate, calculate_error_budget_remaining

__all__ = [
    "SLOTarget",
    "SERVICE_SLOS",
    "get_slo_for_service",
    "calculate_burn_rate",
    "calculate_error_budget_remaining"
]
