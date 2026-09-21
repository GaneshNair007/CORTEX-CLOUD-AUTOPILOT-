"""Explainable weighted scoring with no paid model calls."""
import json
from datetime import datetime
from .config import RetrievalConfig
from .hybrid import Candidate
from .models import RetrievalContext, IncidentFingerprint, EvidenceCandidate
from .normalization import tokens, normalize
from .recency import recency_score
from .trust import trust_scores


def overlap(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(1, len(left))


def rerank(candidate: Candidate, context: RetrievalContext, fingerprint: IncidentFingerprint,
           config: RetrievalConfig, now: datetime, semantic_enabled: bool, lexical_enabled: bool,
           strategy: str = "full") -> EvidenceCandidate:
    meta = candidate.document.metadata
    techs = set(str(meta.get("technologies_csv", "")).split(",")) - {""}
    errors = set(str(meta.get("error_signatures_csv", "")).split(",")) - {""}
    technology = overlap(set(fingerprint.technology_family), techs)
    error = overlap(set(fingerprint.error_signatures), errors)
    failure = float(fingerprint.failure_mode not in (None, "unknown") and fingerprint.failure_mode == meta.get("failure_mode"))
    service = float(bool(context.service) and context.service == meta.get("service"))
    if not service and context.service_family and context.service_family == meta.get("service_family"):
        service = .6
    dep_names = set(str(meta.get("dependencies_csv", "")).split(",")) | {str(meta.get("service", ""))}
    dependency = max((context.dependency_weights.get(dep, .7) for dep in dep_names & set(context.dependencies)), default=0.)
    dependency = max(dependency, overlap(set(map(normalize, context.dependency_types)),
                                         set(map(normalize, str(meta.get("dependency_types_csv", "")).split(",")))))
    historical_telemetry = json.loads(str(meta.get("telemetry_signature_json", "{}")))
    meaningful = {k: v for k, v in fingerprint.telemetry_signature.items() if v in ("high", "critical")}
    telemetry = sum(historical_telemetry.get(k) == v for k, v in meaningful.items()) / max(1, len(meaningful))
    service_dependency = max(service, dependency * .7, telemetry * .4)
    recency = recency_score(meta, now, config)
    trust, outcome = trust_scores(meta, config)
    scores = {"semantic": candidate.semantic, "lexical": candidate.lexical, "failure_mode": failure,
              "technology": technology, "error": error, "service_dependency": service_dependency,
              "trust_outcome": .7 * trust + .3 * outcome, "recency": recency}
    weights = dict(config.weights)
    if strategy in ("vector_only", "lexical_only", "hybrid"):
        weights = {"semantic": 1., "lexical": 1.} if strategy == "hybrid" else {"semantic" if strategy == "vector_only" else "lexical": 1.}
    elif strategy == "hybrid_context":
        weights.pop("trust_outcome")
        weights.pop("recency")
    if not semantic_enabled:
        weights.pop("semantic", None)
    if not lexical_enabled:
        weights.pop("lexical", None)
    final = sum(scores[k] * w for k, w in weights.items()) / (sum(weights.values()) or 1)
    why = []
    if technology:
        why.append("same technology: " + ", ".join(sorted(set(fingerprint.technology_family) & techs)))
    if failure:
        why.append("same failure mode: " + str(fingerprint.failure_mode).replace("_", " "))
    if error:
        why.append("matching exact signal: " + ", ".join(sorted(set(fingerprint.error_signatures) & errors)))
    if service:
        why.append("same service" if service == 1 else "same service family")
    if dependency:
        why.append("matching direct dependency or dependency type")
    if telemetry:
        why.append("matching elevated telemetry categories")
    if context.environment and context.environment == meta.get("environment"):
        why.append("same environment")
    if meta.get("verified"):
        status = meta.get("memory_status")
        why.append("verified historical recovery" if status == "VERIFIED_RECOVERED" else f"verified outcome: {status}")
        if status in ("WORSE", "ROLLED_BACK", "NO_CHANGE"):
            why.append("NEGATIVE EVIDENCE: this action did not restore service; do not repeat it blindly")
    else:
        why.append("source is unverified; use as a hypothesis, not proof of recovery")
    timestamp = meta.get("resolved_at_epoch") or meta.get("timestamp_epoch")
    if timestamp:
        why.append(f"recorded {max(0, int((now.timestamp() - float(timestamp)) / 86400))} days ago")
    if candidate.semantic:
        why.append("semantic similarity")
    if candidate.lexical:
        why.append("lexical technical-token match")
    return EvidenceCandidate(id=candidate.document.id, document_type=str(meta["document_type"]),
                             title=str(meta.get("title", candidate.document.id)), text=candidate.document.text,
                             metadata=meta, semantic_score=candidate.semantic, lexical_score=candidate.lexical,
                             context_score=(failure + technology + error + service_dependency) / 4,
                             recency_score=recency, trust_score=trust, outcome_score=outcome,
                             final_score=max(0., min(1., final)), retrieval_stage=candidate.stage,
                             why_retrieved=why, score_components={**scores, "service": service, "dependency": dependency, "telemetry": telemetry, "final": final})
