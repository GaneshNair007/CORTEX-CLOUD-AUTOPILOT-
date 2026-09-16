"""
CORTEX Cloud Autopilot — Policy-as-Code Engine
Implements deterministic governance rules evaluated independently of LLM prompts.
"""

from typing import Dict, Any, List, Tuple
import time


class PolicyRule:
    def __init__(self, code: str, name: str, description: str):
        self.code = code
        self.name = name
        self.description = description

    def evaluate(self, action_type: str, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Returns:
            (triggered: bool, decision: 'BLOCK'|'REQUIRE_APPROVAL'|'ALLOW', reason: str)
        """
        raise NotImplementedError


class DatabaseFailoverPolicy(PolicyRule):
    def __init__(self):
        super().__init__(
            code="POL-001",
            name="Stateful Database Failover Protection",
            description="Production DB restart is BLOCKED when active failover is unavailable."
        )

    def evaluate(self, action_type: str, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str, str]:
        if action_type in ["restart_database", "truncate_table"]:
            failover_ready = context.get("failover_ready", False)
            if not failover_ready:
                return True, "BLOCK", f"Policy {self.code}: Database restart blocked because no active failover replica is configured."
            return True, "REQUIRE_APPROVAL", f"Policy {self.code}: Stateful database restart requires human approval."
        return False, "ALLOW", ""


class BlastRadiusLimitPolicy(PolicyRule):
    def __init__(self):
        super().__init__(
            code="POL-002",
            name="Blast Radius Threshold Guard",
            description="Actions with blast radius >= 70 require manual approval."
        )

    def evaluate(self, action_type: str, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str, str]:
        blast_score = context.get("blast_radius_score", 0)
        if blast_score >= 80:
            return True, "BLOCK", f"Policy {self.code}: Blast radius score ({blast_score}/100) exceeds safety limit of 80."
        if blast_score >= 60:
            return True, "REQUIRE_APPROVAL", f"Policy {self.code}: High blast radius ({blast_score}/100) mandates human approval."
        return False, "ALLOW", ""


class MinimumCapacityReservePolicy(PolicyRule):
    def __init__(self):
        super().__init__(
            code="POL-003",
            name="SLO Minimum Capacity Reserve",
            description="Scaling cannot decrease service replica count below 2."
        )

    def evaluate(self, action_type: str, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str, str]:
        if action_type == "scale_deployment":
            replicas = params.get("replicas", 1)
            if replicas < 2:
                return True, "BLOCK", f"Policy {self.code}: Cannot scale below minimum SLO redundancy threshold (min 2 replicas, requested {replicas})."
        return False, "ALLOW", ""


class AntiThrashingTemporalPolicy(PolicyRule):
    def __init__(self, cooldown_seconds: int = 60):
        super().__init__(
            code="POL-004",
            name="Temporal Anti-Thrashing Cooldown",
            description="Prevents rapid consecutive mutations on the same service within cooldown window."
        )
        self.cooldown_seconds = cooldown_seconds
        self.last_mutation_time: Dict[str, float] = {}

    def evaluate(self, action_type: str, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str, str]:
        service = params.get("service") or params.get("deployment") or "unknown"
        now = time.time()
        last_time = self.last_mutation_time.get(service, 0.0)
        elapsed = now - last_time

        if elapsed < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - elapsed)
            return True, "BLOCK", f"Policy {self.code}: Service '{service}' is in cooldown for {remaining}s to prevent control thrashing."
        return False, "ALLOW", ""

    def record_mutation(self, service: str) -> None:
        self.last_mutation_time[service] = time.time()


# Registry of active policies
ACTIVE_POLICIES = [
    DatabaseFailoverPolicy(),
    BlastRadiusLimitPolicy(),
    MinimumCapacityReservePolicy(),
    AntiThrashingTemporalPolicy(cooldown_seconds=30)
]
