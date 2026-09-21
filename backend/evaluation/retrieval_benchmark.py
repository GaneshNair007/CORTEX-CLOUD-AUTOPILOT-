"""Reproducible five-strategy benchmark against explicit relevance judgments."""
import argparse
import json
import math
from pathlib import Path
from statistics import mean
from time import perf_counter
from datetime import datetime, timezone

from backend.retrieval.engine import get_engine, RetrievalEngine
from backend.retrieval.models import RetrievalContext, RetrievalOptions

SCENARIOS_PATH = Path(__file__).with_name("retrieval_scenarios.json")
STRATEGIES = ("vector_only", "lexical_only", "hybrid", "hybrid_context", "full")


def rank_metrics(ids: list[str], expected: list[str]) -> dict[str, float]:
    """Compute binary relevance Hit@K, Recall@5, reciprocal rank and NDCG@5."""
    gold = set(expected)
    if not gold:
        raise ValueError("each benchmark scenario requires explicit relevance judgments")
    gains = [int(doc_id in gold) for doc_id in ids[:5]]
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(5, len(gold))))
    return {"hit_at_1": float(bool(set(ids[:1]) & gold)), "hit_at_3": float(bool(set(ids[:3]) & gold)),
            "recall_at_5": len(set(ids[:5]) & gold) / len(gold),
            "mrr": next((1 / rank for rank, doc_id in enumerate(ids, 1) if doc_id in gold), 0.),
            "ndcg_at_5": dcg / ideal}


def evaluate(engine: RetrievalEngine | None = None) -> dict:
    """Fail instead of publishing vector numbers when semantic search is unavailable."""
    engine = engine or get_engine()
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    documents = engine.repository.documents()
    known_ids = {d.id for d in documents}
    missing = {doc_id for scenario in scenarios for doc_id in scenario["expected"]} - known_ids
    if missing:
        raise ValueError(f"benchmark labels reference missing documents: {sorted(missing)}")
    start = perf_counter()
    # Record model/index warmup separately from request latency.
    engine.semantic.query("operational incident", {"schema_version": 2}, 1)
    warmup_ms = (perf_counter() - start) * 1000
    comparisons = []
    for strategy in STRATEGIES:
        details = []
        for scenario in scenarios:
            context = RetrievalContext(query_text=scenario["query"], service=scenario["service"], incident_id=scenario["id"])
            bundle = engine.retrieve(context, RetrievalOptions(enable_diversification=strategy == "full"), strategy=strategy)
            if strategy != "lexical_only" and not bundle.semantic_available:
                raise RuntimeError("semantic benchmark degraded; no valid vector comparison can be reported")
            ids = [e.id for e in bundle.evidence]
            details.append({"scenario_id": scenario["id"], "retrieved_ids": ids, "expected_ids": scenario["expected"],
                            "latency_ms": bundle.retrieval_time_ms, **rank_metrics(ids, scenario["expected"])})
        latencies = sorted(d["latency_ms"] for d in details)
        averages = {key: round(mean(d[key] for d in details), 6) for key in rank_metrics([], ["placeholder"])}
        comparisons.append({"strategy": strategy, "scenarios": len(details), **averages,
                            "mean_latency_ms": round(mean(latencies), 3),
                            "p95_latency_ms": latencies[math.ceil(.95 * len(latencies)) - 1], "scenario_details": details})
    return {"status": "completed", "timestamp": datetime.now(timezone.utc).isoformat(),
            "corpus_size": len(documents), "index_revision": engine.repository.revision,
            "embedding_model": "all-MiniLM-L6-v2", "model_index_warmup_ms": round(warmup_ms, 3),
            "label_source": "backend/evaluation/retrieval_scenarios.json",
            "limitations": ["Small curated corpus; not a scale benchmark", "Binary relevance labels are manually authored",
                            "Existing source incidents have no verified outcome provenance; trust effects are covered separately by lifecycle tests"],
            "baselines": comparisons}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "baselines": [{k: v for k, v in row.items() if k != "scenario_details"} for row in report["baselines"]]}, indent=2))


if __name__ == "__main__":
    main()
