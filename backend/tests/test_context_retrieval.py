"""Behavioral retrieval, validation, safety and lifecycle regression coverage."""
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.rag.documents import make_document
from backend.rag.index import SemanticUnavailable, ChromaIndex
from backend.retrieval.models import RetrievalContext, RetrievalOptions, EvidenceRequest
from backend.retrieval.config import RetrievalConfig
from backend.retrieval.repository import KnowledgeRepository
from backend.retrieval.engine import RetrievalEngine
from backend.retrieval.context_builder import ContextBuilder
from backend.retrieval.fingerprint import build_fingerprint
from backend.retrieval.normalization import normalize, error_signatures
from backend.retrieval.memory_writer import IncidentMemoryWriter
from backend.models.proposals import ActionProposal, ExecutionResult, VerificationResult
from backend.verification.outcomes import classify_outcome

NOW = datetime(2026, 9, 19, tzinfo=timezone.utc)


class UnavailableIndex:
    def query(self, *args, **kwargs):
        raise SemanticUnavailable("test outage")

    def upsert(self, *args, **kwargs):
        raise SemanticUnavailable("test outage")


def doc(doc_id, service="payment-api", status="VERIFIED_RECOVERED", age=1, body=None, **metadata):
    body = body or "PostgreSQL connection pool exhaustion SQLSTATE 53300 HTTP 503 too many clients"
    return make_document({"id": doc_id, "title": body, "service": service, "verified": status != "UNVERIFIED",
                          "memory_status": status, "timestamp": (NOW - timedelta(days=age)).isoformat(), **metadata}, body, "incident")


@pytest.fixture
def repository():
    sql = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    repo = KnowledgeRepository(sql)
    yield repo
    sql.dispose()


def retrieve(repository, documents, context=None, **options):
    repository.upsert(documents)
    return RetrievalEngine(repository, UnavailableIndex()).retrieve(
        context or RetrievalContext(query_text="Postgres connection pool exhaustion SQLSTATE 53300 HTTP 503", service="payment-api"),
        RetrievalOptions(**options), now=NOW)


def test_same_service_ranks_first_and_cross_service_survives(repository):
    bundle = retrieve(repository, [doc("other", service="user-profile-api"), doc("same")])
    assert bundle.evidence[0].id == "same"
    assert "other" in [e.id for e in bundle.evidence]
    assert "RELAXED_SERVICE" in bundle.stages_attempted
    assert "service" in bundle.relaxed_filters


def test_wrong_technology_ranks_below_pool_incident(repository):
    bundle = retrieve(repository, [doc("pg"), doc("redis", body="Redis cache memory eviction HTTP 503", technologies=["redis"])])
    scores = {e.id: e.final_score for e in bundle.evidence}
    assert scores["pg"] > scores["redis"] + .15


def test_exact_signature_boost(repository):
    context = RetrievalContext(query_text="CrashLoopBackOff", technologies=["k8s"])
    bundle = retrieve(repository, [doc("crash", body="Kubernetes CrashLoopBackOff missing secret"), doc("dns", body="Kubernetes DNS issue")], context)
    assert bundle.evidence[0].id == "crash"
    assert bundle.evidence[0].lexical_score > 0
    assert any("exact signal" in reason for reason in bundle.evidence[0].why_retrieved)


def test_recency_keeps_old_but_prefers_recent(repository):
    bundle = retrieve(repository, [doc("old", age=1095), doc("new", age=1)], enable_diversification=False)
    assert [e.id for e in bundle.evidence] == ["new", "old"]


def test_verified_outcome_preferred(repository):
    bundle = retrieve(repository, [doc("unverified", status="UNVERIFIED"), doc("verified")])
    assert bundle.evidence[0].id == "verified"
    assert bundle.evidence[0].trust_score > bundle.evidence[1].trust_score


def test_negative_evidence_reliable_but_unsuccessful(repository):
    bundle = retrieve(repository, [doc("failed", status="WORSE", historical_action="restart_database")])
    evidence = bundle.evidence[0]
    assert evidence.trust_score > evidence.outcome_score
    assert "NEGATIVE EVIDENCE" in " ".join(evidence.why_retrieved)
    assert evidence.public_result()["verification_outcome"] == "WORSE"
    filtered = RetrievalEngine(repository, UnavailableIndex()).retrieve(bundle.context, RetrievalOptions(include_failed_incidents=False))
    assert filtered.evidence == []


