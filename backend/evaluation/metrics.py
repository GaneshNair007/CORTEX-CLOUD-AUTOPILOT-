"""
CORTEX Cloud Autopilot — Evaluation Metrics & Baseline Comparison Engine
Calculates standard evaluation metrics across retrieval, diagnosis, safety, and control reliability.
"""

from typing import List, Dict, Any, Tuple
import math


def calculate_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    """Calculates Recall@k for retrieved evidence documents."""
    if not expected_ids:
        return 1.0
    top_k = retrieved_ids[:k]
    matched = set(top_k) & set(expected_ids)
    return len(matched) / len(expected_ids)


def calculate_mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
    """Calculates Mean Reciprocal Rank (MRR) for the first relevant document."""
    expected_set = set(expected_ids)
    for idx, doc_id in enumerate(retrieved_ids, 1):
        if doc_id in expected_set:
            return 1.0 / idx
    return 0.0


def calculate_safety_metrics(
    total_actions: int,
    unsafe_proposed: int,
    unsafe_blocked: int,
    safe_proposed: int,
    safe_blocked: int
) -> Dict[str, float]:
    """
    Computes safety authorization metrics:
    - Unsafe Prevention Rate (Recall on unsafe actions)
    - False Block Rate (Over-blocking of safe actions)
    - False Allow Rate (Critical safety failure)
    """
    unsafe_prevention_rate = (unsafe_blocked / unsafe_proposed) if unsafe_proposed > 0 else 1.0
    false_allow_rate = ((unsafe_proposed - unsafe_blocked) / unsafe_proposed) if unsafe_proposed > 0 else 0.0
    false_block_rate = (safe_blocked / safe_proposed) if safe_proposed > 0 else 0.0

    return {
        "unsafe_prevention_rate": round(unsafe_prevention_rate * 100, 2),
        "false_allow_rate": round(false_allow_rate * 100, 2),
        "false_block_rate": round(false_block_rate * 100, 2)
    }


def get_system_baseline_comparison() -> dict:
    """Deprecated: measured baselines come from retrieval_benchmark.evaluate."""
    return {}
