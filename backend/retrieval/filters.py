"""Server-constructed hard boundaries and progressively relaxed search scopes."""
from datetime import datetime, timezone
from typing import Any
from .models import RetrievalContext, RetrievalOptions, IncidentFingerprint

STAGES = ("EXACT_SIGNATURE", "STRICT_CONTEXT", "RELAXED_SERVICE", "RELAXED_FAILURE_FAMILY", "GENERAL_OPERATIONAL")
NEGATIVE = ("WORSE", "ROLLED_BACK", "NO_CHANGE", "PARTIALLY_RECOVERED")


def combine(clauses: list[dict[str, Any]]) -> dict[str, Any]:
    return {"$and": clauses} if len(clauses) > 1 else clauses[0]


def hard_filters(context: RetrievalContext, options: RetrievalOptions, now: datetime) -> dict[str, Any]:
    clauses: list[dict[str, Any]] = [
        {"schema_version": 2}, {"deleted": False}, {"deprecated": False},
        {"tenant_id": context.tenant_id or ""},
    ]
    types = (["incident", "memory"] if options.include_incidents else []) + (["runbook"] if options.include_runbooks else [])
    clauses.append({"document_type": {"$in": types}})
    if options.verified_only:
        clauses.append({"verified": True})
    if not options.include_failed_incidents:
        clauses.append({"memory_status": {"$nin": list(NEGATIVE)}})
    if options.max_age_days is not None:
        clauses.append({"timestamp_epoch": {"$gte": now.timestamp() - options.max_age_days * 86400}})
    if options.require_environment_match and context.environment:
        clauses.append({"$or": [{"environment": context.environment},
                                {"$and": [{"document_type": "runbook"}, {"environment_scope": "any"}]}]})
    return combine(clauses)


def stage_filter(hard: dict[str, Any], context: RetrievalContext, fingerprint: IncidentFingerprint, stage: str) -> dict[str, Any]:
    scope: list[dict[str, Any]] = [hard]
    if stage in ("STRICT_CONTEXT", "RELAXED_SERVICE", "RELAXED_FAILURE_FAMILY") and fingerprint.technology_family:
        scope.append({"technology_primary": {"$in": fingerprint.technology_family}})
    if stage in ("STRICT_CONTEXT", "RELAXED_SERVICE") and fingerprint.failure_mode not in (None, "unknown"):
        scope.append({"failure_mode": fingerprint.failure_mode})
    if stage == "STRICT_CONTEXT" and context.service:
        # A preferred first scope, never a permanent boundary. Runbooks can be shared.
        scope.append({"$or": [{"service": context.service}, {"document_type": "runbook"}]})
    return combine(scope)
