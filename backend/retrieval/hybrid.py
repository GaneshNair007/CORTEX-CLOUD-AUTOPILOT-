"""Merge channel candidates by stable document identity."""
from dataclasses import dataclass
from .models import IndexDocument


@dataclass
class Candidate:
    document: IndexDocument
    stage: str
    semantic: float = 0
    lexical: float = 0


def merge(target: dict[str, Candidate], results: list[tuple[IndexDocument, float]], channel: str, stage: str) -> None:
    for document, score in results:
        candidate = target.setdefault(document.id, Candidate(document=document, stage=stage))
        setattr(candidate, channel, max(getattr(candidate, channel), score))
