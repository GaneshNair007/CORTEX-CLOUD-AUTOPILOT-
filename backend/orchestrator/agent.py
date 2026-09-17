"""Incident-response agent loop: retrieve -> hypothesize -> self-critique ->
confidence-gated action -> memory write-back.

Calls ONLY the frozen contract functions from rag/store.py and tools/actions.py
(signatures declared in interfaces.py).
"""

import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm.client import LLMClient  # noqa: E402
from interfaces import emit_event, remember, retrieve  # noqa: E402
from models.proposals import ActionProposal  # noqa: E402

CONFIDENCE_AUTO_EXECUTE = 0.6  # below this we only recommend, never act

# risk levels for the mock action set; high-risk always requires human approval
ACTION_RISK = {
    "restart_service": "low",
    "create_ticket": "low",
    "generate_postmortem": "low",
    "rollback_deployment": "high",
}

SYSTEM_PROMPT = (
    "You are an on-prem incident-response copilot for SRE teams. Be concise, "
    "structured, and evidence-driven. Never invent metrics not present in the "
    "provided context."
)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _extract_confidence(text: str, default: float = 0.5) -> float:
    """Extract a confidence score from LLM output.

    Robust to real-model quirks: markdown formatting (**bold**),
    varied labels (score/level), percentages, and buried-in-sentence values.
    """
    # Strip markdown bold/italic/code so "**CONFIDENCE**: 0.7" parses
    cleaned = re.sub(r'[*_`]', '', text)

    # 1. Explicit labeled pattern (highest priority, last match wins)
    #    CONFIDENCE: 0.72 | REVISED CONFIDENCE = 0.66 | Confidence Score: 0.8
    explicit = re.findall(
        r'(?:REVISED\s+)?CONFIDENCE(?:\s+(?:SCORE|LEVEL))?'
        r'\s*[:=\s]\s*'
        r'([01](?:\.\d+)?|\.\d+)',
        cleaned, re.IGNORECASE,
    )
    if explicit:
        try:
            return max(0.0, min(1.0, float(explicit[-1])))
        except ValueError:
            pass

    # 2. Percentage after a confidence label: "CONFIDENCE: 72%"
    pct = re.findall(
        r'(?:REVISED\s+)?CONFIDENCE(?:\s+(?:SCORE|LEVEL))?'
        r'\s*[:=\s]\s*(\d{1,3})\s*%',
        cleaned, re.IGNORECASE,
    )
    if pct:
        try:
            return max(0.0, min(1.0, float(pct[-1]) / 100.0))
        except ValueError:
            pass

    # 3. Fallback: any 0.XX on a line containing "confiden" (last match wins)
    for line in reversed(cleaned.splitlines()):
        if 'confiden' in line.lower():
            nums = re.findall(r'\b([01]\.\d+)\b', line)
            if nums:
                try:
                    return max(0.0, min(1.0, float(nums[-1])))
                except ValueError:
                    pass

    return default


try:
    from llm.router import IncidentRouter
except ImportError:
    IncidentRouter = None


