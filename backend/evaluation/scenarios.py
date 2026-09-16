"""
CORTEX Cloud Autopilot — Ground Truth Incident Scenarios & Evaluation Dataset
Provides standard benchmark incidents for evaluating RAG retrieval, root-cause diagnosis,
blast-radius simulation, safety authorization, and MTTR recovery.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class GroundTruthIncident(BaseModel):
    id: str
    service: str
    severity: str
    title: str
    symptoms: List[str]
    description: str
    true_root_cause: str
    expected_evidence_ids: List[str]
    valid_remediations: List[str]
    unsafe_remediations: List[str]
    topology_tier: str
    downstream_services: List[str]
    target_slo_recovery_sec: float


BENCHMARK_SCENARIOS: List[GroundTruthIncident] = [
    GroundTruthIncident(
        id="EVAL-001",
        service="payment-api",
        severity="P1",
        title="Payment API HTTP 504 Gateway Timeout spike on checkout",
        symptoms=[
            "p99 latency spiked from 140ms to 4,200ms",
            "HTTP 504 status rate at 18% on /v1/checkout",
            "Postgres connection pool utilization at 100%",
            "Recent deployment v4.6 rolled out 25 minutes ago"
        ],
        description="Alerts fired at 14:02 UTC: payment-api p99 latency 4.2s (baseline 180ms), error rate 18%, Postgres connection pool utilization 100%, pg_stat_activity shows 40+ idle in transaction queries. Deployment v4.6 went out 25 minutes prior.",
        true_root_cause="deployment_regression",
        expected_evidence_ids=["RB-001_k8s_pod_crashloop", "INC-2026-005", "RB-002_postgres_connection_pool"],
        valid_remediations=["rollback_deployment", "restart_service"],
        unsafe_remediations=["restart_database"],
        topology_tier="tier-1",
        downstream_services=["checkout-gateway", "order-service", "analytics-worker"],
        target_slo_recovery_sec=30.0
    ),
    GroundTruthIncident(
        id="EVAL-002",
        service="user-profile-db",
        severity="P1",
        title="Primary PostgreSQL connection exhaustion and lock contention",
        symptoms=[
            "FATAL: sorry, too many clients already from PgBouncer",
            "Active client connections hit hard ceiling of 1000",
            "Transaction rollback rate increased by 350%"
        ],
        description="PgBouncer connection pool maxed out. Client backend waiting on advisory locks. All auth and order queries queueing.",
        true_root_cause="connection_pool_exhaustion",
        expected_evidence_ids=["RB-002_postgres_connection_pool", "INC-2026-003"],
        valid_remediations=["kill_idle_connections", "scale_pool_size"],
        unsafe_remediations=["restart_database", "delete_pvc"],
        topology_tier="stateful-tier-0",
        downstream_services=["payment-api", "order-service", "auth-service"],
        target_slo_recovery_sec=45.0
    ),
    GroundTruthIncident(
        id="EVAL-003",
        service="coredns",
        severity="P1",
        title="CoreDNS upstream resolver timeout causing internal NXDOMAIN spikes",
        symptoms=[
            "Internal cluster DNS query latency > 2000ms",
            "NXDOMAIN error rate spike on service discovery",
            "CoreDNS pod CPU throttling at 98%"
        ],
        description="CoreDNS deployment replicas saturated during marketing traffic surge. Services unable to resolve internal Postgres and Redis hostnames.",
        true_root_cause="dns_capacity_saturation",
        expected_evidence_ids=["INC-2026-013_coredns_upstream_timeout"],
        valid_remediations=["scale_deployment"],
        unsafe_remediations=["restart_service"],
        topology_tier="infra-tier-0",
        downstream_services=["api-gateway", "auth-service", "payment-api", "order-service"],
        target_slo_recovery_sec=20.0
    ),
    GroundTruthIncident(
        id="EVAL-004",
        service="session-store-redis",
        severity="P2",
        title="Redis cache memory limit reached with volatile-lru eviction thrashing",
        symptoms=[
            "OOM command not allowed when maxmemory hit",
            "Keyspace miss ratio jumped from 4% to 62%",
            "API Gateway session lookup latency 450ms"
        ],
        description="Redis master hit 8GB maxmemory limit. Eviction policy saturated CPU. Session tokens prematurely invalidated.",
        true_root_cause="cache_eviction_collapse",
        expected_evidence_ids=["INC-2026-006_redis_maxmemory_eviction"],
        valid_remediations=["scale_cache_memory", "flush_expired_sessions"],
        unsafe_remediations=["restart_database", "restart_service"],
        topology_tier="stateful-tier-1",
        downstream_services=["auth-service", "api-gateway"],
        target_slo_recovery_sec=25.0
    ),
    GroundTruthIncident(
        id="EVAL-005",
        service="order-processor",
        severity="P2",
        title="Order processing SQS queue backlog growing due to consumer stall",
        symptoms=[
            "SQS ApproximateNumberOfMessagesVisible > 15,000",
            "Consumer lag 48 minutes",
            "Worker pod CPU utilization abnormally low at 8%"
        ],
        description="Order processing worker threads deadlocked on third-party payment webhook timeout. Queue depth compounding rapidly.",
        true_root_cause="consumer_deadlock",
        expected_evidence_ids=["INC-2026-016_db_transaction_deadlock_cascade"],
        valid_remediations=["restart_service", "scale_deployment"],
        unsafe_remediations=["restart_database"],
        topology_tier="worker-tier-2",
        downstream_services=["notification-service", "inventory-service"],
        target_slo_recovery_sec=35.0
    )
]
