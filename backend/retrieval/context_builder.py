"""Enrich incidents from actual supplied telemetry and configured topology."""
from typing import Any
from .config import RetrievalConfig, get_config
from .models import RetrievalContext, ContextHints
from .normalization import technologies


class ContextBuilder:
    def __init__(self, config: RetrievalConfig | None = None):
        self.config = config or get_config()

    def build(self, incident: dict[str, Any], telemetry: dict[str, Any] | None = None,
              topology: Any = None, metadata: dict[str, Any] | None = None) -> RetrievalContext:
        """Missing context remains absent; graph health/demo metrics are never used."""
        merged = {**(metadata or {}), **incident}
        fields = {k: merged[k] for k in ContextHints.model_fields if k in merged and merged[k] is not None}
        fields["service"] = fields.get("service") or merged.get("affected_service")
        fields["query_text"] = str(merged.get("query_text") or merged.get("description") or merged.get("symptom") or merged.get("title") or "Incident without diagnostic text")
        fields["incident_id"] = merged.get("incident_id") or merged.get("id")
        fields["technologies"] = list(dict.fromkeys([*fields.get("technologies", []), *technologies(fields["query_text"])]))
        weights = {}
        graph = topology if hasattr(topology, "successors") else getattr(topology, "graph", None)
        service = fields.get("service")
        if graph is not None and service in graph:
            node = graph.nodes[service]
            for key in ("region", "environment", "provider", "service_family", "resource_type", "deployment_version"):
                if key in node:
                    fields.setdefault(key, node[key])
            deps = list(fields.get("dependencies", []))
            dep_types = list(fields.get("dependency_types", []))
            for target in graph.successors(service):
                deps.append(target)
                edge = graph.edges[service, target]
                weights[target] = float(edge.get("weight", 1))
                if edge.get("protocol"):
                    dep_types.append(edge["protocol"])
            for caller in graph.predecessors(service):
                deps.append(caller)
                weights[caller] = .5 * float(graph.edges[caller, service].get("weight", 1))
            fields["dependencies"] = list(dict.fromkeys(deps))[:64]
            fields["dependency_types"] = list(dict.fromkeys(dep_types))[:32]
        signature = dict(fields.get("telemetry_signature", {}))
        if telemetry and telemetry.get("freshness", "FRESH") == "FRESH" and telemetry.get("source") not in ("fallback", "unavailable", "http_probe"):
            aliases = {"cpu_percent": "cpu", "memory_percent": "memory", "db_connections_pct": "db_connections",
                       "p95_latency_ms": "latency", "p95_ms": "latency", "error_rate_pct": "error_rate"}
            thresholds = dict(self.config.telemetry_thresholds)
            if service:
                from backend.slo.config import get_slo_for_service
                slo = get_slo_for_service(service)
                thresholds["latency"] = [slo.max_p95_ms, slo.max_p95_ms * 2]
                thresholds["error_rate"] = [slo.max_error_rate * 100, slo.max_error_rate * 200]
            for raw, key in aliases.items():
                value = telemetry.get(raw)
                if isinstance(value, (float, int)):
                    high, critical = thresholds[key]
                    signature[key] = "critical" if value >= critical else "high" if value >= high else "normal"
        fields["telemetry_signature"] = signature
        return RetrievalContext(**fields, dependency_weights=weights)
