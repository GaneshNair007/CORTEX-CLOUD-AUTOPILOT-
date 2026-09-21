"""Dense candidate generation uses the existing MiniLM/cosine Chroma index."""
from .models import RetrievalContext, IncidentFingerprint


def semantic_query(context: RetrievalContext, fingerprint: IncidentFingerprint) -> str:
    return " ".join(filter(None, [context.query_text, context.service,
                                 " ".join(fingerprint.technology_family),
                                 (fingerprint.failure_mode or "").replace("_", " "),
                                 " ".join(fingerprint.error_signatures)]))
