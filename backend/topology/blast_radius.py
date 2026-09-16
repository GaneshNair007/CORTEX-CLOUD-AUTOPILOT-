"""
CORTEX Cloud Autopilot — Change Blast Radius Calculator
Computes topological blast radius scores (0–100) and affected critical paths for any candidate mutation.
"""

from typing import Dict, Any, List
from topology.graph import topology


def calculate_blast_radius(action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes blast radius across the dependency topology.
    Returns:
        score: int (0 to 100)
        risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'
        directly_affected: str
        affected_services: List[str]
        critical_paths: List[List[str]]
        failover_ready: bool
        explanation: str
    """
    target = (
        params.get("service") or
        params.get("deployment") or
        params.get("database") or
        params.get("cluster") or
        params.get("pod_name") or
        "unknown"
    )

    # Normalize target name
    if "db" in target or "postgres" in target:
        target = "user-profile-db"
    elif "redis" in target or "cache" in target:
        target = "session-store"
    elif "payment" in target:
        target = "payment-api"
    elif "auth" in target:
        target = "auth-service"
    elif "order" in target:
        target = "order-service"

    node_data = topology.graph.nodes.get(target, {})
    criticality = node_data.get("criticality", 3)
    is_stateful = node_data.get("is_stateful", False)
    failover_ready = node_data.get("failover_available", True)
    replicas = node_data.get("replicas", 1)

    # Downstream services impacted if target goes down
    affected_services = topology.get_downstream_dependencies(target)
    critical_paths = topology.get_critical_paths(target)

    # Calculate weighted blast radius score
    score = 0

    if action_type in ["restart_database", "delete_resource", "truncate_table"]:
        base_impact = 45
        stateful_mult = 25 if is_stateful else 10
        downstream_mult = min(len(affected_services) * 8, 25)
        failover_penalty = 0 if failover_ready else 15
        score = base_impact + stateful_mult + downstream_mult + failover_penalty

    elif action_type in ["rollback_deployment"]:
        base_impact = 25
        downstream_mult = min(len(affected_services) * 6, 20)
        criticality_impact = criticality * 5
        score = base_impact + downstream_mult + criticality_impact

    elif action_type in ["restart_service", "restart_pod"]:
        base_impact = 15
        redundancy_discount = -10 if replicas > 1 else 15
        downstream_mult = min(len(affected_services) * 4, 15)
        score = base_impact + redundancy_discount + downstream_mult

    elif action_type in ["scale_deployment"]:
        new_replicas = params.get("replicas", replicas)
        delta = abs(new_replicas - replicas)
        scale_in_penalty = 15 if new_replicas < replicas else 0
        score = 10 + min(delta * 2, 20) + scale_in_penalty

    else:
        score = 10

    score = max(5, min(100, score))

    if score >= 75:
        risk_level = "CRITICAL"
    elif score >= 50:
        risk_level = "HIGH"
    elif score >= 25:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    # Human-readable explanation
    if is_stateful and not failover_ready:
        explanation = (
            f"Action '{action_type}' on stateful resource '{target}' impairs {len(affected_services)} "
            f"upstream services ({', '.join(list(affected_services)[:3])}). No active failover replica is available."
        )
    elif affected_services:
        explanation = (
            f"Action '{action_type}' on '{target}' impacts {len(affected_services)} dependent services "
            f"with {replicas} active instances."
        )
    else:
        explanation = f"Action '{action_type}' is localized to '{target}' with minimal downstream propagation."

    return {
        "score": score,
        "risk_level": risk_level,
        "directly_affected": target,
        "affected_services": sorted(list(affected_services)),
        "critical_paths": critical_paths[:3],
        "failover_ready": failover_ready,
        "explanation": explanation
    }
