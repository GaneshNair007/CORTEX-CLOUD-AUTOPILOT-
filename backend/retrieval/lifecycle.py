"""Persist reasoning context before authorization so delayed approvals can learn."""
import json
from sqlalchemy import Table, Column, String, Text, select
from sqlalchemy.dialects.sqlite import insert
from backend.persistence.database import engine
from backend.persistence.models import Base
from backend.models.proposals import ActionProposal, ExecutionResult, VerificationResult
from .models import RetrievalContext

contexts = Table("incident_learning_contexts", Base.metadata,
    Column("proposal_id", String, primary_key=True), Column("payload", Text, nullable=False))


def prepare_learning(proposal: ActionProposal, context: RetrievalContext,
                     diagnosis: str | None = None, simulation: dict | None = None) -> None:
    """Keep the original incident context in SQL across approval/restart boundaries."""
    contexts.create(engine, checkfirst=True)
    payload = json.dumps({"context": context.model_dump(mode="json"), "diagnosis": diagnosis, "simulation": simulation})
    with engine.begin() as conn:
        statement = insert(contexts).values(proposal_id=proposal.proposal_id, payload=payload)
        conn.execute(statement.on_conflict_do_nothing(index_elements=["proposal_id"]))


def learn_verified_execution(proposal: ActionProposal, execution: ExecutionResult) -> dict | None:
    """Close LEARN for immediate, manual and later-approved gateway operations."""
    if execution.output.get("dry_run") or execution.output.get("idempotent_replay"):
        return None
    data = execution.output.get("verification")
    if not data or data.get("outcome") == "UNKNOWN":
        return None
    from .engine import get_engine
    from .memory_writer import IncidentMemoryWriter
    from backend.persistence.database import db_manager
    contexts.create(engine, checkfirst=True)
    with engine.connect() as conn:
        payload = conn.execute(select(contexts.c.payload).where(contexts.c.proposal_id == proposal.proposal_id)).scalar()
    stored = json.loads(payload) if payload else {}
    context = RetrievalContext.model_validate(stored["context"]) if payload else RetrievalContext(
        incident_id=proposal.incident_id, service=proposal.target,
        query_text=proposal.reason or proposal.rationale or f"Manual {proposal.action_type} on {proposal.target}")
    verification = VerificationResult.model_validate(data)
    retrieval = get_engine()
    result = IncidentMemoryWriter(retrieval.repository, retrieval.semantic).write(
        context, proposal, execution, verification, diagnosis=stored.get("diagnosis"),
        policy=execution.output.get("guard_decision"), simulation=stored.get("simulation"))
    if verification.outcome == "RECOVERED" and verification.slo_satisfied:
        db_manager.resolve_incident(proposal.incident_id)
    return result
