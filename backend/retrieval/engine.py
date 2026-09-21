"""One authoritative, context-gated hybrid retrieval operation per incident."""
from datetime import datetime, timezone
from functools import lru_cache
from time import perf_counter

from backend.rag.index import ChromaIndex, SemanticUnavailable
from .config import RetrievalConfig, get_config
from .models import RetrievalContext, RetrievalOptions, EvidenceBundle
from .repository import KnowledgeRepository
from .fingerprint import build_fingerprint
from .filters import STAGES, hard_filters, stage_filter
from .semantic import semantic_query
from .lexical import lexical_query
from .hybrid import Candidate, merge
from .reranker import rerank
from .diversification import diversify
from .metrics import event


class RetrievalEngine:
    def __init__(self, repository: KnowledgeRepository, semantic: ChromaIndex, config: RetrievalConfig | None = None):
        self.repository = repository
        self.semantic = semantic
        self.config = config or get_config()

    def retrieve(self, context: RetrievalContext, options: RetrievalOptions | None = None,
                 *, strategy: str = "full", now: datetime | None = None) -> EvidenceBundle:
        """Return bounded evidence without mutating infrastructure.

        strategy is internal evaluation configuration, never a raw API filter.
        """
        if strategy not in ("full", "hybrid_context", "hybrid", "vector_only", "lexical_only"):
            raise ValueError("unknown retrieval strategy")
        start = perf_counter()
        options = options or self.config.options()
        now = now or datetime.now(timezone.utc)
        fingerprint = build_fingerprint(context)
        hard = hard_filters(context, options, now)
        bundle = EvidenceBundle(incident_id=context.incident_id, context=context, fingerprint=fingerprint,
                                index_revision=self.repository.revision)
        semantic_enabled = options.enable_semantic and strategy != "lexical_only"
        lexical_enabled = options.enable_lexical and strategy != "vector_only"
        semantic_available = semantic_enabled
        counts = {"semantic_candidate_count": 0, "lexical_candidate_count": 0}
        merged: dict[str, Candidate] = {}
        stages = list(STAGES) if strategy in ("full", "hybrid_context") else ["GENERAL_OPERATIONAL"]
        if not fingerprint.error_signatures and "EXACT_SIGNATURE" in stages:
            stages.remove("EXACT_SIGNATURE")
        if not options.allow_scope_relaxation and strategy in ("full", "hybrid_context"):
            stages = [s for s in stages if s in ("EXACT_SIGNATURE", "STRICT_CONTEXT")]
        dense_query = semantic_query(context, fingerprint) if strategy != "vector_only" else context.query_text
        sparse_query = lexical_query(context, fingerprint)
        event("retrieval_started", context.incident_id, index_revision=bundle.index_revision)
        ranked = []
        for stage in stages:
            where = stage_filter(hard, context, fingerprint, stage)
            bundle.stages_attempted.append(stage)
            bundle.filters_applied[stage] = where
            event("retrieval_stage_started", context.incident_id, stage=stage)
            if stage == "RELAXED_SERVICE" and context.service:
                bundle.relaxed_filters.append("service")
            elif stage == "RELAXED_FAILURE_FAMILY" and fingerprint.failure_mode != "unknown":
                bundle.relaxed_filters.append("failure_mode")
            elif stage == "GENERAL_OPERATIONAL" and fingerprint.technology_family:
                bundle.relaxed_filters.append("technology_primary")
            if stage.startswith("RELAXED") or stage == "GENERAL_OPERATIONAL":
                event("retrieval_stage_relaxed", context.incident_id, stage=stage)
            # Exact lexical evidence is retained; dense search follows scoped context.
            if semantic_available and stage != "EXACT_SIGNATURE":
                try:
                    dense = self.semantic.query(dense_query, where, options.candidate_k)
                    canonical = self.repository.authoritative_documents([d.id for d, _ in dense], where)
                    dense = [(canonical[d.id], score) for d, score in dense if d.id in canonical]
                    counts["semantic_candidate_count"] += len(dense)
                    merge(merged, dense, "semantic", stage)
                    event("semantic_search_completed", context.incident_id, stage=stage, count=len(dense))
                except SemanticUnavailable:
                    semantic_available = False
                    lexical_enabled = True
                    bundle.status = "DEGRADED_RETRIEVAL"
                    bundle.warnings.append("semantic index unavailable; lexical fallback used")
                    event("retrieval_degraded", context.incident_id, stage=stage, reason="semantic_unavailable")
            if lexical_enabled:
                query = " ".join(fingerprint.error_signatures) if stage == "EXACT_SIGNATURE" else sparse_query
                sparse = self.repository.lexical_search(query, where, options.candidate_k)
                counts["lexical_candidate_count"] += len(sparse)
                merge(merged, sparse, "lexical", stage)
                event("lexical_search_completed", context.incident_id, stage=stage, count=len(sparse))
            selected_strategy = strategy if options.enable_reranking else "hybrid"
            ranked = [rerank(c, context, fingerprint, self.config, now, semantic_available, lexical_enabled, selected_strategy)
                      for c in merged.values() if c.lexical > 0 or c.semantic >= self.config.min_semantic_relevance]
            ranked.sort(key=lambda c: (-c.final_score, c.id))
            event("rerank_completed", context.incident_id, stage=stage, candidate_count=len(ranked))
            # Don't declare semantic success without querying the semantic index.
            if stage != "EXACT_SIGNATURE" and len(ranked) >= options.top_k and ranked[0].final_score >= self.config.high_confidence:
                if sum(c.final_score >= self.config.min_acceptable for c in ranked) >= min(options.top_k, self.config.confident_count):
                    break
        bundle.semantic_available = semantic_available
        bundle.candidate_count = len(merged)
        bundle.retrieval_stage = bundle.stages_attempted[-1] if ranked else "NO_EVIDENCE"
        bundle.evidence = diversify(ranked, options.top_k, self.config.diversity_penalty) if options.enable_diversification else ranked[:options.top_k]
        if not bundle.evidence:
            bundle.warnings.append("no relevant evidence found")
        bundle.retrieval_time_ms = round((perf_counter() - start) * 1000, 3)
        scores = [c.final_score for c in bundle.evidence]
        bundle.metrics = {**counts, "retrieval_latency_ms": bundle.retrieval_time_ms,
                          "candidate_count": bundle.candidate_count, "final_evidence_count": len(scores),
                          "stage_reached": bundle.retrieval_stage, "scope_relaxation_count": len(bundle.relaxed_filters),
                          "best_score": max(scores, default=0), "mean_top_k_score": sum(scores) / max(1, len(scores)),
                          "semantic_available": semantic_available}
        event("retrieval_completed", context.incident_id, **bundle.metrics)
        return bundle


@lru_cache(maxsize=1)
def get_engine() -> RetrievalEngine:
    """Cache infrastructure only; contexts, options and evidence remain request-local."""
    from backend.persistence.database import engine
    from backend.rag.index import index
    from backend.rag.documents import load_sources
    repository = KnowledgeRepository(engine)
    repository.upsert(load_sources())
    return RetrievalEngine(repository, index)
