"""
CORTEX Cloud Autopilot — Real Chaos Engineering Engine
Provides controlled, policy-governed fault injection strictly bounded to the sandbox environment.
"""

import time
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sandbox.manager import sandbox_manager
try:
    from backend.cortex.ledger import ledger
except ImportError:
    from cortex.ledger import ledger


class ChaosEngine:
    """
    Chaos engineering controller for running controlled resilience experiments.
    Strict Invariant: Never allows fault injection outside the 'sandbox' environment.
    """

    ALLOWED_ENVIRONMENTS = {"sandbox", "local", "test"}
    VALID_FAULTS = {
        "cpu_stress",
        "latency",
        "error_burst",
        "crash",
        "process_kill",
        "db_outage",
        "traffic_flood"
    }

    def __init__(self):
        self._active_experiments: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def inject_fault(
        self,
        target_service: str,
        fault_type: str,
        duration_sec: int = 30,
        intensity: float = 1.0,
        environment: str = "sandbox",
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Injects a real fault into the target service in the sandbox environment.
        Raises PermissionError if environment is not sandbox.
        """
        cid = correlation_id or f"CHAOS-{int(time.time()*1000)}"

        # STRICT SAFETY INVARIANT: Only sandbox environment allowed
        if environment.lower() not in self.ALLOWED_ENVIRONMENTS:
            err_msg = (
                f"SAFETY INVARIANT VIOLATION: Chaos injection strictly rejected for environment '{environment}'. "
                f"Chaos testing is only permitted in {self.ALLOWED_ENVIRONMENTS}."
            )
            ledger.record_event(
                event_type="chaos_safety_violation_blocked",
                actor="cortex-chaos-engine",
                payload={"target_service": target_service, "environment": environment, "fault_type": fault_type},
                correlation_id=cid
            )
            raise PermissionError(err_msg)

        if fault_type not in self.VALID_FAULTS:
            return {
                "status": "REJECTED",
                "error": f"Invalid fault type: {fault_type}. Valid types: {sorted(list(self.VALID_FAULTS))}"
            }

        # Normalize service name
        service_name = target_service.lower().replace("_", "-")
        if service_name == "payment-api":
            service_name = "payment-service"
        elif service_name == "postgres-primary":
            service_name = "postgres"

        from backend.cortex.gateway import execution_gateway
        from backend.models.proposals import ActionProposal
        from backend.providers.sandbox_provider import LocalSandboxProvider
        if not 1 <= duration_sec <= 120:
            return {"status": "REJECTED", "error": "Duration must be 1–120 seconds"}
        target_to_record = ("redis" if "redis" in service_name else "postgres") if fault_type == "db_outage" else service_name
        actual_fault = "crash" if fault_type in {"crash", "process_kill", "db_outage"} else "latency" if fault_type == "traffic_flood" else fault_type
        proposal = ActionProposal(incident_id=cid, action_type="chaos_inject", target=target_to_record,
            params={"service": target_to_record, "fault_type": actual_fault, "duration_sec": duration_sec, "intensity": intensity},
            risk_score=40, generated_by="cortex-chaos-engine")
        execution = execution_gateway.evaluate_and_execute(proposal, custom_provider=LocalSandboxProvider())
        if execution.status != "SUCCESS":
            return {"status": execution.status, "execution_result": execution.model_dump(mode="json")}
        result = execution.output

        experiment_id = f"exp-{target_to_record}-{fault_type}-{int(time.time())}"
        exp_record = {
            "experiment_id": experiment_id,
            "target_service": target_to_record,
            "fault_type": fault_type,
            "duration_sec": duration_sec,
            "intensity": intensity,
            "environment": environment,
            "start_time": time.time(),
            "expires_at": time.time() + duration_sec,
            "status": "RUNNING",
            "provider_result": result
        }

        with self._lock:
            self._active_experiments[experiment_id] = exp_record

        # Schedule automatic fault cleanup when duration elapses
        def auto_cleanup():
            time.sleep(duration_sec)
            self.clear_faults(target_to_record, environment=environment, experiment_id=experiment_id)

        cleanup_thread = threading.Thread(target=auto_cleanup, daemon=True, name=f"chaos-cleanup-{experiment_id}")
        cleanup_thread.start()

        ledger.record_event(
            event_type="chaos_fault_injected",
            actor="cortex-chaos-engine",
            payload=exp_record,
            correlation_id=cid
        )

        return {
            "status": "ACTIVE",
            "experiment_id": experiment_id,
            "target_service": target_to_record,
            "fault_type": fault_type,
            "duration_sec": duration_sec,
            "intensity": intensity,
            "details": result
        }

    def inject_cascading_failure(
        self,
        root_service: str = "postgres",
        cascade_chain: Optional[List[str]] = None,
        duration_sec: int = 30,
        environment: str = "sandbox"
    ) -> Dict[str, Any]:
        """
        Simulates a multi-tier cascading cloud outage starting from root_service
        and propagating up to dependent upstream services (e.g. postgres -> payment-service -> api-gateway).
        """
        if environment.lower() not in self.ALLOWED_ENVIRONMENTS:
            raise PermissionError(f"SAFETY INVARIANT: Cascading failure injection strictly rejected for environment '{environment}'.")

        chain = cascade_chain or [root_service, "payment-service", "api-gateway"]
        results = {}
        for idx, svc in enumerate(chain):
            if idx == 0:
                res = self.inject_fault(svc, "latency", duration_sec=duration_sec, intensity=250.0, environment=environment)
            elif idx == 1:
                res = self.inject_fault(svc, "error_burst", duration_sec=duration_sec, intensity=40.0, environment=environment)
            else:
                res = self.inject_fault(svc, "latency", duration_sec=duration_sec, intensity=100.0, environment=environment)
            results[svc] = res

        ledger.record_event(
            event_type="chaos_cascading_failure_injected",
            actor="cortex-chaos-engine",
            payload={"root_service": root_service, "cascade_chain": chain, "tier_count": len(chain)}
        )

        return {
            "status": "CASCADING_ACTIVE",
            "root_service": root_service,
            "cascade_chain": chain,
            "tier_count": len(chain),
            "tier_results": results
        }

    def clear_faults(
        self,
        target_service: str,
        environment: str = "sandbox",
        experiment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clears all active faults on the target service."""
        if environment.lower() not in self.ALLOWED_ENVIRONMENTS:
            raise PermissionError(f"Safety violation: clear_faults rejected for environment '{environment}'")

        service_name = target_service.lower().replace("_", "-")
        if service_name == "payment-api":
            service_name = "payment-service"
        elif service_name == "postgres-primary":
            service_name = "postgres"

        # Restart / reset service state in sandbox
        from backend.cortex.gateway import execution_gateway
        from backend.models.proposals import ActionProposal
        from backend.providers.sandbox_provider import LocalSandboxProvider
        proposal = ActionProposal(incident_id=f"CHAOS-CLEAR-{time.time_ns()}", action_type="chaos_clear", target=service_name,
            params={"service": service_name}, risk_score=20, generated_by="chaos-cleanup")
        execution = execution_gateway.evaluate_and_execute(proposal, custom_provider=LocalSandboxProvider())
        if execution.status != "SUCCESS":
            return {"status": execution.status, "execution_result": execution.model_dump(mode="json")}
        res = execution.output

        with self._lock:
            if experiment_id and experiment_id in self._active_experiments:
                self._active_experiments[experiment_id]["status"] = "COMPLETED"
            else:
                for eid, exp in self._active_experiments.items():
                    if exp.get("target_service") == service_name:
                        exp["status"] = "CLEARED"

        ledger.record_event(
            event_type="chaos_faults_cleared",
            actor="cortex-chaos-engine",
            payload={"target_service": service_name, "status": "CLEARED", "result": res}
        )

        return {"status": "CLEARED", "target_service": service_name, "result": res}

    def list_active_experiments(self) -> List[Dict[str, Any]]:
        """Lists all currently active or recently completed experiments."""
        now = time.time()
        with self._lock:
            # Auto-expire completed ones
            for exp in self._active_experiments.values():
                if exp["status"] == "RUNNING" and now > exp["expires_at"]:
                    exp["status"] = "EXPIRED_AWAITING_CLEANUP"
            return list(self._active_experiments.values())

    def stop_all(self, environment: str = "sandbox") -> Dict[str, Any]:
        """Emergency stop for all running chaos experiments."""
        if environment.lower() not in self.ALLOWED_ENVIRONMENTS:
            raise PermissionError(f"Safety violation: stop_all rejected for environment '{environment}'")

        with self._lock:
            targets = {exp["target_service"] for exp in self._active_experiments.values()}
        results = {target: self.clear_faults(target, environment) for target in targets}
        cleared = [target for target, result in results.items() if result["status"] == "CLEARED"]
        return {"status": "ALL_STOPPED" if len(cleared) == len(targets) else "BLOCKED", "cleared_services": cleared, "results": results}


chaos_engine = ChaosEngine()
