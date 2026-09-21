"""Sandbox-only mutation adapter called exclusively by the execution gateway."""
from backend.models.proposals import ActionProposal
from backend.providers.sandbox_provider import LocalSandboxProvider
from sandbox.manager import sandbox_manager


def execute_chaos(proposal: ActionProposal, provider) -> dict:
    if not isinstance(provider, LocalSandboxProvider):
        return {"status": "FAILED", "reason": "Chaos requires an explicit local sandbox provider"}
    if proposal.target not in sandbox_manager.specs:
        return {"status": "FAILED", "reason": "Unknown sandbox target"}
    if proposal.action_type == "chaos_clear":
        result = sandbox_manager.restart_service(proposal.target)
        return {"status": "SUCCESS" if result.get("status") in {"SUCCESS", "RESTARTED"} else "FAILED", "details": result}
    fault = proposal.params.get("fault_type")
    duration = proposal.params.get("duration_sec", 30)
    intensity = proposal.params.get("intensity", 1.0)
    if fault not in {"cpu_stress", "latency", "error_burst", "crash"} or type(duration) is not int or not 1 <= duration <= 120:
        return {"status": "FAILED", "reason": "Invalid fault or duration (1–120 seconds required)"}
    if not isinstance(intensity, (int, float)) or not 0 < intensity <= 1000:
        return {"status": "FAILED", "reason": "Invalid fault intensity"}
    result = sandbox_manager.inject_fault(proposal.target, fault, duration_sec=duration, intensity=intensity)
    return {"status": "SUCCESS" if result.get("status") in {"APPLIED", "INJECTED", "FAULT_INJECTED", "SUCCESS"} else "FAILED", "details": result}
