# Retrieval implementation report

Local implementation and verification passed. External NVIDIA inference and hosted backend acceptance remain separate, pending checks; this report does not declare the full production system complete.

| Feature | Before | After / implementation | Test | Status |
| --- | --- | --- | --- | --- |
| Structured context | String query | retrieval/models.py, context_builder.py, fingerprint.py | normalization_fingerprint_and_topology | PASS |
| Metadata gate | Global vector candidates | schema v2 and server-only filters.py | boundaries_not_relaxed | PASS |
| Cross-service scope | No staged contract | strict → relaxed service → failure → general | same_service_ranks_first_and_cross_service_survives | PASS |
| Hybrid search | Vector or separate keyword fallback | Chroma + SQLite FTS BM25, hybrid.py | exact_signature_boost / wrong_technology | PASS |
| Explainable ranking | Similarity score | reranker.py, trust.py, recency.py | recency / verified_outcome / negative_evidence | PASS |
| Single retrieval | Pipeline plus agent queries | one EvidenceBundle passed explicitly | pipeline_retrieves_once | PASS |
| Learn loop | JSONL separate from Chroma | SQL verified memory/outbox + idempotent upsert | real_chroma_migration_and_learn_loop | PASS |
| Outage | Weak fallback visibility | explicit DEGRADED_RETRIEVAL, lexical fallback | no_evidence_and_explicit_semantic_outage | PASS |
| Compatibility | Legacy API | existing facade + structured endpoint | legacy_facade_and_apis | PASS |
| Bounded inputs | Small implicit top-k | typed limits/config validation | invalid_options / invalid_configuration | PASS |
| Failed actions | Inconsistent resolution | WORSE retained; compensation verified separately | verified_worse_action_retains_negative_memory | PASS |
| Evaluation | Demonstration metrics | five computed strategies / 20 labels | retrieval_benchmark CLI | PASS |

Test references are in backend/tests/test_context_retrieval.py and test_final_integration.py. Full backend run: 164 passed, 0 failed, 0 skipped, with 9 dependency/legacy-setting deprecation warnings. Real HTTP/SQL/Chroma API demonstration: 17 checks passed (docs/local_demo_verification.json).

## Index migration performed

Actual latest rebuild: 20 incidents, 15 runbooks, 1 preserved learned memory, total 36; schema v2; revision 36. The initial old schema v1 was migrated earlier; the final idempotent rebuild detected v2 and retained its previous collection as sre_backup_74f047a139a34fdfa4a7463e957e0a72. Sources were preserved. Isolated demo starts with 35 source documents and finishes with 37 after two learned memories.

## Computed evaluation

Source: docs/retrieval_evaluation.json; 20 labeled scenarios, 36 documents, MiniLM. Model/index warmup: 19,285.473 ms, excluded from the following request latencies.

| Strategy | Hit@1 | Hit@3 | Recall@5 | MRR | NDCG@5 | p95 ms |
| --- | --- | --- | --- | --- | --- | --- |
| vector_only | 0.950 | 1.000 | 1.000 | 0.9750 | 0.9628 | 47.37 |
| lexical_only | 1.000 | 1.000 | 1.000 | 1.0000 | 1.0000 | 6.53 |
| hybrid | 1.000 | 1.000 | 1.000 | 1.0000 | 1.0000 | 45.79 |
| hybrid_context | 0.950 | 0.950 | 1.000 | 0.9625 | 0.9751 | 186.08 |
| full | 0.950 | 0.950 | 1.000 | 0.9625 | 0.9710 | 224.15 |

Full context ranking does not outperform lexical/hybrid baselines on every metric in this small corpus. All expected documents are present within five results. Labels are manually authored; no production accuracy or million-document scaling claim is made.

## Architecture, models, API, scoring and lifecycle

See CONTEXT_GATED_RETRIEVAL.md for the architecture, five stages, seven typed models, scoring formula, metadata schema, trust lifecycle, API request/response and exact migration/evaluation commands. API v2 is POST /api/v1/evidence/retrieve; POST /api/rag/retrieve remains compatible and is deprecated only for new integrations.

## Remaining limitations

SQLite FTS5 only; single-worker local execution locks; no multi-tenant public authorization; explicit startup/manual outbox replay; no large-scale benchmark; source incidents lack verified outcome provenance; the browser UI uses contract fixtures in automated tests while the real API is exercised separately. Live NVIDIA acceptance and cloud executor deployment are not established by these tests.
