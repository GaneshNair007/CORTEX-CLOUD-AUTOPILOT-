"""Technical token representations for the SQL FTS5 BM25 adapter."""
from .models import RetrievalContext, IncidentFingerprint


def lexical_query(context: RetrievalContext, fingerprint: IncidentFingerprint) -> str:
    return " ".join([context.query_text, *fingerprint.technology_family, *fingerprint.error_signatures,
                     fingerprint.failure_mode or "", *context.exception_types, *context.error_codes])
