"""
CORTEX Cloud Autopilot — State & Infrastructure Topology Graph
Models the multi-tier microservice dependency graph using NetworkX.
Provides graph traversal, downstream dependency resolution, and critical path analysis.
"""

from typing import Dict, Any, List, Optional, Set
import networkx as nx


class TopologyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_default_topology()

    def _build_default_topology(self) -> None:
        """Constructs the canonical 10-service cloud architecture topology."""
        nodes = [
            {
                "id": "ingress-controller",
                "name": "Cloud Ingress Proxy",
                "tier": "edge",
                "criticality": 5,
                "replicas": 4,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 1250,
                "p95_ms": 15,
                "error_rate": 0.001,
                "slo_ms": 50,
                "region": "us-east-1",
                "az": "us-east-1a"
            },
            {
                "id": "api-gateway",
                "name": "API Gateway Envoy",
                "tier": "edge",
                "criticality": 5,
                "replicas": 6,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 1200,
                "p95_ms": 32,
                "error_rate": 0.002,
                "slo_ms": 80,
                "region": "us-east-1",
                "az": "us-east-1a"
            },
            {
                "id": "auth-service",
                "name": "Authentication & OAuth",
                "tier": "tier-1",
                "criticality": 5,
                "replicas": 4,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 450,
                "p95_ms": 45,
                "error_rate": 0.001,
                "slo_ms": 100,
                "region": "us-east-1",
                "az": "us-east-1b"
            },
            {
                "id": "payment-api",
                "name": "Payment Gateway API",
                "tier": "tier-1",
                "criticality": 5,
                "replicas": 6,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 380,
                "p95_ms": 142,
                "error_rate": 0.005,
                "slo_ms": 200,
                "region": "us-east-1",
                "az": "us-east-1c"
            },
            {
                "id": "order-service",
                "name": "Order Management Engine",
                "tier": "tier-1",
                "criticality": 4,
                "replicas": 5,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 320,
                "p95_ms": 95,
                "error_rate": 0.002,
                "slo_ms": 150,
                "region": "us-east-1",
                "az": "us-east-1a"
            },
            {
                "id": "inventory-service",
                "name": "Inventory & Stock Sync",
                "tier": "tier-2",
                "criticality": 3,
                "replicas": 3,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 210,
                "p95_ms": 68,
                "error_rate": 0.001,
                "slo_ms": 120,
                "region": "us-east-1",
                "az": "us-east-1b"
            },
            {
                "id": "notification-service",
                "name": "Async Dispatch & Alerts",
                "tier": "tier-2",
                "criticality": 2,
                "replicas": 2,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 95,
                "p95_ms": 110,
                "error_rate": 0.004,
                "slo_ms": 250,
                "region": "us-east-1",
                "az": "us-east-1c"
            },
            {
                "id": "session-store",
                "name": "Redis Session Master",
                "tier": "stateful",
                "criticality": 4,
                "replicas": 2,
                "is_stateful": True,
                "health": "Healthy",
                "rps": 650,
                "p95_ms": 8,
                "error_rate": 0.000,
                "slo_ms": 20,
                "region": "us-east-1",
                "az": "us-east-1a",
                "failover_available": True
            },
            {
                "id": "user-profile-db",
                "name": "PostgreSQL Primary Cluster",
                "tier": "stateful",
                "criticality": 5,
                "replicas": 1,
                "is_stateful": True,
                "health": "Healthy",
                "rps": 580,
                "p95_ms": 22,
                "error_rate": 0.001,
                "slo_ms": 50,
                "region": "us-east-1",
                "az": "us-east-1a",
                "failover_available": False  # Crucial for blast-radius demos
            },
            {
                "id": "order-db",
                "name": "PostgreSQL Orders Read/Write",
                "tier": "stateful",
                "criticality": 4,
                "replicas": 2,
                "is_stateful": True,
                "health": "Healthy",
                "rps": 310,
                "p95_ms": 28,
                "error_rate": 0.002,
                "slo_ms": 60,
                "region": "us-east-1",
                "az": "us-east-1b",
                "failover_available": True
            },
            {
                "id": "coredns",
                "name": "Cluster CoreDNS Cluster",
                "tier": "infra",
                "criticality": 5,
                "replicas": 4,
                "is_stateful": False,
                "health": "Healthy",
                "rps": 2400,
                "p95_ms": 4,
                "error_rate": 0.000,
                "slo_ms": 10,
                "region": "us-east-1",
                "az": "multi-az"
            }
        ]

        for n in nodes:
            self.graph.add_node(n["id"], **n)

        # Edges directed from upstream caller to downstream provider
        dependencies = [
            ("ingress-controller", "api-gateway", {"protocol": "http2", "weight": 1.0}),
            ("api-gateway", "auth-service", {"protocol": "grpc", "weight": 0.9}),
            ("api-gateway", "payment-api", {"protocol": "sync_http", "weight": 1.0}),
            ("api-gateway", "order-service", {"protocol": "sync_http", "weight": 0.9}),
            ("auth-service", "session-store", {"protocol": "redis", "weight": 0.95}),
            ("auth-service", "user-profile-db", {"protocol": "postgres", "weight": 0.85}),
            ("payment-api", "user-profile-db", {"protocol": "postgres", "weight": 1.0}),
            ("payment-api", "session-store", {"protocol": "redis", "weight": 0.7}),
            ("payment-api", "notification-service", {"protocol": "async_sqs", "weight": 0.4}),
            ("order-service", "inventory-service", {"protocol": "grpc", "weight": 0.85}),
            ("order-service", "order-db", {"protocol": "postgres", "weight": 1.0}),
            ("order-service", "notification-service", {"protocol": "async_sqs", "weight": 0.5}),
            ("inventory-service", "order-db", {"protocol": "postgres", "weight": 0.75})
        ]

        for src, dst, attrs in dependencies:
            self.graph.add_edge(src, dst, **attrs)

    def get_topology_data(self) -> Dict[str, Any]:
        """Returns node and edge dictionary representations suitable for React Flow."""
        nodes_data = []
        for node_id, data in self.graph.nodes(data=True):
            nodes_data.append({"id": node_id, **data})

        edges_data = []
        for src, dst, data in self.graph.edges(data=True):
            edges_data.append({"id": f"{src}->{dst}", "source": src, "target": dst, **data})

        return {"nodes": nodes_data, "edges": edges_data}

    def get_downstream_dependencies(self, resource_id: str) -> List[str]:
        """
        Returns all nodes that depend directly or transitively on the given resource.
        Note: In our directed call graph (caller -> callee), if callee fails,
        the upstream callers are affected. We traverse PREDECESSORS in the call graph.
        """
        if resource_id not in self.graph:
            return []

        # Find upstream services that call this resource (i.e. Ancestors in caller graph)
        affected = nx.ancestors(self.graph, resource_id)
        return list(affected)

    def get_critical_paths(self, resource_id: str) -> List[List[str]]:
        """Finds paths from edge entry point (ingress-controller) to the resource."""
        if resource_id not in self.graph or "ingress-controller" not in self.graph:
            return []
        try:
            return list(nx.all_simple_paths(self.graph, source="ingress-controller", target=resource_id))
        except Exception:
            return []

    def update_node_health(self, resource_id: str, health: str, p95_ms: Optional[float] = None, error_rate: Optional[float] = None) -> None:
        """Updates health and metrics for a specific node in real time."""
        if resource_id in self.graph:
            self.graph.nodes[resource_id]["health"] = health
            if p95_ms is not None:
                self.graph.nodes[resource_id]["p95_ms"] = p95_ms
            if error_rate is not None:
                self.graph.nodes[resource_id]["error_rate"] = error_rate


# Global singleton topology graph instance
topology = TopologyGraph()
