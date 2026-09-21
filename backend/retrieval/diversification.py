"""Lightweight MMR: penalize near duplicates, never insert irrelevant documents."""
from .models import EvidenceCandidate
from .normalization import tokens


def diversify(candidates: list[EvidenceCandidate], top_k: int, penalty: float) -> list[EvidenceCandidate]:
    remaining = list(candidates)
    selected: list[EvidenceCandidate] = []
    features = {c.id: set(tokens(c.title + " " + c.text[:1200])) for c in candidates}
    while remaining and len(selected) < top_k:
        def utility(candidate: EvidenceCandidate) -> float:
            similarity = max((len(features[candidate.id] & features[s.id]) / max(1, len(features[candidate.id] | features[s.id])) for s in selected), default=0.)
            return candidate.final_score - penalty * similarity
        best = max(remaining, key=lambda c: (utility(c), c.final_score, c.id))
        selected.append(best)
        remaining.remove(best)
    return selected
