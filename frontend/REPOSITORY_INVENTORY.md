# Tracked repository inventory

Snapshot: commit 266668c on 2026-09-17. This lists every tracked path at the audit baseline, grouped by subsystem. New uncommitted frontend handoff files are not part of this baseline. Inventory does not imply formal line-by-line verification of assets or every legacy component.

Tracked paths: 276

| Area | Files | Role |
| --- | ---: | --- |
| backend/chaos | 2 | Backend subsystem or project configuration |
| backend/control_plane | 2 | Backend subsystem or project configuration |
| backend/cortex | 5 | Backend subsystem or project configuration |
| backend/data | 3 | Backend subsystem or project configuration |
| backend/evaluation | 3 | Backend subsystem or project configuration |
| backend/execution | 7 | Backend subsystem or project configuration |
| backend/forecasting | 9 | Backend subsystem or project configuration |
| backend/llm | 7 | Backend subsystem or project configuration |
| backend/models | 2 | Backend subsystem or project configuration |
| backend/observability | 4 | Backend subsystem or project configuration |
| backend/optimization | 2 | Backend subsystem or project configuration |
| backend/orchestrator | 3 | Backend subsystem or project configuration |
| backend/persistence | 3 | Backend subsystem or project configuration |
| backend/providers | 5 | Backend subsystem or project configuration |
| backend/rag | 39 | Backend subsystem or project configuration |
| backend/slo | 2 | Backend subsystem or project configuration |
| backend/tests | 11 | Backend subsystem or project configuration |
| backend/tools | 5 | Backend subsystem or project configuration |
| backend/topology | 3 | Backend subsystem or project configuration |
| backend/twin | 2 | Backend subsystem or project configuration |
| backend/verification | 2 | Backend subsystem or project configuration |
| docs | 6 | Architecture, requirements and migration references |
| frontend/active-console | 18 | Active new UI and client contracts |
| frontend/other | 114 | Build, assets, tests and preserved legacy frontend |
| root/configuration | 13 | Backend subsystem or project configuration |
| sandbox | 4 | Local HTTP service runtime |

## backend/chaos

- backend/chaos/__init__.py
- backend/chaos/engine.py

## backend/control_plane

- backend/control_plane/__init__.py
- backend/control_plane/pipeline.py

## backend/cortex

- backend/cortex/__init__.py
- backend/cortex/gateway.py
- backend/cortex/guard.py
- backend/cortex/ledger.py
- backend/cortex/policies.py

## backend/data

- backend/data/memory_store.jsonl
- backend/data/past_incidents.json
- backend/data/runbooks.json

## backend/evaluation

- backend/evaluation/harness.py
- backend/evaluation/metrics.py
- backend/evaluation/scenarios.py

## backend/execution

- backend/execution/__init__.py
- backend/execution/anti_thrashing.py
- backend/execution/idempotency.py
- backend/execution/locks.py
- backend/execution/retry.py
- backend/execution/rollout.py
- backend/execution/tool_registry.py

## backend/forecasting

- backend/forecasting/__init__.py
- backend/forecasting/anomalies.py
- backend/forecasting/artifacts/model_metadata.json
- backend/forecasting/artifacts/workload_model.pkl
- backend/forecasting/evaluate.py
- backend/forecasting/features.py
- backend/forecasting/forecaster.py
- backend/forecasting/model.py
- backend/forecasting/train.py

## backend/llm

- backend/llm/__init__.py
- backend/llm/benchmark.py
- backend/llm/benchmark_routing.py
- backend/llm/client.py
- backend/llm/optimization_summary.md
- backend/llm/router.py
- backend/llm/test_batch.py

## backend/models

- backend/models/__init__.py
- backend/models/proposals.py

## backend/observability

- backend/observability/__init__.py
- backend/observability/health_probe.py
- backend/observability/metrics_collector.py
- backend/observability/telemetry_models.py

## backend/optimization

- backend/optimization/__init__.py
- backend/optimization/optimizer.py

## backend/orchestrator

- backend/orchestrator/__init__.py
- backend/orchestrator/agent.py
- backend/orchestrator/test_variants.py

## backend/persistence