def test_no_evidence_and_explicit_semantic_outage(repository):
    bundle = retrieve(repository, [doc("pg")], RetrievalContext(query_text="zzzzunrelatedqxyz"))
    assert bundle.evidence == []
    assert bundle.status == "DEGRADED_RETRIEVAL"
    assert not bundle.semantic_available
    assert "no relevant evidence found" in bundle.warnings
    assert "semantic index unavailable; lexical fallback used" in bundle.warnings


def test_boundaries_not_relaxed(repository):
    bundle = retrieve(repository, [doc("tenant", tenant_id="private"), doc("deprecated", deprecated=True), doc("otherenv", environment="staging")],
                      RetrievalContext(query_text="Postgres pool exhaustion", environment="production"), require_environment_match=True)
    assert not bundle.evidence


@pytest.mark.parametrize("values", [{"top_k": 100000}, {"candidate_k": 201}, {"top_k": 10, "candidate_k": 5}, {"max_age_days": -1}, {"where": {"service": "x"}}])
def test_invalid_options_rejected(values):
    with pytest.raises(ValidationError):
        RetrievalOptions(**values)


@pytest.mark.parametrize("values", [{"high_confidence": 2}, {"weights": {"semantic": 1}}, {"min_acceptable": .9, "high_confidence": .8}])
def test_invalid_configuration(values):
    with pytest.raises(ValidationError):
        RetrievalConfig(**values)


def test_normalization_fingerprint_and_topology():
    import networkx as nx
    graph = nx.DiGraph()
    graph.add_edge("checkout", "payment-api", weight=1.)
    graph.add_edge("payment-api", "postgres", weight=.9, protocol="postgres")
    context = ContextBuilder().build({"id": "x", "service": "payment-api", "description": "PostgreSQL SQLSTATE 53300 HTTP 503"},
                                     {"cpu_percent": 43, "p95_latency_ms": 780, "error_rate_pct": 18, "source": "prometheus"}, graph)
    assert context.region is None
    assert context.dependencies == ["postgres", "checkout"]
    assert context.dependency_weights["postgres"] > context.dependency_weights["checkout"]
    assert context.telemetry_signature["cpu"] == "normal"
    assert context.telemetry_signature["latency"] == "critical"
    assert build_fingerprint(context).failure_mode == "connection_pool_exhaustion"
    assert normalize("PG") == normalize("PostgreSQL") == "postgresql"
    assert "k8s_oomkilled" in error_signatures("OOMKilled")


def lifecycle(outcome="RECOVERED"):
    context = RetrievalContext(incident_id="new", query_text="Postgres pool exhaustion HTTP 503", service="payment-api")
    proposal = ActionProposal(incident_id="new", action_type="restart_service", target="payment-api", params={"service": "payment-api"})
    execution = ExecutionResult(operation_id="operation", proposal_id=proposal.proposal_id, action_type=proposal.action_type,
                                target=proposal.target, params=proposal.params, status="SUCCESS", idempotency_key="key")
    verification = VerificationResult(operation_id="operation", service="payment-api", outcome=outcome,
                                       pre_metrics={"p95_ms": 900, "error_rate_pct": 18}, post_metrics={"p95_ms": 100, "error_rate_pct": .1},
                                       p95_change_ms=-800, error_change_pct=-17.9, slo_satisfied=outcome == "RECOVERED")
    return context, proposal, execution, verification


def test_sql_outbox_survives_semantic_failure_and_replays(repository):
    context, proposal, execution, verified = lifecycle()
    writer = IncidentMemoryWriter(repository, UnavailableIndex())
    result = writer.write(context, proposal, execution, verified)
    assert result["index_state"] == "PENDING"
    assert len(repository.documents(pending_only=True)) == 1
    bundle = RetrievalEngine(repository, UnavailableIndex()).retrieve(context)
    assert bundle.evidence[0].id == result["id"]
    working = Mock()
    assert IncidentMemoryWriter(repository, working).replay_pending() == 1
    assert repository.documents(pending_only=True) == []


def test_unverified_memory_rejected(repository):
    context, proposal, execution, verification = lifecycle("UNKNOWN")
    with pytest.raises(ValueError, match="inconclusive"):
        IncidentMemoryWriter(repository, UnavailableIndex()).write(context, proposal, execution, verification)
    assert not repository.documents()


