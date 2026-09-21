"""Stable fingerprints derived without model calls."""
from .models import IncidentFingerprint, RetrievalContext
from .normalization import error_signatures, failure_mode, normalize, technologies


def build_fingerprint(context: RetrievalContext) -> IncidentFingerprint:
    text = " ".join([context.query_text, *context.error_codes, *context.exception_types])
    tech = sorted(set(map(normalize, context.technologies)) | set(technologies(text)))
    resource = context.resource_type
    if not resource and any(t in tech for t in ("postgresql", "mysql", "pgbouncer")):
        resource = "database"
    errors = error_signatures(text)
    telemetry = {k: str(v) for k, v in context.telemetry_signature.items() if v is not None}
    return IncidentFingerprint(
        service_family=context.service_family, resource_family=resource,
        technology_family=tech, failure_mode=normalize(context.failure_mode) if context.failure_mode else failure_mode(text),
        symptom_signatures=sorted(set(errors + [f"{k}_{v}" for k, v in telemetry.items() if v in ("high", "critical")])),
        error_signatures=errors, telemetry_signature=telemetry,
        dependency_signature=sorted(context.dependencies),
        change_signature=context.deployment_version or ("recent_change" if context.recent_change else None),
    )
