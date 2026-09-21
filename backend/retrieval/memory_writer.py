"""Verified lifecycle -> SQL transaction -> Chroma upsert, with a durable outbox."""
import json
from typing import Any
from backend.models.proposals import ActionProposal, ExecutionResult, VerificationResult
from backend.rag.documents import make_document
from backend.rag.index import ChromaIndex, SemanticUnavailable
from .models import RetrievalContext
from .fingerprint import build_fingerprint
from .repository import KnowledgeRepository
from .metrics import event


class IncidentMemoryWriter:
    def __init__(self, repository: KnowledgeRepository, semantic: ChromaIndex):
        self.repository = repository
        self.semantic = semantic

    def write(self, context: RetrievalContext, proposal: ActionProposal, execution: ExecutionResult,
              verification: VerificationResult, *, diagnosis: str | None = None,
              policy: dict | None = None, simulation: dict | None = None,
              mttr: float | None = None) -> dict[str, Any]:
        """Only a completed verifier result is eligible for learned evidence.

        Failed remediations remain verified observations, not successful recipes.
        A generated diagnosis is explicitly labeled as a hypothesis.
        """
        if verification.operation_id != execution.operation_id or proposal.proposal_id != execution.proposal_id:
            raise ValueError("verification must belong to the executed operation")
        if verification.service != proposal.target or (context.incident_id and context.incident_id != proposal.incident_id):
            raise ValueError("verification and context must belong to the incident target")
        if execution.status not in ("SUCCESS", "ROLLED_BACK", "FAILED") or execution.output.get("dry_run"):
            raise ValueError("unexecuted proposals cannot become verified memories")
        if verification.outcome == "UNKNOWN" or not verification.pre_metrics or not verification.post_metrics:
            raise ValueError("verification is inconclusive; no trusted memory may be written")
        if verification.outcome == "RECOVERED" and not verification.slo_satisfied:
            raise ValueError("recovery requires verified SLO satisfaction")
        from backend.verification.outcomes import classify_outcome
        measured_outcome, measured_slo = classify_outcome(proposal.target, verification.pre_metrics, verification.post_metrics)
        if verification.outcome == "RECOVERED" and (measured_outcome != "RECOVERED" or not measured_slo):
            raise ValueError("verification metrics do not demonstrate recovery")
        status = "VERIFIED_RECOVERED" if verification.outcome == "RECOVERED" else verification.outcome
        if verification.simulated:
            context = context.model_copy(update={"environment": "sandbox"})
        payload = {"incident_id": context.incident_id or proposal.incident_id,
                   "context": context.model_dump(mode="json"), "fingerprint": build_fingerprint(context).model_dump(),
                   "diagnosis_hypothesis": diagnosis, "proposal": proposal.model_dump(mode="json"),
                   "execution": execution.model_dump(mode="json"), "verification": verification.model_dump(mode="json"),
                   "policy_decision": policy, "digital_twin": simulation}
        doc_id = f"memory:{proposal.incident_id}:{proposal.proposal_id}"
        data = {**context.model_dump(mode="json"), "id": doc_id,
                "title": f"{context.service or proposal.target}: {context.query_text[:160]}",
                "memory_status": status, "verification_outcome": status, "verified": True,
                "historical_action": proposal.action_type, "action_type": proposal.action_type,
                "rollback_performed": bool(verification.rollback_result and str(verification.rollback_result.get("status", "")).upper() == "SUCCESS"),
                "slo_recovered": verification.slo_satisfied,
                "simulated": verification.simulated,
                "timestamp": verification.verified_at.isoformat(),
                "failure_mode": build_fingerprint(context).failure_mode}
        if status == "VERIFIED_RECOVERED":
            data["resolved_at"] = verification.verified_at.isoformat()
            if mttr is not None:
                data["mttr"] = mttr
        content = f"Incident: {proposal.incident_id}\nService: {context.service}\nSymptoms: {context.query_text}\n"
        content += f"Diagnosis hypothesis (not a verified root cause): {diagnosis or 'not available'}\n"
        content += f"Executed action: {proposal.action_type}\nVerification outcome: {status}\n"
        if status in ("WORSE", "ROLLED_BACK", "NO_CHANGE"):
            content += "NEGATIVE EVIDENCE: this remediation did not recover the service.\n"
        content += json.dumps({k: v for k, v in payload.items() if k not in ("diagnosis_hypothesis",)}, default=str, sort_keys=True)
        document = make_document(data, content, "memory")
        self.repository.write_memory(document, payload)
        try:
            self.semantic.upsert([document], self.repository.revision)
            self.repository.mark_indexed([document])
            state = "INDEXED"
        except SemanticUnavailable:
            state = "PENDING"
            event("retrieval_degraded", context.incident_id, reason="memory_index_pending", memory_id=doc_id)
        return {"id": doc_id, "memory_status": status, "index_state": state,
                "trusted": document.metadata["trusted"],
                "warning": "semantic index unavailable; memory persisted in SQL and lexical index" if state == "PENDING" else None}

    def replay_pending(self) -> int:
        """Idempotently replay SQL outbox after a semantic outage."""
        documents = self.repository.documents(pending_only=True)
        self.semantic.upsert(documents, self.repository.revision)
        self.repository.mark_indexed(documents)
        return len(documents)


if __name__ == "__main__":
    from .engine import get_engine
    engine = get_engine()
    print(json.dumps({"indexed": IncidentMemoryWriter(engine.repository, engine.semantic).replay_pending()}))
