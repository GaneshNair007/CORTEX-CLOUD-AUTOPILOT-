"""Validated public retrieval contracts and internal index documents."""
from datetime import datetime
from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Label = Annotated[str, Field(max_length=256)]
Score = Annotated[float, Field(ge=0, le=1)]


class ContextHints(BaseModel):
    """Only allow typed context fields, never arbitrary database filters."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    service: Label | None = None
    service_family: Label | None = None
    environment: Label | None = None
    severity: Label | None = None
    provider: Label | None = None
    region: Label | None = None
    availability_zone: Label | None = None
    cluster: Label | None = None
    namespace: Label | None = None
    resource_type: Label | None = None
    resource_id: Label | None = None
    technologies: list[Label] = Field(default_factory=list, max_length=32)
    error_codes: list[Label] = Field(default_factory=list, max_length=32)
    exception_types: list[Label] = Field(default_factory=list, max_length=32)
    failure_mode: Label | None = None
    dependencies: list[Label] = Field(default_factory=list, max_length=64)
    dependency_types: list[Label] = Field(default_factory=list, max_length=32)
    deployment_version: Label | None = None
    recent_change: bool | None = None
    telemetry_signature: dict[Label, float | str | bool | None] = Field(default_factory=dict, max_length=32)
    timestamp: datetime | None = None


class RetrievalContext(ContextHints):
    incident_id: Label | None = None
    query_text: str = Field(min_length=1, max_length=12000)
    # Internal only: must eventually come from authenticated identity, never user filters.
    tenant_id: Label | None = None
    dependency_weights: dict[str, float] = Field(default_factory=dict)


class IncidentFingerprint(BaseModel):
    service_family: str | None = None
    resource_family: str | None = None
    technology_family: list[str] = Field(default_factory=list)
    failure_mode: str | None = None
    symptom_signatures: list[str] = Field(default_factory=list)
    error_signatures: list[str] = Field(default_factory=list)
    telemetry_signature: dict[str, str] = Field(default_factory=dict)
    dependency_signature: list[str] = Field(default_factory=list)
    change_signature: str | None = None


class RetrievalOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top_k: int = Field(default=5, ge=1, le=20, strict=True)
    candidate_k: int = Field(default=30, ge=1, le=200, strict=True)
    max_age_days: int | None = Field(default=None, ge=1, le=36500, strict=True)
    verified_only: bool = False
    include_incidents: bool = True
    include_runbooks: bool = True
    include_failed_incidents: bool = True
    enable_lexical: bool = True
    enable_semantic: bool = True
    enable_reranking: bool = True
    enable_diversification: bool = True
    allow_scope_relaxation: bool = True
    require_environment_match: bool = False

    @model_validator(mode="after")
    def valid_limits(self):
        if self.candidate_k < self.top_k:
            raise ValueError("candidate_k must be >= top_k")
        if not self.enable_semantic and not self.enable_lexical:
            raise ValueError("at least one retrieval channel must be enabled")
        if not self.include_incidents and not self.include_runbooks:
            raise ValueError("at least one document type must be enabled")
        return self


class EvidenceCandidate(BaseModel):
    id: str
    document_type: str
    title: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    semantic_score: Score = 0
    lexical_score: Score = 0
    context_score: Score = 0
    recency_score: Score = 0
    trust_score: Score = 0
    outcome_score: Score = 0
    final_score: Score = 0
    retrieval_stage: str
    why_retrieved: list[str] = Field(default_factory=list)
    score_components: dict[str, float] = Field(default_factory=dict, exclude=True)

    def public_result(self) -> dict[str, Any]:
        """Keep the existing UI contract while adding explainable component scores."""
        result = self.model_dump(exclude={"metadata"})
        result.update(score=self.final_score, kind=self.document_type,
                      tags=[t.strip() for t in str(self.metadata.get("tags", "")).split(",") if t.strip()],
                      filename=self.metadata.get("filename", ""))
        for key in ("verification_outcome", "historical_action", "rollback_performed", "slo_recovered", "mttr", "memory_status", "simulated", "environment"):
            if key in self.metadata:
                result[key] = self.metadata[key]
        return result


class EvidenceBundle(BaseModel):
    incident_id: str | None = None
    context: RetrievalContext
    fingerprint: IncidentFingerprint
    evidence: list[EvidenceCandidate] = Field(default_factory=list)
    retrieval_stage: str = "NO_EVIDENCE"
    stages_attempted: list[str] = Field(default_factory=list)
    candidate_count: int = 0
    retrieval_time_ms: float = 0
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    relaxed_filters: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: str = "OK"
    semantic_available: bool = True
    index_revision: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)

    def public_response(self) -> dict[str, Any]:
        result = self.model_dump(exclude={"evidence", "context", "metrics"})
        result["results"] = [e.public_result() for e in self.evidence]
        return result


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=12000)
    incident_id: Label | None = None
    context: ContextHints = Field(default_factory=ContextHints)
    options: RetrievalOptions | None = None


class IndexDocument(BaseModel):
    id: str
    text: str
    metadata: dict[str, str | int | float | bool]
