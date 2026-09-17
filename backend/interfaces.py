"""Frozen interface contract between orchestrator/ (llm side) and rag/ + tools/ (partner side).

These four signatures must never change without both partners agreeing first.
This module is the stable facade: callers may import retrieve/remember/
execute_action/emit_event from here and stay decoupled from where the real
implementations live.

Retrieval routes to rag/retrieve.py (ChromaDB semantic search) with an
automatic fallback to rag/store.py (keyword overlap) when the vector DB is
unavailable. Results are normalised to always expose both 'kind' and
'document_type' so legacy consumers (orchestrator) and new consumers (app.py)
both work without changes.

Events route to tools/event_bus.py (thread-safe, persistent JSONL timeline).

Implementations are imported lazily so this file imports cleanly in any
checkout; a missing module surfaces as an ImportError only when called.
"""


def retrieve(query: str, k: int) -> list[dict]:
    """Return up to k relevant documents (runbooks / past incidents).

    Each dict has at least: {"id": str, "kind": str, "document_type": str,
    "title": str, "text": str, "score": float}.
    """
    try:
        from rag.retrieve import retrieve as _impl
        results = _impl(query, k)
        # Normalise: add 'kind' alias for orchestrator compatibility
        for r in results:
            if "kind" not in r:
                r["kind"] = r.get("document_type", "doc")
        return results
    except Exception:
        # Fallback to keyword-overlap store when ChromaDB is unavailable
        from rag.store import retrieve as _fallback
        return _fallback(query, k)


def remember(record: dict) -> None:
    """Persist a resolved incident record into the memory store."""
    from rag.store import remember as _impl
    _impl(record)


def execute_action(action_type: str, params: dict) -> dict:
    """
    Executes a bounded remediation action strictly through CORTEX Execution Gateway.
    Guarantees that all callers (legacy or new) pass through the same deterministic authorization gate.
    """
    from models.proposals import ActionProposal
    from cortex.gateway import execution_gateway

    target = params.get("service", params.get("deployment", "default-service"))
    proposal = ActionProposal(
        incident_id="LEGACY-CALL",
        action_type=action_type,
        target=target,
        params=params,
        confidence=1.0,
        rationale="Executed via legacy interfaces contract facade.",
        generated_by="interfaces-facade"
    )
    result = execution_gateway.evaluate_and_execute(proposal)
    return {
        "status": "success" if result.status == "SUCCESS" else result.status.lower(),
        "action": action_type,
        "params": params,
        "result": result.output,
        "operation_id": result.operation_id
    }


def emit_event(event: dict) -> None:
    """Append a structured event to the thread-safe event bus and audit log.

    Event format: {"type": str, "payload": dict}
    """
    from tools.event_bus import emit_event as _impl
    _impl(event)
