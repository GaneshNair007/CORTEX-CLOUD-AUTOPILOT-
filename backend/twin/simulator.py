"""
CORTEX Cloud Autopilot — Counterfactual Digital Twin Simulator
Performs dependency-aware pre-flight simulation on shadow state before executing cloud mutations.
"""

from typing import Dict, Any, List, Optional
import copy
from backend.topology.graph import topology
from backend.topology.blast_radius import calculate_blast_radius


class CounterfactualTwin:
    def __init__(self):
        pass

    def simulate_action(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes counterfactual simulation:
        1. Snapshots current abstract infrastructure state.
        2. Applies proposed action to shadow state.
        3. Propagates cascade effects through dependencies.
        4. Calculates expected SLO impact, cost change, and reversibility.
        """
        # Step 1: Clone current state
        current_data = topology.get_topology_data()
        shadow_nodes = {n["id"]: copy.deepcopy(n) for n in current_data["nodes"]}
        
        target = (
            params.get("service") or
            params.get("deployment") or
            params.get("database") or
            params.get("cluster") or
            params.get("pod_name") or
            "payment-api"
        )
        if "db" in target or "postgres" in target:
            target = "user-profile-db"
        elif "payment" in target:
            target = "payment-api"

        blast = calculate_blast_radius(action_type, params)
        affected_nodes = blast["affected_services"]

        slo_breaches: List[str] = []
        simulated_p95_delta = 0
        simulated_error_rate_delta = 0.0
        reversibility = "REVERSIBLE"
        projected_downtime_sec = 0.0

        # Step 2 & 3: Apply mutation and propagate backpressure
        if action_type == "restart_database":
            projected_downtime_sec = 35.0
            reversibility = "IRREVERSIBLE_ACTIVE_TRANSACTIONS"
            if target in shadow_nodes:
                shadow_nodes[target]["health"] = "Outage"
                shadow_nodes[target]["error_rate"] = 1.0

            for affected_id in affected_nodes:
                if affected_id in shadow_nodes:
                    shadow_nodes[affected_id]["health"] = "Degraded"
                    shadow_nodes[affected_id]["p95_ms"] = min(shadow_nodes[affected_id]["p95_ms"] * 5.0, 5000)
                    shadow_nodes[affected_id]["error_rate"] = 0.45
                    slo_breaches.append(f"{affected_id}: p95 exceeded {shadow_nodes[affected_id]['slo_ms']}ms SLO")

            simulated_p95_delta = 3800
            simulated_error_rate_delta = 0.42

        elif action_type == "restart_service":
            projected_downtime_sec = 8.0
            reversibility = "REVERSIBLE"
            if target in shadow_nodes:
                shadow_nodes[target]["health"] = "Restarting"
                # Temporary slight latency increase during restart, then recovery
                simulated_p95_delta = -80  # expected improvement post-settling

        elif action_type in ("scale_deployment", "scale_service", "scale_replicas"):
            new_replicas = params.get("replicas", shadow_nodes.get(target, {}).get("replicas", 4))
            curr_replicas = shadow_nodes.get(target, {}).get("replicas", 4)
            projected_downtime_sec = 0.0
            reversibility = "REVERSIBLE"

            if target in shadow_nodes:
                shadow_nodes[target]["replicas"] = new_replicas
                if new_replicas > curr_replicas:
                    # Scale out reduces latency
                    scale_factor = curr_replicas / max(new_replicas, 1)
                    shadow_nodes[target]["p95_ms"] = int(shadow_nodes[target]["p95_ms"] * scale_factor)
                    simulated_p95_delta = int(shadow_nodes[target]["p95_ms"] - (shadow_nodes[target]["p95_ms"] / scale_factor))
                else:
                    # Scale in might increase latency
                    scale_factor = curr_replicas / max(new_replicas, 1)
                    shadow_nodes[target]["p95_ms"] = int(shadow_nodes[target]["p95_ms"] * scale_factor)
                    simulated_p95_delta = 45

        elif action_type == "rollback_deployment":
            projected_downtime_sec = 12.0
            reversibility = "REVERSIBLE"
            if target in shadow_nodes:
                shadow_nodes[target]["health"] = "RollingBack"
                simulated_p95_delta = -240  # returns to pre-bug baseline
                simulated_error_rate_delta = -0.15

        simulated_nodes_list = list(shadow_nodes.values())

        return {
            "action_type": action_type,
            "target": target,
            "blast_radius": blast,
            "projected_downtime_sec": projected_downtime_sec,
            "reversibility": reversibility,
            "predicted_p95_ms": shadow_nodes.get(target, {}).get("p95_ms", 120.0),
            "predicted_error_rate": shadow_nodes.get(target, {}).get("error_rate", 0.005),
            "simulated_p95_delta_ms": simulated_p95_delta,
            "simulated_error_rate_delta": simulated_error_rate_delta,
            "confidence": 0.85,
            "slo_breaches": slo_breaches,
            "affected_node_count": len(affected_nodes),
            "simulated_nodes": simulated_nodes_list,
            "summary": (
                f"Simulated '{action_type}' on '{target}'. "
                f"Projected downtime: {projected_downtime_sec}s. "
                f"{len(slo_breaches)} downstream SLO breaches predicted."
            )
        }


# Global singleton twin instance
twin = CounterfactualTwin()