def test_recovery_requires_slo_not_command_success():
    assert classify_outcome("payment-api", {"p95_ms": 30000, "error_rate_pct": 100}, {"p95_ms": 30000, "error_rate_pct": 100}) == ("NO_CHANGE", False)
    assert classify_outcome("payment-api", {"p95_ms": 900, "error_rate_pct": .5}, {"p95_ms": 100, "error_rate_pct": .1}) == ("RECOVERED", True)
    assert classify_outcome("payment-api", {}, {}) == ("UNKNOWN", False)


def test_legacy_facade_and_apis(repository, monkeypatch):
    repository.upsert([doc("pg")])
    engine = RetrievalEngine(repository, UnavailableIndex())
    import backend.retrieval.engine as engine_module
    monkeypatch.setattr(engine_module, "get_engine", lambda: engine)
    from backend.rag.retrieve import retrieve as legacy
    assert legacy("database timeout postgres", 3)[0]["id"] == "pg"
    from backend import api_server
    monkeypatch.setattr(api_server, "get_engine", lambda: engine)
    from fastapi.testclient import TestClient
    client = TestClient(api_server.app)
    old = client.post("/api/rag/retrieve", json={"query": "postgres pool", "k": 3})
    assert old.status_code == 200 and old.json()["results"][0]["id"] == "pg"
    new = client.post("/api/v1/evidence/retrieve", json={"query": "postgres pool", "context": {"service": "payment-api"}, "options": {"top_k": 3}})
    assert new.status_code == 200 and new.json()["results"][0]["why_retrieved"]
    assert client.post("/api/v1/evidence/retrieve", json={"query": "x", "options": {"top_k": 100000}}).status_code == 422
    assert client.post("/api/v1/evidence/retrieve", json={"query": "x", "context": {"where": {}}}).status_code == 422
    assert client.post("/api/rag/retrieve", json={"query": "x", "k": 100000}).status_code == 422


def test_pipeline_retrieves_once_and_does_not_resolve_execution_alone(repository, monkeypatch):
    import backend.control_plane.pipeline as pipeline
    retrieval = RetrievalEngine(repository, UnavailableIndex())
    retrieval.retrieve = Mock(wraps=retrieval.retrieve)
    monkeypatch.setattr(pipeline, "get_engine", lambda: retrieval)
    def execute(proposal, **kwargs):
        return ExecutionResult(operation_id="single", proposal_id=proposal.proposal_id, action_type=proposal.action_type,
                               target=proposal.target, params=proposal.params, status="SUCCESS", output={}, idempotency_key="one")
    monkeypatch.setattr(pipeline.execution_gateway, "evaluate_and_execute", execute)
    result = pipeline.ControlPlanePipeline().run_control_loop(service="payment-api", symptom="PostgreSQL pool exhaustion")
    assert retrieval.retrieve.call_count == 1
    assert not result["stages"]["learn"]["incident_resolved"]
    assert result["stages"]["learn"]["memory"] is None


def test_real_chroma_migration_and_learn_loop(repository, tmp_path):
    """Uses actual MiniLM embeddings and persistent Chroma, never a fake vector score."""
    from backend.rag.rebuild_index import rebuild
    semantic = ChromaIndex(tmp_path / "chroma")
    stats = rebuild(repository, semantic, sources=[doc("seed")])
    assert stats["schema"] == 2 and stats["total"] == 1
    writer = IncidentMemoryWriter(repository, semantic)
    context, proposal, execution, verification = lifecycle()
    result = writer.write(context, proposal, execution, verification)
    assert result["index_state"] == "INDEXED"
    writer.write(context, proposal, execution, verification)
    assert semantic.collection().count() == 2
    bundle = RetrievalEngine(repository, semantic).retrieve(context, RetrievalOptions(verified_only=True))
    assert result["id"] in [e.id for e in bundle.evidence]
    negative = verification.model_copy(update={"outcome": "WORSE", "slo_satisfied": False,
                                               "rollback_result": {"status": "SUCCESS"}})
    writer.write(context, proposal, execution, negative)
    bundle = RetrievalEngine(repository, semantic).retrieve(context)
    memory = next(e for e in bundle.evidence if e.id == result["id"])
    assert memory.public_result()["verification_outcome"] == "WORSE"
    assert memory.public_result()["rollback_performed"] is True
    assert memory.metadata["trusted"] is False
    assert rebuild(repository, semantic, sources=[doc("seed")])["total"] == 2
