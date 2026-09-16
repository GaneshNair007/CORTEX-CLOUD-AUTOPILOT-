# CORTEX CLOUD AUTOPILOT — Competitive Research & Prior Art
**Document:** `docs/COMPETITIVE_RESEARCH.md`  
**Date Checked:** September 16, 2026  
**Audience:** Senior Infrastructure Engineers, Cloud Architecture Researchers, Evaluation Committees  
**Standards Adherence:** Strict factual discipline. Zero marketing hyperbole. No claims of "first ever" or "nobody has done this before."

---

## 1. Cloud Optimization & Autoscaling Systems

### 1.1 AWS Compute Optimizer
* **Capability:** Rightsizing recommendations for EC2 instances, EBS volumes, Auto Scaling groups, and AWS Lambda functions based on Amazon CloudWatch metrics.
* **What it already solves:** Analyzes up to 14 days of historical utilization (CPU, memory, storage, network) using proprietary machine learning models to identify over-provisioned or under-provisioned resources and recommend optimal instance families. Supports ASGs using predictive scaling.
* **Limitations / intended scope:** Focuses primarily on static rightsizing recommendations (e.g., changing instance types) rather than active, sub-minute dynamic control. Does not model downstream multi-tier application dependencies or simulate cascading impacts of instance type migrations.
* **What CORTEX must NOT claim as unique:** Machine-learning-based instance rightsizing recommendations; compute cost estimation for candidate instance types.
* **What gap remains relevant:** Pre-action counterfactual simulation of how a rightsizing or scaling change affects downstream dependencies and SLOs before applying the change.
* **Official Source:** [AWS Compute Optimizer User Guide](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)
* **Date Checked:** September 16, 2026

### 1.2 Amazon EC2 Predictive Scaling
* **Capability:** Proactive capacity provisioning for EC2 Auto Scaling groups using machine learning to forecast daily and weekly recurring traffic patterns.
* **What it already solves:** Uses at least 24 hours (ideally 14 days) of historical CloudWatch traffic data to calculate future capacity requirements, provisioning EC2 instances in advance so they are warmed up before cyclical traffic spikes hit.
* **Limitations / intended scope:** Best suited for predictable, cyclical workloads (daily/weekly diurnal patterns). Operates at the EC2 Auto Scaling group level; cannot predict non-cyclical sudden events or cross-service cascading backpressure. Does not integrate with multi-objective trade-offs (e.g., trade off p95 latency vs. carbon/energy).
* **What CORTEX must NOT claim as unique:** Predictive scaling ahead of forecasted demand curves; recurring traffic pattern forecasting.
* **What gap remains relevant:** Multi-objective evaluation combining cost, latency, reliability, carbon estimation, and blast-radius risk, alongside reactive fallback when predictions exhibit high uncertainty.
* **Official Source:** [Predictive Scaling for Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-predictive-scaling.html)
* **Date Checked:** September 16, 2026

