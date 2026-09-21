"""Smooth half-life decay; unknown dates receive a neutral score."""
import math
from datetime import datetime
from typing import Any
from .config import RetrievalConfig


def recency_score(metadata: dict[str, Any], now: datetime, config: RetrievalConfig) -> float:
    timestamp = metadata.get("resolved_at_epoch") or metadata.get("timestamp_epoch")
    if not timestamp:
        return .5
    days = max(0., (now.timestamp() - float(timestamp)) / 86400)
    half_life = config.runbook_half_life if metadata.get("document_type") == "runbook" else config.recency_half_life
    return math.exp(-math.log(2) * days / half_life)