- backend/persistence/__init__.py
- backend/persistence/database.py
- backend/persistence/models.py

## backend/providers

- backend/providers/__init__.py
- backend/providers/base.py
- backend/providers/cloud_placeholders.py
- backend/providers/docker_provider.py
- backend/providers/sandbox_provider.py

## backend/rag

- backend/rag/__init__.py
- backend/rag/build_index.py
- backend/rag/data/incidents/INC-2026-001_k8s_pod_crashloop.json
- backend/rag/data/incidents/INC-2026-002_k8s_oomkilled_pod.json
- backend/rag/data/incidents/INC-2026-003_postgres_conn_pool_exhaustion.json
- backend/rag/data/incidents/INC-2026-004_postgres_read_replica_lag.json
- backend/rag/data/incidents/INC-2026-005_api_gateway_504_timeout.json
- backend/rag/data/incidents/INC-2026-006_redis_maxmemory_eviction.json
- backend/rag/data/incidents/INC-2026-007_redis_latency_keyscan.json
- backend/rag/data/incidents/INC-2026-008_vpc_peering_route_drop.json
- backend/rag/data/incidents/INC-2026-009_canary_deployment_failure.json
- backend/rag/data/incidents/INC-2026-010_vault_token_expiry_auth_drop.json
- backend/rag/data/incidents/INC-2026-011_pvc_pending_storage_provision.json
- backend/rag/data/incidents/INC-2026-012_disk_space_100_percent_full.json
- backend/rag/data/incidents/INC-2026-013_coredns_upstream_timeout.json
- backend/rag/data/incidents/INC-2026-014_prometheus_tsdb_corruption.json
- backend/rag/data/incidents/INC-2026-015_vector_log_pipeline_backpressure.json
- backend/rag/data/incidents/INC-2026-016_db_transaction_deadlock_cascade.json
- backend/rag/data/incidents/INC-2026-017_envoy_rate_limit_misconfig.json
- backend/rag/data/incidents/INC-2026-018_ebs_gp2_iops_exhaustion.json
- backend/rag/data/incidents/INC-2026-019_aws_iam_sts_assume_role_drift.json
- backend/rag/data/incidents/INC-2026-020_external_dns_ttl_drift.json
- backend/rag/data/runbooks/RB-001_k8s_pod_crashloop.md
- backend/rag/data/runbooks/RB-002_postgres_connection_pool.md
- backend/rag/data/runbooks/RB-003_postgres_replication_lag.md
- backend/rag/data/runbooks/RB-004_api_gateway_504_timeouts.md
- backend/rag/data/runbooks/RB-005_redis_memory_eviction.md
- backend/rag/data/runbooks/RB-006_redis_latency_single_thread.md
- backend/rag/data/runbooks/RB-007_vpc_peering_network_partition.md
- backend/rag/data/runbooks/RB-008_failed_canary_deployment.md
- backend/rag/data/runbooks/RB-009_vault_jwt_auth_failure.md
- backend/rag/data/runbooks/RB-010_pvc_storage_pending_disk_full.md
- backend/rag/data/runbooks/RB-011_coredns_name_resolution.md
- backend/rag/data/runbooks/RB-012_prometheus_tsdb_monitoring.md
- backend/rag/data/runbooks/RB-013_vector_fluentbit_logging.md
- backend/rag/data/runbooks/RB-014_postgres_deadlock_cascades.md
- backend/rag/data/runbooks/RB-015_envoy_rate_limit_ebs_iops_iam.md
- backend/rag/retrieve.py
- backend/rag/store.py

## backend/slo

- backend/slo/__init__.py
- backend/slo/config.py

## backend/tests

- backend/tests/__init__.py
- backend/tests/test_cascading_autonomy_level3.py
- backend/tests/test_chaos.py
- backend/tests/test_closed_loop_verification.py
- backend/tests/test_execution_gateway.py
- backend/tests/test_forecasting_pipeline.py
- backend/tests/test_guard.py
- backend/tests/test_optimizer.py
- backend/tests/test_pipeline.py
- backend/tests/test_security_invariants.py
- backend/tests/test_twin_and_topology.py

## backend/tools

