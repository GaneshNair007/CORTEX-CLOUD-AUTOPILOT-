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

        # Apply specific fault types
        result = {}
        if fault_type == "db_outage":
            # Target postgres or redis directly
            db_target = "redis" if "redis" in service_name else "postgres"
            result = sandbox_manager.inject_fault(db_target, "crash", duration_sec=duration_sec, intensity=1.0)
            target_to_record = db_target
        elif fault_type in ("crash", "process_kill"):
            result = sandbox_manager.inject_fault(service_name, "crash", duration_sec=duration_sec, intensity=1.0)
            target_to_record = service_name
        elif fault_type == "traffic_flood":
            # High intensity latency + error burst
            result = sandbox_manager.inject_fault(service_name, "latency", duration_sec=duration_sec, intensity=max(150.0, intensity * 50))
            sandbox_manager.inject_fault(service_name, "error_burst", duration_sec=duration_sec, intensity=min(80.0, intensity * 20))
            target_to_record = service_name
        else:
            result = sandbox_manager.inject_fault(service_name, fault_type, duration_sec=duration_sec, intensity=intensity)
            target_to_record = service_name

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
        res = sandbox_manager.restart_service(service_name)

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
                    exp["status"] = "COMPLETED"
            return list(self._active_experiments.values())

    def stop_all(self, environment: str = "sandbox") -> Dict[str, Any]:
        """Emergency stop for all running chaos experiments."""
        if environment.lower() not in self.ALLOWED_ENVIRONMENTS:
            raise PermissionError(f"Safety violation: stop_all rejected for environment '{environment}'")

        cleared_services = []
        with self._lock:
            for eid, exp in list(self._active_experiments.items()):
                target = exp.get("target_service")
                if target and target not in cleared_services:
                    sandbox_manager.restart_service(target)
                    cleared_services.append(target)
                exp["status"] = "ABORTED"

        return {"status": "ALL_STOPPED", "cleared_services": cleared_services}


chaos_engine = ChaosEngine()
