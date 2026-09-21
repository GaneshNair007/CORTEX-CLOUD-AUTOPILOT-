# Context-gated hierarchical incident retrieval

## Problem and migration

The original string-only vector search discarded operational metadata, retrieved twice in the main diagnosis path, and learned into JSONL while semantic retrieval used Chroma. The upgraded domain extends the existing control plane. SQL owns canonical knowledge/lifecycle records; Chroma remains the single semantic index using `all-MiniLM-L6-v2` with cosine distance. SQLite FTS5 provides lexical BM25 without another service.

```text
Incident + topology + available telemetry
  -> ContextBuilder -> RetrievalContext -> IncidentFingerprint
  -> hard boundaries -> staged semantic + lexical candidates
  -> ID merge -> deterministic scoring -> diversification
  -> one EvidenceBundle -> IncidentAgent -> proposal
  -> CORTEX gateway -> executor -> verifier
  -> SQL canonical memory/outbox -> Chroma upsert
```

Retrieval is evidence, never authorization. Missing context stays unknown. Neither fingerprinting nor reranking needs an LLM. Retrieved prose is explicitly untrusted data in the agent prompt. Only final selected evidence is sent to the model.

## Models and metadata

`backend/retrieval/models.py` defines `RetrievalContext`, `IncidentFingerprint`, `RetrievalOptions`, `EvidenceCandidate`, `EvidenceBundle`, `EvidenceRequest` and `IndexDocument`. Mutable values use factories. External context hints forbid unknown fields and raw database filters. Top-k is 1–20; candidate-k is 1–200 and must cover top-k. A positive optional maximum age is capped at 36,500 days. Defaults retain old records and rank recency rather than silently excluding them.

Schema v2 flat metadata includes document type, service/family, environment/scope, provider/region, resource type, primary technology and canonical technology CSV, failure mode, error signatures, dependencies, severity, timestamp epochs, source filename, lifecycle status, verification, trust, deprecation and deletion. Optional unavailable attributes are not invented. Runbooks have their own type/scope/verification and slower recency decay. Source incidents are not verified merely because a historical resolution is written down.

Deterministic aliases normalize PostgreSQL/PG/postgres and Kubernetes/k8s/kube. Signature extraction handles HTTP codes, SQLSTATE 53300, CrashLoopBackOff, OOMKilled and common connection errors. Topology supplies direct dependencies and lower-weight dependents. Telemetry categories use configured thresholds and service SLOs when available.

## Search scopes and hard boundaries

Hard constraints always preserve schema v2, tenant boundary (empty tenant for the current single-tenant app), visibility, document types, and explicit verified/environment/age options. Tenant hints are internal readiness, not an implemented public multi-tenant security system.

| Stage | Candidate scope |
| --- | --- |
| EXACT_SIGNATURE | Lexical exact operational signatures within hard boundaries |
| STRICT_CONTEXT | Primary technology/failure family and preferred same service, allowing shared runbooks |
| RELAXED_SERVICE | Same technology/failure family across services |
| RELAXED_FAILURE_FAMILY | Same technology; failure constraint removed |
| GENERAL_OPERATIONAL | Related operational knowledge within unchanged hard boundaries |

Service is not a permanent hard filter. Candidates from earlier stages are retained. Search can stop when it has top-k candidates, best score ≥0.82 and at least min(top-k, 3) scores ≥0.70. All thresholds are configuration, not guarantees of calibrated probability. Explicit `allow_scope_relaxation=false` stops widening. Every bundle reports attempted scopes and relaxed fields.

Each enabled channel requests candidate-k. Chroma results are rechecked against authoritative SQL metadata, so a stale semantic copy cannot restore deleted or restricted evidence. Candidates merge by stable document ID. No source file scan happens per query.

## Explainable ranking

Default final score (all components in [0,1]):

```text
0.35 semantic + 0.15 failure + 0.10 technology + 0.10 exact error
+ 0.10 service/dependency/telemetry + 0.08 lexical
+ 0.07 (0.70 knowledge trust + 0.30 remediation outcome) + 0.05 recency
```