- backend/tools/__init__.py
- backend/tools/actions.py
- backend/tools/event_bus.py
- backend/tools/events.jsonl
- backend/tools/evidence_ledger.jsonl

## backend/topology

- backend/topology/__init__.py
- backend/topology/blast_radius.py
- backend/topology/graph.py

## backend/twin

- backend/twin/__init__.py
- backend/twin/simulator.py

## backend/verification

- backend/verification/__init__.py
- backend/verification/verifier.py

## docs

- docs/BACKEND_COMPLETION_REPORT.md
- docs/COMPETITIVE_RESEARCH.md
- docs/CURRENT_SYSTEM_AUDIT.md
- docs/FRONTEND_MIGRATION_PLAN.md
- docs/IMPLEMENTATION_PLAN.md
- docs/TARGET_ARCHITECTURE.md

## frontend/active-console

- frontend/src/control-plane/Actions.tsx
- frontend/src/control-plane/Application.tsx
- frontend/src/control-plane/Governance.tsx
- frontend/src/control-plane/Intelligence.tsx
- frontend/src/control-plane/Landing.tsx
- frontend/src/control-plane/Overview.tsx
- frontend/src/control-plane/Records.tsx
- frontend/src/control-plane/Support.tsx
- frontend/src/control-plane/Topology.tsx
- frontend/src/control-plane/client.ts
- frontend/src/control-plane/contracts.ts
- frontend/src/control-plane/hooks.ts
- frontend/src/control-plane/navigation.ts
- frontend/src/control-plane/template/card.tsx
- frontend/src/control-plane/template/dialog.tsx
- frontend/src/control-plane/template/utils.ts
- frontend/src/control-plane/theme.css
- frontend/src/control-plane/ui.tsx

## frontend/other

