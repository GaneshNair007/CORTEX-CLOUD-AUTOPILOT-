"""Canonical schema-v2 source adapters; existing sources retain their provenance."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml
from backend.retrieval.models import IndexDocument
from backend.retrieval.normalization import normalize, technologies, error_signatures, failure_mode

DATA_DIR = Path(__file__).parent / "data"
SCHEMA_VERSION = 2
VERIFIED_OUTCOMES = {"VERIFIED_RECOVERED", "PARTIALLY_RECOVERED", "NO_CHANGE", "WORSE", "ROLLED_BACK"}


def epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 0.
    date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return date.replace(tzinfo=date.tzinfo or timezone.utc).timestamp()


def make_document(data: dict[str, Any], text: str, document_type: str, filename: str = "") -> IndexDocument:
    """Flatten metadata without upgrading an AI hypothesis into verified evidence."""
    doc_id = str(data.get("id") or data.get("incident_id") or Path(filename).stem)
    tech = sorted(set(normalize(t) for t in data.get("technologies", [])) | set(technologies(text)))
    status = str(data.get("memory_status") or data.get("verification_outcome") or "UNVERIFIED").upper()
    if status == "RECOVERED":
        status = "VERIFIED_RECOVERED"
    verified = bool(data.get("verified", False)) and (status in VERIFIED_OUTCOMES or document_type == "runbook")
    tags = data.get("tags", [])
    meta: dict[str, str | int | float | bool] = {
        "id": doc_id, "document_type": document_type, "title": str(data.get("title", doc_id)),
        "service": str(data.get("service") or data.get("affected_service") or ""),
        "technology_primary": normalize(str(data.get("technology_primary") or ("postgresql" if "postgresql" in tech else tech[0] if tech else ""))),
        "technologies_csv": ",".join(tech), "failure_mode": normalize(str(data.get("failure_mode") or failure_mode(text))),
        "error_signatures_csv": ",".join(error_signatures(text)),
        "tags": ",".join(map(str, tags)) if isinstance(tags, list) else str(tags), "filename": filename,
        "memory_status": status, "verification_outcome": status,
        "verified": verified, "trusted": verified and status == "VERIFIED_RECOVERED",
        "deleted": bool(data.get("deleted", False)), "deprecated": bool(data.get("deprecated", False)),
        "schema_version": SCHEMA_VERSION, "tenant_id": str(data.get("tenant_id") or ""),
        "environment": str(data.get("environment") or ""),
        "environment_scope": str(data.get("environment_scope") or ("any" if document_type == "runbook" else "")),
        "timestamp_epoch": epoch(data.get("timestamp") or data.get("updated_at") or data.get("resolved_at")),
        "resolved_at_epoch": epoch(data.get("resolved_at")),
        "dependencies_csv": ",".join(data.get("dependencies", [])),
        "dependency_types_csv": ",".join(data.get("dependency_types", [])),
        "telemetry_signature_json": json.dumps(data.get("telemetry_signature", {}), sort_keys=True),
    }
    for key in ("service_family", "severity", "provider", "region", "availability_zone", "cluster", "namespace",
                "resource_type", "root_cause_category", "resolution_category", "action_type", "historical_action",
                "rollback_performed", "slo_recovered", "mttr", "deployment_version", "version", "simulated"):
        if data.get(key) is not None and isinstance(data[key], (str, float, int, bool)):
            meta[key] = data[key]
    if "resource_type" not in meta:
        meta["resource_type"] = "database" if "postgresql" in tech or "mysql" in tech else ""
    return IndexDocument(id=doc_id, text=text, metadata=meta)


def incident_document(path: Path) -> IndexDocument:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = "\n".join(f"{key.replace('_', ' ').title()}: {value if not isinstance(value, list) else '; '.join(map(str, value))}"
                     for key, value in data.items())
    return make_document(data, text, "incident", path.name)


def runbook_document(path: Path) -> IndexDocument:
    content = path.read_text(encoding="utf-8")
    data: dict[str, Any] = {"id": path.stem}
    if content.startswith("---\n"):
        _, front, content = content.split("---", 2)
        data.update(yaml.safe_load(front) or {})
    data.setdefault("title", next((line.lstrip("# ").removeprefix("Runbook:").strip() for line in content.splitlines() if line.startswith("#")), path.stem))
    if "## Related Tags" in content:
        data.setdefault("tags", [line.strip("- ") for line in content.split("## Related Tags")[-1].splitlines() if line.strip().startswith("-")])
    return make_document(data, content, "runbook", path.name)


def load_sources(root: Path = DATA_DIR) -> list[IndexDocument]:
    docs = [incident_document(p) for p in sorted((root / "incidents").glob("*.json"))]
    docs += [runbook_document(p) for p in sorted((root / "runbooks").glob("*.md"))]
    if len({d.id for d in docs}) != len(docs):
        raise ValueError("duplicate document IDs in canonical sources")
    return docs
