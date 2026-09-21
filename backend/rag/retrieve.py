"""Backward-compatible retrieval facade; structured callers use RetrievalEngine."""
from backend.retrieval.models import RetrievalContext, RetrievalOptions, EvidenceBundle


def retrieve(query: str | RetrievalContext, k: int | RetrievalOptions = 5) -> list[dict] | EvidenceBundle:
    """Support retrieve(text, k) and retrieve(context, options) during migration."""
    from backend.retrieval.engine import get_engine
    if isinstance(query, RetrievalContext):
        options = k if isinstance(k, RetrievalOptions) else RetrievalOptions(top_k=k, candidate_k=max(30, k))
        return get_engine().retrieve(query, options)
    if not isinstance(query, str):
        raise ValueError("query must be a string or RetrievalContext")
    options = RetrievalOptions(top_k=k, candidate_k=max(30, k))
    bundle = get_engine().retrieve(RetrievalContext(query_text=query), options)
    return [candidate.public_result() for candidate in bundle.evidence]