- frontend/.agents/skills/superdesign/INIT.md
- frontend/.agents/skills/superdesign/SKILL.md
- frontend/.agents/skills/superdesign/SUPERDESIGN.md
- frontend/.agents/skills/superdesign/agents/openai.yaml
- frontend/.agents/skills/superdesign/references/ASSET_GENERATION.md
- frontend/.agents/skills/superdesign/references/COMPONENTS.md
- frontend/.agents/skills/superdesign/references/GRAPHIC.md
- frontend/.agents/skills/superdesign/references/INIT.md
- frontend/.agents/skills/superdesign/references/PRESENTATION.md
- frontend/.agents/skills/superdesign/references/RESUME.md
- frontend/.agents/skills/superdesign/references/SUPERDESIGN.md
- frontend/.agents/skills/superdesign/references/WEBSITE.md
- frontend/.agents/skills/superdesign/references/design-with-your-model.md
- frontend/.env.example
- frontend/.gitignore
- frontend/README.md
- frontend/THIRD_PARTY_LICENSES.md
- frontend/index.html
- frontend/metadata.json
- frontend/package-lock.json
- frontend/package.json
- frontend/playwright.config.ts
- frontend/server.ts
- frontend/skills-lock.json
- frontend/src/App.tsx
- frontend/src/assets/images/1_corridor.jpg
- frontend/src/assets/images/2_rack_leds.jpg
- frontend/src/assets/images/3_cables.jpg
- frontend/src/assets/images/4_engineer.jpg
- frontend/src/assets/images/5_control_room.jpg
- frontend/src/assets/images/6_hardware.jpg
- frontend/src/assets/images/7_switch.jpg
- frontend/src/assets/images/8_team.jpg
- frontend/src/assets/images/ATTRIBUTION.md
- frontend/src/assets/images/arjit.png
- frontend/src/assets/images/ganesh.png
- frontend/src/components/ActionControl.tsx
- frontend/src/components/AuditTimeline.tsx
- frontend/src/components/CommandOverview.tsx
- frontend/src/components/DeployPatchModal.tsx
- frontend/src/components/EvidenceRetrieval.tsx
- frontend/src/components/GlobalSearchModal.tsx
- frontend/src/components/IncidentDetailModal.tsx
- frontend/src/components/IncidentHistoryView.tsx
- frontend/src/components/IncidentSimulator.tsx
- frontend/src/components/KnowledgeBaseView.tsx
- frontend/src/components/LogsView.tsx
- frontend/src/components/Navbar.tsx
- frontend/src/components/OverviewView.tsx
- frontend/src/components/PortalHero.tsx
- frontend/src/components/RunbookExecutionModal.tsx
- frontend/src/components/SettingsModal.tsx
- frontend/src/components/SideNavBar.tsx
- frontend/src/components/SimulatorView.tsx
- frontend/src/components/SupportModal.tsx
- frontend/src/components/TelemetryView.tsx
- frontend/src/components/TopNavBar.tsx
- frontend/src/components/TopologyModal.tsx
- frontend/src/components/console/CommandCenterView.tsx
- frontend/src/components/layout/CommandPalette.tsx
- frontend/src/components/layout/CortexHeader.tsx
- frontend/src/components/layout/CortexSidebar.tsx
- frontend/src/components/layout/Navbar.tsx
- frontend/src/components/modals/IncidentDetailDrawer.tsx
- frontend/src/components/modals/ServiceInspectorDrawer.tsx
- frontend/src/components/sections/ArchitectureStory.tsx
- frontend/src/components/sections/AuditTimeline.tsx
- frontend/src/components/sections/ClosingSection.tsx
- frontend/src/components/sections/EntryLoader.tsx
- frontend/src/components/sections/EvidenceRetrieval.tsx
- frontend/src/components/sections/HeroSection.tsx
- frontend/src/components/sections/IncidentMarquee.tsx
- frontend/src/components/sections/IncidentSimulator.tsx
- frontend/src/components/sections/ProblemSection.tsx
- frontend/src/components/sections/ProblemStatement.tsx
- frontend/src/components/sections/SafetyControl.tsx
- frontend/src/components/sections/SystemWorkflow.tsx
- frontend/src/components/ui/CircularGallery.tsx
- frontend/src/components/views/ApprovalsView.tsx
- frontend/src/components/views/AuditLedgerView.tsx
- frontend/src/components/views/ChaosLabView.tsx
- frontend/src/components/views/CloudProvidersView.tsx
- frontend/src/components/views/CortexGuardView.tsx
- frontend/src/components/views/CostView.tsx
- frontend/src/components/views/DemoView.tsx
- frontend/src/components/views/DigitalTwinView.tsx
- frontend/src/components/views/EvaluationView.tsx
- frontend/src/components/views/IncidentMemoryView.tsx
- frontend/src/components/views/IncidentsView.tsx
- frontend/src/components/views/OptimizerView.tsx
- frontend/src/components/views/PoliciesView.tsx
- frontend/src/components/views/PredictionsView.tsx
- frontend/src/components/views/ReliabilityView.tsx
- frontend/src/components/views/SustainabilityView.tsx
- frontend/src/components/views/TopologyView.tsx
- frontend/src/data/mockData.ts
- frontend/src/index.css
- frontend/src/main.tsx
- frontend/src/services/api.ts
- frontend/src/types.ts
- frontend/src/vite-env.d.ts
- frontend/tests/adversarial_stress_verification.test.ts
- frontend/tests/browser/console.spec.ts
- frontend/tests/browser/fixtures.ts
- frontend/tests/run_tests.ts
- frontend/tests/test_helpers.ts
- frontend/tests/tier1_feature_coverage.test.ts
- frontend/tests/tier2_boundary_corner.test.ts
- frontend/tests/tier3_cross_feature.test.ts
- frontend/tests/tier4_real_world_sre.test.ts
- frontend/tests/tier6_hero_portal_responsiveness.test.ts
- frontend/tsconfig.json
- frontend/vercel.json
- frontend/vite.config.ts

## root/configuration

- .gitignore
- GEMINI.md
- README.md
- backend/.env.example
- backend/.gitignore
- backend/.python-version
- backend/README.md
- backend/__init__.py
- backend/api_server.py
- backend/app.py
- backend/interfaces.py
- backend/main.py
- backend/requirements.txt

## sandbox

- sandbox/docker-compose.yml
- sandbox/manager.py
- sandbox/prometheus.yml
- sandbox/services/service_template.py