Disabled channels have their weights removed and remaining weights normalized. Defaults and sum/bound checks live in `config.py`. Service family and dependency similarity receive partial credit. Recency uses an exponential half-life of 180 days for incidents and 730 for runbooks. Token-overlap redundancy penalties diversify relevant results without forcing unrelated runbooks. Internal score components support debugging; public results expose component scores and human-readable reasons without internal weight dumps.

Knowledge trust and remediation success are separate: a verified WORSE record is useful evidence that an action failed, not an endorsement. Negative evidence stays searchable unless explicitly excluded. Unverified sources are visibly labeled as hypotheses, not recovery proof.

## Verified learning and recovery

The main pipeline builds exactly one bundle and passes it to `IncidentAgent.handle_incident(..., evidence=bundle)`. Legacy direct agent callers can retrieve internally when no bundle is supplied.

Before authorization, SQL persists the original context and diagnosis hypothesis. The gateway learns after a conclusive verification, including actions approved later. Command success alone never resolves the incident. The writer checks operation, proposal, incident and target binding; dry runs, unknown verification and invalid recovered SLO metrics cannot become trusted memories.

Verified recovery sets `VERIFIED_RECOVERED` and trusted=true. Partial/no-change/worse outcomes remain accurate negative or partial evidence, with trusted-remediation=false where appropriate. Sandbox verification explicitly stores environment=sandbox and simulated=true. A stable incident/proposal memory ID prevents duplicate appends. SQL transaction/outbox precedes Chroma upsert; semantic failure leaves PENDING, but lexical evidence remains available. Replay is explicit or performed at startup, not a distributed queue.

## API and compatibility

`POST /api/v1/evidence/retrieve` accepts:

```json
{
  "query": "HTTP 503 PostgreSQL connection pool saturation",
  "incident_id": "INC-1042",
  "context": {"service": "payment-api", "technologies": ["postgresql"], "environment": "production"},
  "options": {"top_k": 5, "candidate_k": 30, "verified_only": false}
}
```

The response includes results, fingerprint, stage, attempted stages, filters, warnings, semantic availability, timing and revision. Results retain id/document_type/title/text/tags/score/filename and add final/component scores, why_retrieved and available outcome fields. Viewer authentication is required by default. Production clients cannot submit raw Chroma where clauses or enable internal debug weights.

`POST /api/rag/retrieve` with `{ "query": "database timeout", "k": 3 }` and Python `retrieve("database timeout", 3)` remain supported through the domain facade. The old endpoint is deprecated for new integrations, not removed.

Semantic outages return `DEGRADED_RETRIEVAL` and “semantic index unavailable; lexical fallback used.” Empty searches return empty evidence with a warning. They never fabricate documents.

## Operations and evaluation

From the repository root, with the API stopped for migration:

```powershell
.venv\Scripts\python.exe -m backend.rag.rebuild_index
.venv\Scripts\python.exe -m backend.retrieval.memory_writer
.venv\Scripts\python.exe -m backend.evaluation.retrieval_benchmark --output docs/retrieval_evaluation.json
.venv\Scripts\python.exe -m pytest backend/tests -q
```

Rebuild inspects the existing collection, imports otherwise orphaned documents as unverified, builds a shadow, verifies unique IDs, and retains the old collection as a backup before switching. Canonical files and SQL memories survive. Do not run migration concurrently with live writes.

The benchmark computes Hit@1, Hit@3, Recall@5, MRR, NDCG@5 and latency for vector-only, lexical-only, hybrid, hybrid/context and full ranking. Model/index warmup is separate. Labels are manually authored across 20 scenarios; this is not a scale or unbiased research benchmark. Semantic outage fails the comparison instead of inventing vector metrics.

Structured retrieval events report incident IDs, stage, counts, relaxation, score summaries, availability and latency, never credentials or full incident payloads. Cached infrastructure is shared under locks; request context is local. No result cache is needed at current size. Index revision supports later cache invalidation. SQL lexical queries require SQLite FTS5; PostgreSQL and distributed writers are not implemented.