### 1.3 Azure Advisor & Azure Predictive Autoscale
* **Capability:** Azure Advisor provides personalized recommendations across High Availability, Security, Performance, and Cost. Azure Monitor Predictive Autoscale forecasts CPU load for Virtual Machine Scale Sets (VMSS).
* **What it already solves:** Azure predictive autoscale trains an ML model on at least 7 days of historical Percentage CPU utilization (average aggregation) to scale out VMSS ahead of recurring spikes. Provides a "Forecast Only" mode for validation.
* **Limitations / intended scope:** Limited to Azure VMSS and the CPU percentage metric. Supports scale-out only (scale-in must be handled by metric rules). Advisor recommendations are advisory and batch-generated rather than closed-loop real-time controllers.
* **What CORTEX must NOT claim as unique:** Visualizing actual vs. predicted workload curves; forecast-only simulation modes.
* **What gap remains relevant:** Multi-metric forecasting (request rate, queue depth, connection pools, latency) coupled with policy-governed safety gates and closed-loop post-action verification.
* **Official Source:** [Azure Monitor Autoscale Documentation](https://learn.microsoft.com/en-us/azure/azure-monitor/autoscale/autoscale-get-started)
* **Date Checked:** September 16, 2026

### 1.4 Google Cloud Recommender & GKE Multidimensional Pod Autoscaling (MPA)
* **Capability:** Google Cloud Recommender provides automated heuristic and ML insights for cost, security, and performance. GKE Multidimensional Pod Autoscaler combines horizontal and vertical pod autoscaling.
* **What it already solves:** MPA coordinates horizontal scaling (adjusting replica count based on CPU utilization) and vertical scaling (adjusting pod memory requests via VPA) simultaneously without conflict.
* **Limitations / intended scope:** Reactive to observed utilization thresholds; does not forecast ahead of impending flash crowds. Operates within individual Kubernetes deployment boundaries without end-to-end dependency graph awareness.
* **What CORTEX must NOT claim as unique:** Combining horizontal and vertical autoscaling concepts in Kubernetes.
* **What gap remains relevant:** Dependency-aware blast radius calculation and pre-flight simulation before changing replica counts or mutating stateful backends.
* **Official Source:** [GKE Multidimensional Pod Autoscaling](https://cloud.google.com/kubernetes-engine/docs/how-to/multidimensional-pod-autoscaling)
* **Date Checked:** September 16, 2026

### 1.5 Karpenter (Kubernetes Node Autoscaling)
* **Capability:** High-performance, open-source node autoscaler designed for Kubernetes (originally AWS, now provider-neutral under CNCF).
* **What it already solves:** Observes unscheduled pods, evaluates their scheduling constraints (resource requests, node selectors, affinities, tolerations, topologies), and directly provisions right-sized nodes in seconds without intermediary node groups. Continuously consolidates nodes to minimize cost.
* **Limitations / intended scope:** Operates strictly at the infrastructure/node layer (provisioning and bin-packing compute capacity for pods). Does not determine pod-level application scaling or diagnose application-level service faults.
* **What CORTEX must NOT claim as unique:** Dynamic node provisioning or node consolidation algorithms.
* **What gap remains relevant:** Application-layer SRE control: linking telemetry, runbooks, and causal incident diagnosis to safe remediation decisions.
* **Official Source:** [Karpenter Official Documentation](https://karpenter.sh/)
* **Date Checked:** September 16, 2026

### 1.6 OpenCost & Kubecost
* **Capability:** Open-source (CNCF sandbox) real-time cost monitoring and allocation for Kubernetes workloads.
* **What it already solves:** Allocates cloud infrastructure spend by namespace, deployment, service, and pod label. Calculates daily and hourly run rates using cloud billing APIs and pricing sheets.
* **Limitations / intended scope:** Visibility and chargeback platform; does not execute autonomous mutations, remediations, or predictive scaling.
* **What CORTEX must NOT claim as unique:** Breaking down Kubernetes costs by namespace and container; allocating infrastructure spend to individual microservices.
* **What gap remains relevant:** Real-time multi-objective scoring that weighs estimated cost delta against SLO violation risk and reliability risk before executing actions.
* **Official Source:** [OpenCost Specification & Docs](https://www.opencost.io/)
* **Date Checked:** September 16, 2026

### 1.7 CAST AI & StormForge
* **Capability:** Autonomous cloud optimization platforms for Kubernetes. CAST AI automates node selection, spot instance lifecycle, and bin-packing. StormForge automates pod resource rightsizing (CPU/memory requests and limits) via ML.
* **What it already solves:** CAST AI provides hands-off compute optimization, replacing traditional cluster autoscalers. StormForge uses machine learning on historical application performance to recommend right-sized pod configurations, preventing CPU throttling and OOMKills.
* **Limitations / intended scope:** Primarily cost- and resource-allocation-driven. Neither platform functions as an autonomous incident response copilot or forensic investigator with RAG, runbook correlation, causal diagnosis, or policy-governed tool execution.
* **What CORTEX must NOT claim as unique:** Autonomous rightsizing of Kubernetes resources; automated spot instance rebalancing.
* **What gap remains relevant:** Unified control loop linking incident triage, vector memory retrieval, counterfactual digital twin simulation, and risk-adaptive safety authorization.
* **Official Source:** [CAST AI Documentation](https://cast.ai/), [StormForge Documentation](https://www.stormforge.io/)
* **Date Checked:** September 16, 2026

---

## 2. Cloud Reliability & Real-World Outage Postmortems

Analysis of major infrastructure outages across AWS, Azure, Google Cloud, and Cloudflare (2023–2026) highlights recurring failure modes that inform CORTEX's defensive invariants.

| Outage / Incident Type | Real-World Failure Mechanism | Industry Postmortem Finding | CORTEX Architectural Defense |
| :--- | :--- | :--- | :--- |
| **Global Configuration Propagation** | A minor configuration or metadata update is published globally without canary stages, immediately crashing edge proxies or control-plane handlers. | "Configuration changes must be staged through progressive canary deployment rings with automated rollbacks upon error rate deviation." | **Progressive Change Guard:** Staged rollout (`Proposed → Shadow → Canary 1 → Observe → 10% → Verify → 100%`) with automatic abort on metric regression. |
| **Monitoring Coupled with Infrastructure** | The monitoring and telemetry plane shares dependencies (DNS, identity, or network) with the failing workloads, blinding SREs during outages. | "Observability must maintain out-of-band health probes independent of primary telemetry collectors." | **Out-of-Band Probes & `OBSERVABILITY_DEGRADED`:** Secondary synthetic HTTP probes; autonomy level automatically drops when monitoring confidence degrades. |
| **Cascading Dependency Failures** | Failure of an upstream cache or database causes timeouts in middle-tier services, which bubble up to the API Gateway and fail downstream callers. | "Static blast radius assumptions fail because indirect transitive dependencies amplify failure across service boundaries." | **Topology-Aware Blast Radius:** Computes blast radius across complete graph (services, databases, caches, networks) rather than direct dependencies. |
| **Retry Amplification (Retry Storms)** | Upstream services receive 5xx errors and immediately retry, flooding recovering downstream services with exponential traffic and preventing recovery. | "Aggressive, unbudgeted retries turn temporary latency hiccups into prolonged multi-hour death spirals." | **Retry Budgets & Circuit Breakers:** Bounded retry budgets, exponential backoff with full jitter, per-service action quotas, and minimum dwell times. |
| **Harmful Remediation (Second Incident)** | An operator or automated script restarts a primary database or rolls back a core service during peak load, exacerbating the outage. | "Remediation actions must be treated as first-class infrastructure changes subject to pre-flight risk checks." | **Counterfactual Digital Twin & CORTEX Guard:** Mandatory pre-execution shadow simulation; high-blast-radius actions (`restart_database`) are blocked or require human approval. |
| **Control-Plane Thrashing** | Rapid oscillations where autoscalers alternate between aggressive scale-up and scale-down, causing continuous pod churn. | "Autoscalers must implement hysteresis and cooldown periods to prevent thrashing under fluctuating workloads." | **Anti-Thrashing Controller:** Enforces cooldown windows, minimum dwell times, and incorporates change cost into optimization scoring. |

---

## 3. Agentic Security & Tool Governance

### 3.1 AWS Agentic AI Lens & Bedrock AgentCore
* **What it solves:** Provides Well-Architected guidance across Operational Excellence, Security, Reliability, Performance, and Cost for autonomous agent systems. Implements AgentCore Policy for deterministic evaluation of agent tool calls.
* **Limitations:** Focuses on enterprise cloud governance within AWS Bedrock; relies on developers to implement domain-specific simulation and verification handlers.
* **What CORTEX must NOT claim as unique:** Defining architectural pillars for AI agents; policy gates before tool invocation.
* **What gap remains relevant:** Open, multi-cloud, infrastructure-specific capability envelopes that integrate counterfactual topology simulation into policy evaluation.
* **Official Source:** [AWS Well-Architected Agentic AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/)
* **Date Checked:** September 16, 2026

### 3.2 AWS Dogwood (Temporal Runtime Verification)
* **What it solves:** Released by AWS in August 2026, Dogwood extends the Cedar policy language with temporal policies. Evaluates agent action history over multi-step sessions (e.g., enforcing rate limits over time, verifying prerequisites like "must inspect status before scaling").
* **Limitations:** Language and evaluation engine; does not provide cloud infrastructure models, blast radius algorithms, or digital twin simulation out of the box.
* **What CORTEX must NOT claim as unique:** Temporal policy evaluation over agent action sequences.
* **What gap remains relevant:** Domain-specific temporal rules applied to cloud reliability (e.g., "cannot execute scale-down within 15 minutes of scale-up on the same service").
* **Official Source:** [AWS Open Source / Dogwood Specification](https://github.com/cedar-policy)
* **Date Checked:** September 16, 2026

### 3.3 Google Model Armor & Agent Gateway
* **What it solves:** Google Model Armor provides real-time LLM traffic filtering (jailbreak detection, PII redaction, content safety). Google Agent Gateway provides a centralized control plane for governing agent tool interactions with identity-aware enforcement.
* **Limitations:** General-purpose enterprise AI gateway; lacks deep Kubernetes topology awareness or closed-loop post-action telemetry verification.
* **What CORTEX must NOT claim as unique:** Prompt-injection filtering; reverse-proxy agent gateways for tool calling.
* **What gap remains relevant:** Linking agent identity and capability contracts directly to infrastructure blast radius and post-action SLO verification.
* **Official Source:** [Google Cloud Model Armor Documentation](https://cloud.google.com/security/products/model-armor)
* **Date Checked:** September 16, 2026

### 3.4 Microsoft Defender for Endpoint — AI Agent Runtime Protection
* **What it solves:** Protects local AI agents at three inspection points: user prompt, pre-tool call, and post-tool response. Detects prompt injection, data exfiltration, and unauthorized file access in audit or block mode.
* **Limitations:** Host-level endpoint security product; not designed to manage cloud infrastructure mutations or evaluate distributed service availability.
* **What CORTEX must NOT claim as unique:** Pre-tool and post-tool interception hooks.
* **What gap remains relevant:** Infrastructure-native CORTEX Guard: intercepting cloud mutations, simulating dependency impact, and verifying operational recovery.
* **Official Source:** [Microsoft Defender for Endpoint Documentation](https://learn.microsoft.com/en-us/defender-endpoint/)
* **Date Checked:** September 16, 2026

### 3.5 OWASP Top 10 for Agentic AI & LLM Applications
Key threats addressed in CORTEX architecture:
1. **ASI-01: Excessive Agency & Unbounded Execution:** Addressed by CORTEX Guard capability envelopes, strict tool registry schemas, and risk-adaptive autonomy levels.
2. **ASI-02: Prompt Injection via Untrusted Data:** Addressed by treating RAG runbooks and external telemetry strictly as structured data, never executable instructions.
3. **ASI-03: Inadequate Authorization & Monolithic Identity:** Addressed by propagating user and agent identity to every audit event.
4. **ASI-04: Lack of Post-Execution Verification:** Addressed by mandatory telemetry settling periods and closed-loop verification before marking incidents resolved.
5. **ASI-05: Cascading Blast Radius:** Addressed by dependency-aware counterfactual simulation and blast radius score thresholds.

---

## 4. Synthesis & The Defensible CORTEX Positioning

| Capability Dimension | Existing Cloud Providers & Tools | CORTEX Cloud Autopilot Target Positioning |
| :--- | :--- | :--- |
| **Detection & Diagnosis** | Fragmented across Datadog, Prometheus, PagerDuty, Runbooks | Unified deterministic correlation + Dense vector RAG memory + LLM hypothesis with self-critique |
| **Workload Scaling** | AWS/Azure predictive autoscale (cyclical CPU only); HPA (reactive) | Hybrid scaling: Reactive safety layer + Predictive scale-ahead + Multi-objective Pareto optimization |
| **Remediation Safety** | Advisory recommendations or unrestricted script execution | Policy-governed CORTEX Guard + Capability contracts + Dependency-aware blast radius scoring |
| **Impact Evaluation** | None (trial-and-error in production) | Pre-flight Counterfactual Digital Twin shadow simulation across service dependency graph |
| **Execution Rollout** | Blind single-shot API execution | Staged progressive rollout (`Shadow → Canary 1 → 10% → 100%`) with automatic rollback |
| **Post-Action Verification** | API returns HTTP 200 = assumed success | Closed-loop telemetry verification comparing pre/post SLO metrics before declaring recovery |
| **Audit & Governance** | Unlinked application logs | Tamper-evident, hash-chained evidence ledger recording full provenance and correlation IDs |
