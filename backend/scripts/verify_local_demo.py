"""Exercise the API and actual local lab in an isolated workspace, without paid AI.

Run: python -m backend.scripts.verify_local_demo --output docs/local_demo_verification.json
This is explicitly a modeled sandbox check, never a live NVIDIA acceptance test.
"""
import argparse
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def run() -> dict:
    runtime = Path(tempfile.mkdtemp(prefix="cortex-demo-verification-"))
    os.environ.update(PYTHON_DOTENV_DISABLED="1", LLM_PRIMARY_PROVIDER="heuristic",
        DIAGNOSIS_PROVIDER="heuristic", CRITIQUE_PROVIDER="heuristic", CORTEX_START_SANDBOX="true",
        CORTEX_EXECUTION_PROVIDER="local_sandbox", CORTEX_DATA_DIR=str(runtime),
        CORTEX_CHROMA_DIR=str(runtime / "chroma"), CORTEX_PUBLIC_READS="false", HF_HUB_OFFLINE="1")
    admin, operator, viewer = (secrets.token_urlsafe(32) for _ in range(3))
    os.environ.update(CORTEX_ADMIN_TOKEN=admin, CORTEX_OPERATOR_TOKEN=operator, CORTEX_VIEWER_TOKEN=viewer)
    from sandbox.manager import sandbox_manager
    for spec in sandbox_manager.specs.values():
        spec["port"] += 21000  # Private lab: never mutate a user's demo services.
    from fastapi.testclient import TestClient
    from backend.api_server import app
    from backend.retrieval.engine import get_engine
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append({"name": name, "status": "PASS"})
    with TestClient(app) as client:
        def get(path, token=viewer):
            response = client.get(path, headers={"Authorization": "Bearer " + token})
            response.raise_for_status()
            return response.json()
        def post(path, body, token=operator):
            response = client.post(path, json=body, headers={"Authorization": "Bearer " + token})
            response.raise_for_status()
            return response.json()
        check("SQL and actual Chroma startup", get("/readyz")["status"] == "ready")
        check("anonymous mutation denied", client.post("/api/tools/action", json={}).status_code == 401)
        check("viewer mutation denied", client.post("/api/tools/action", json={}, headers={"Authorization": "Bearer " + viewer}).status_code == 403)
        services = get("/api/services")["services"]
        check("eight live HTTP model services", len(services) == 8 and all(s["simulated"] and s["source"] == "sandbox_model" for s in services))
        evidence = post("/api/v1/evidence/retrieve", {"query": "PostgreSQL connection pool exhaustion HTTP 503", "context": {"service": "payment-api", "technologies": ["postgresql"]}})
        check("real hybrid retrieval and explanations", evidence["semantic_available"] and bool(evidence["results"]) and all(r["why_retrieved"] for r in evidence["results"]))
        get("/api/services")
        blocked = post("/api/tools/action", {"action_type": "restart_database", "params": {"service": "postgres"}})
        check("dangerous database mutation blocked", blocked["status"] == "blocked")
        before = sandbox_manager.get_health("inventory-service")["version"]
        dry = post("/api/tools/action", {"action_type": "restart_service", "params": {"service": "inventory-service"}, "dry_run": True})
        check("dry run leaves resource unchanged", sandbox_manager.get_health("inventory-service")["version"] == before and dry["action_result"]["output"]["dry_run"])
        post("/api/cortex/kill-switch", {"engaged": True}, admin)
        chaos = post("/api/chaos/inject", {"fault_type": "latency", "target_service": "inventory-service"})
        check("shared kill switch blocks chaos", chaos["status"] == "blocked" and sandbox_manager.get_health("inventory-service")["version"] == before)
        post("/api/cortex/kill-switch", {"engaged": False}, admin)
        post("/api/cortex/autonomy", {"level": 3}, admin)
        get("/api/services")
        chaos = post("/api/chaos/inject", {"fault_type": "latency", "target_service": "inventory-service"})
        check("authorized real sandbox fault", chaos["status"] == "injected")
        get("/api/services")
        healed = post("/api/tools/action", {"incident_id": "DEMO-RECOVER", "action_type": "restart_service", "params": {"service": "inventory-service"}, "reason": "Inventory zebra request stall with high latency after a sandbox fault"})
        check("verification establishes modeled recovery", healed["status"] == "success" and healed["verification"]["outcome"] == "RECOVERED" and healed["verification"]["verification"]["simulated"])
        memory_id = healed["verification"]["memory"]["id"]
        learned = post("/api/v1/evidence/retrieve", {"query": "Inventory zebra request stall high latency", "context": {"service": "inventory-service", "environment": "sandbox"}, "options": {"top_k": 10}})
        check("verified memory immediately searchable in Chroma", memory_id in [r["id"] for r in learned["results"]] and learned["semantic_available"])
        post("/api/cortex/autonomy", {"level": 1}, admin)
        get("/api/services")
        pending = post("/api/tools/action", {"incident_id": "DEMO-APPROVAL", "action_type": "scale_service", "params": {"service": "order-service", "replicas": 4}})
        check("one visible approval record", pending["status"] == "approval_required" and pending["approval_id"] in [r["approval_id"] for r in get("/api/cortex/approvals")["pending_approvals"]])
        visible = next(r for r in get("/api/cortex/approvals")["pending_approvals"] if r["approval_id"] == pending["approval_id"])
        check("approval matches console contract", visible["status"] == "pending" and isinstance(visible["created_at"], (int, float)) and visible["ttl_seconds"] > 0)
        approved = post("/api/cortex/approvals/resolve", {"approval_id": pending["approval_id"], "approved": True})
        check("approved exact action executes", approved["execution_result"]["status"] == "SUCCESS" and sandbox_manager.get_health("order-service")["replicas"] == 4)
        replay = post("/api/cortex/approvals/resolve", {"approval_id": pending["approval_id"], "approved": True})
        check("approval consumed", replay["status"] == "consumed" and "execution_result" not in replay)
        check("audit hash chain intact", get("/api/audit/ledger")["integrity"]["valid"])
        primary = get("/api/v1/llm/status")
        check("heuristic never reported as external AI", primary["active_provider"] == "heuristic" and primary["status"] == "DEGRADED")
        count = get_engine().semantic.collection().count()
    return {"status": "PASS", "timestamp": datetime.now(timezone.utc).isoformat(), "checks": checks,
            "knowledge_documents_after_learning": count, "execution_environment": "isolated_local_sandbox",
            "real_external_ai_test": "NOT_RUN"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