class IncidentAgent:
    def __init__(self, llm: LLMClient | None = None, adaptive_routing: bool | None = None):
        self.llm = llm or LLMClient()
        if adaptive_routing is None:
            adaptive_routing = os.environ.get("ENABLE_ADAPTIVE_ROUTING", "0") == "1"
        self.adaptive_routing = adaptive_routing
        self.router = IncidentRouter() if (adaptive_routing and IncidentRouter) else None

    def handle_incident(self, incident: dict) -> dict:
        """Run the full pipeline for one incident dict {"id", "title", "description"}."""
        emit_event({"type": "start", "payload": {
            "incident_id": incident["id"], "llm_mode": self.llm.mode}})

        # 1. Retrieve relevant runbooks / past incidents
        query = f"{incident['title']} {incident['description']}"
        docs = retrieve(query, k=3)
        emit_event({"type": "retrieve", "payload": {
            "incident_id": incident["id"], "doc_ids": [d["id"] for d in docs]}})

        if self.router:
            complexity, selected_model, routing_ms = self.router.classify_complexity(incident, docs)
            emit_event({"type": "routing", "payload": {
                "incident_id": incident["id"],
                "complexity": complexity,
                "selected_model": selected_model,
                "routing_latency_ms": routing_ms,
            }})
        context = "\n\n".join(
            f"[{d.get('kind', d.get('document_type', 'doc'))}] {d['title']}\n{d['text']}"
            for d in docs
        ) or "(no relevant documents found)"

        # 2. Root-cause hypothesis
        hyp = self.llm.generate(
            f"INCIDENT: {incident['title']}\n{incident['description']}\n\n"
            f"RELEVANT CONTEXT:\n{context}\n\n"
            "Respond in this exact format (no preamble, no extra sections):\n\n"
            "HYPOTHESIS: <2-4 sentences: root cause with evidence from the "
            "context above>\n\n"
            "CONFIDENCE: <a single decimal 0.0-1.0>\n",
            system=SYSTEM_PROMPT,
        )
        hypothesis = hyp["text"].strip()
        confidence = _extract_confidence(hypothesis)
        emit_event({"type": "hypothesis", "payload": {
            "incident_id": incident["id"], "confidence": confidence}})

        # 3. Self-critique: actively try to disprove the hypothesis before acting
        crit = self.llm.generate(
            f"INCIDENT: {incident['title']}\n{incident['description']}\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"PROPOSED HYPOTHESIS:\n{hypothesis}\n\n"
            "You are a skeptical senior SRE reviewing this hypothesis. "
            "Respond in this exact format (no preamble):\n\n"
            "COUNTER-EVIDENCE: <1-2 sentences: what weakens this hypothesis>\n"
            "ALTERNATIVE CAUSE: <1 sentence: a different plausible root cause>\n"
            "VERDICT: <1 sentence: does the hypothesis survive?>\n\n"
            "REVISED CONFIDENCE: <a single decimal 0.0-1.0>\n",
            system=SYSTEM_PROMPT,
        )
        critique = crit["text"].strip()
        revised = _extract_confidence(critique, default=confidence)
        emit_event({"type": "self_critique", "payload": {
            "incident_id": incident["id"], "revised_confidence": revised}})

        # 4. Action Proposal Generation & Gateway Authorization
        action_type, params = self._decide_action(incident, hypothesis)
        service = incident.get("service", "payments-api")

        proposal = ActionProposal(
            incident_id=incident["id"],
            action_type=action_type,
            target=service,
            params=params,
            confidence=revised,
            evidence_ids=[d["id"] for d in docs],
            rationale=f"Hypothesis: {hypothesis[:200]}. Self-critique confidence: {revised:.2f}",
            generated_by="cortex-agent"
        )
        emit_event({"type": "proposal_created", "payload": proposal.model_dump(mode="json")})

        # CRITICAL INVARIANT: Agent only produces ActionProposal; execution belongs to Gateway
        action_result = {
            "status": "PROPOSED",
            "result": "PROPOSED",
            "proposal": proposal.model_dump(mode="json"),
            "action": action_type,
            "params": params
        }
        emit_event({"type": "proposal_generated", "payload": {
            "incident_id": incident["id"], "action": action_type,
            "proposal": proposal.model_dump(mode="json")}})

        # 5. Memory write-back so future similar incidents resolve faster
        record = {
            "id": incident["id"],
            "title": incident["title"],
            "description": incident["description"],
            "hypothesis": hypothesis,
            "critique": critique,
            "confidence": revised,
            "action": {"type": action_type, "params": params, "result": action_result},
            "resolved_at": _now(),
        }
        remember(record)
        emit_event({"type": "remember", "payload": {"incident_id": incident["id"]}})

        return record

    def _decide_action(self, incident: dict, hypothesis: str) -> tuple[str, dict]:
        """Heuristic action selection (native tool-calling is a stretch goal)."""
        text = f"{incident['description']} {hypothesis}".lower()
        service = incident.get("service", "payments-api")
        if "rollback" in text or "bad deploy" in text or "revert" in text:
            return "rollback_deployment", {"deployment": service, "revision": "previous stable version"}
        if any(w in text for w in ("restart", "pool exhaust", "connection pool",
                                   "memory leak", "hung")):
            return "restart_service", {"service": service}
        return "create_ticket", {"service": service,
                                 "summary": incident["title"],
                                 "title": incident["title"],
                                 "hypothesis": hypothesis[:400]}
