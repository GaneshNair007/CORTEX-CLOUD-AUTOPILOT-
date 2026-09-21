"""Strict, bounded model output contracts. Text is never executable authority."""
import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class CandidateAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["restart_service", "scale_service", "rollback_deployment", "create_ticket"]
    params: dict[str, Any] = Field(default_factory=dict)


class DiagnosisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_cause: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    alternative_causes: list[str] = Field(default_factory=list, max_length=5)
    action: CandidateAction


class CritiqueOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    critique: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    verdict: Literal["SUPPORTED", "UNCERTAIN", "REJECTED"]


def parse_output(text: str, model):
    """Accept JSON or a single JSON fence, never extract a plausible fragment."""
    value = text.strip()
    if value.startswith("```json\n") and value.endswith("```"):
        value = value[8:-3].strip()
    if len(value) > 16000:
        raise ValueError("Model response exceeds contract limit")
    return model.model_validate(json.loads(value))
