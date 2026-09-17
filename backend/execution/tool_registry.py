"""
CORTEX Cloud Autopilot — Infrastructure Tool Registry
Strict registry of predefined, bounded infrastructure actions.
Rule: Any tool not explicitly registered is unconditionally BLOCKED.
"""

from typing import Dict, Any, Optional, List, Callable, Literal
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    mutating: bool
    risk_class: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    reversible: bool
    allowed_environments: List[str] = Field(default_factory=lambda: ["sandbox", "staging", "production"])
    required_capability: str
    timeout_seconds: int = 30
    max_retries: int = 1
    cooldown_seconds: int = 60
    requires_approval: bool = False
    param_schema: Dict[str, type] = Field(default_factory=dict)


class ToolRegistry:
    """Central registry of permissible infrastructure mutations."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        # 1. Scale Service / Replicas (Low Risk, Reversible)
        self.register(ToolDefinition(
            name="scale_service",
            description="Adjust horizontal replica count of a stateless service deployment.",
            mutating=True,
            risk_class="LOW",
            reversible=True,
            allowed_environments=["sandbox", "staging", "production"],
            required_capability="scaling",
            timeout_seconds=20,
            max_retries=2,
            cooldown_seconds=60,
            requires_approval=False,
            param_schema={"service": str, "replicas": int},
        ))

        self.register(ToolDefinition(
            name="scale_replicas",
            description="Alias for scale_service.",
            mutating=True,
            risk_class="LOW",
            reversible=True,
            allowed_environments=["sandbox", "staging", "production"],
            required_capability="scaling",
            timeout_seconds=20,
            max_retries=2,
            cooldown_seconds=60,
            requires_approval=False,
            param_schema={"service": str, "replicas": int},
        ))

        # 2. Restart Service (Medium Risk, Container Restart)
        self.register(ToolDefinition(
            name="restart_service",
            description="Gracefully restarts pods or container workers of a stateless service.",
            mutating=True,
            risk_class="MEDIUM",
            reversible=False,
            allowed_environments=["sandbox", "staging", "production"],
            required_capability="restart",
            timeout_seconds=15,
            max_retries=1,
            cooldown_seconds=120,
            requires_approval=False,
            param_schema={"service": str},
        ))

        # 3. Rollback Deployment (Medium Risk, Reversible)
        self.register(ToolDefinition(
            name="rollback_deployment",
            description="Rolls back a service deployment to the previous verified stable image/revision.",
            mutating=True,
            risk_class="MEDIUM",
            reversible=True,
            allowed_environments=["sandbox", "staging", "production"],
            required_capability="rollback",
            timeout_seconds=30,
            max_retries=1,
            cooldown_seconds=60,
            requires_approval=False,
            param_schema={"service": str},
        ))

        # 4. Failover to Replica (High Risk, Stateful Database)
        self.register(ToolDefinition(
            name="failover_to_replica",
            description="Promotes a standby database replica to primary.",
            mutating=True,
            risk_class="HIGH",
            reversible=False,
            allowed_environments=["sandbox", "staging", "production"],
            required_capability="db_admin",
            timeout_seconds=60,
            max_retries=0,
            cooldown_seconds=300,
            requires_approval=True,
            param_schema={"service": str},
        ))

        # 5. Restart Database (Critical Risk, Dangerous — Blocked in Production)
        self.register(ToolDefinition(
            name="restart_database",
            description="Attempts a hard kill or restart of primary database instance.",
            mutating=True,
            risk_class="CRITICAL",
            reversible=False,
            allowed_environments=["sandbox"],  # Explicitly forbidden in production!
            required_capability="db_admin",
            timeout_seconds=60,
            max_retries=0,
            cooldown_seconds=600,
            requires_approval=True,
            param_schema={"service": str},
        ))

        # 6. Read-Only Telemetry / Ticket Tools
        self.register(ToolDefinition(
            name="get_service_health",
            description="Queries liveness and readiness probe.",
            mutating=False,
            risk_class="LOW",
            reversible=True,
            allowed_environments=["sandbox", "staging", "production"],
            required_capability="read_only",
            timeout_seconds=5,
            max_retries=3,
            cooldown_seconds=0,
            requires_approval=False,
            param_schema={"service": str},
        ))

        self.register(ToolDefinition(
            name="create_ticket",
            description="Logs an engineering incident ticket without mutating cluster state.",
            mutating=False,
            risk_class="LOW",
            reversible=True,
            allowed_environments=["sandbox", "staging", "production"],
            required_capability="read_only",
            timeout_seconds=5,
            max_retries=3,
            cooldown_seconds=0,
            requires_approval=False,
            param_schema={"service": str},
        ))

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._tools

    def is_mutating(self, name: str) -> bool:
        tool = self.get(name)
        return tool.mutating if tool else False

    def validate_call(self, name: str, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        tool = self.get(name)
        if not tool:
            return False, f"Unknown tool: '{name}' is not registered in ToolRegistry. Execution BLOCKED."

        for param_name, param_type in tool.param_schema.items():
            if param_name in params:
                val = params[param_name]
                if not isinstance(val, param_type):
                    try:
                        # Attempt coercion for numbers e.g. "9" -> 9
                        params[param_name] = param_type(val)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{param_name}' must be of type {param_type.__name__}, got {type(val).__name__}."
        return True, None


tool_registry = ToolRegistry()
