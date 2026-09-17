"""
CORTEX Cloud Autopilot — Digital Twin & Topology Graph Tests
"""

import pytest
from backend.topology.graph import topology
from backend.topology.blast_radius import calculate_blast_radius
from backend.twin.simulator import twin


def test_topology_graph_structure():
    data = topology.get_topology_data()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 5
    assert len(data["edges"]) >= 4

    # Check payment-api or payment-service exists
    service_names = [n["id"] for n in data["nodes"]]
    assert "payment-api" in service_names or "payment-service" in service_names


def test_blast_radius_calculation():
    blast = calculate_blast_radius("restart_database", {"database": "user-profile-db"})
    assert blast["score"] >= 90
    assert blast["risk_level"] == "CRITICAL"
    assert len(blast["affected_services"]) >= 2


def test_twin_simulation_counterfactual():
    sim = twin.simulate_action("scale_service", {"service": "payment-service", "replicas": 8})
    assert "predicted_p95_ms" in sim
    assert "predicted_error_rate" in sim
    assert "confidence" in sim
    assert sim["confidence"] > 0.5
