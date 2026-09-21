"""Local provider with observed state and durable rollback snapshots.

Actions change explicitly simulated workload configuration served by real HTTP
processes. They do not create cloud instances or application deployment versions.
"""

import threading
import time
import uuid
from typing import Any

from sqlalchemy import Column, Float, JSON, MetaData, String, Table, insert, select, update

from backend.observability.health_probe import HealthProbe
from backend.persistence.database import engine
from backend.providers.base import CloudProvider
from sandbox.manager import sandbox_manager

_history_metadata = MetaData()
_history = Table(
    "sandbox_configuration_history", _history_metadata,
    Column("id", String(64), primary_key=True),
    Column("service", String(160), nullable=False, index=True),
    Column("instance_id", String(64), nullable=False),
    Column("before_state", JSON, nullable=False),
    Column("after_version", String(160)),
    Column("status", String(24), nullable=False),
    Column("created_at", Float, nullable=False),
)


class LocalSandboxProvider(CloudProvider):
    """Operate registered lab services and report only confirmed state changes."""

    def __init__(self) -> None:
        _history_metadata.create_all(engine)
        self._lock = threading.RLock()

    @staticmethod
    def normalize_target(service: str) -> str:
        """Canonical identity for aliases, approval bindings, locks and history."""
        return HealthProbe.normalize_target(service)

    _normalize_name = normalize_target

    def list_resources(self) -> list[dict[str, Any]]:
        """List registered services with observed state and explicit model provenance."""
        return [self.get_resource_state(name) for name in sandbox_manager.specs]

    def get_resource_state(self, service: str) -> dict[str, Any]:
        norm = self.normalize_target(service)
        health = sandbox_manager.get_health(norm)
        metrics = sandbox_manager.get_metrics(norm)
        coherent = bool(
            health.get("instance_id") and health.get("version")
            and health.get("version") == metrics.get("version")
        )
        return {
            "service": service, "canonical_service": norm,
            "status": health.get("status", "UNKNOWN"),
            "ready": health.get("ready", False),
            "replicas": health.get("replicas") if coherent else None,
            "version": health.get("version") if coherent else None,
            "state_version": health.get("version") if coherent else None,
            "instance_id": health.get("instance_id") if coherent else None,
            "metrics": metrics,
            "state_available": coherent,
            "provider": "local_sandbox", "simulated": True,
            "configuration_scope": "local_workload_model",
        }

    def get_metrics(self, service: str) -> dict[str, Any]:
        return sandbox_manager.get_metrics(self.normalize_target(service))

    @staticmethod
    def _failure(service: str, error: str, **details: Any) -> dict[str, Any]:
        return {"status": "FAILED", "service": service, "error": error, "simulated": True, **details}

    def restart_service(self, service: str) -> dict[str, Any]:
        """Reset/revive the actual lab HTTP service; do not call this a deployment."""
        result = sandbox_manager.restart_service(self.normalize_target(service))
        return {
            "status": "SUCCESS" if result.get("status") == "SUCCESS" else "FAILED",
            "service": service, "action": result.get("action", "sandbox_state_reset"),
            "details": result, "simulated": True, "timestamp": time.time(),
        }

    def scale_service(self, service: str, replicas: int) -> dict[str, Any]:
        """Persist a captured pre-action configuration and verify the HTTP mutation."""
        if isinstance(replicas, bool) or not isinstance(replicas, int) or not 1 <= replicas <= 50:
            return self._failure(service, "INVALID_REPLICA_COUNT")
        norm = self.normalize_target(service)
        with self._lock:
            current = self.get_resource_state(service)
            if not current["state_available"] or not isinstance(current["replicas"], int):
                return self._failure(service, "PRE_ACTION_STATE_UNAVAILABLE")
            snapshot_id = uuid.uuid4().hex
            with engine.begin() as connection:
                connection.execute(insert(_history).values(
                    id=snapshot_id, service=norm, instance_id=current["instance_id"],
                    before_state={"replicas": current["replicas"], "version": current["version"]},
                    status="PREPARED", created_at=time.time(),
                ))
            result = sandbox_manager.scale_service(norm, replicas)
            observed = self.get_resource_state(service)
            confirmed = (
                result.get("status") == "SCALED" and observed["state_available"]
                and observed["instance_id"] == current["instance_id"] and observed["replicas"] == replicas
                and result.get("version") == observed["version"]
                and observed["version"] != current["version"]
            )
            with engine.begin() as connection:
                connection.execute(update(_history).where(_history.c.id == snapshot_id).values(
                    status="APPLIED" if confirmed else "FAILED",
                    after_version=observed.get("version") if confirmed else None,
                ))
            return {
                "status": "SUCCESS" if confirmed else "FAILED", "service": service,
                "action": "sandbox_replica_model_update", "simulated": True,
                "previous_replicas": current["replicas"], "target_replicas": replicas,
                "state_version": observed.get("version"), "snapshot_id": snapshot_id,
                "details": result, "timestamp": time.time(),
                **({} if confirmed else {"error": "SCALE_NOT_CONFIRMED"}),
            }

    def rollback_service(self, service: str, revision: str | None = None) -> dict[str, Any]:
        """Restore one successful scale snapshot from this actual service instance."""
        norm = self.normalize_target(service)
        with self._lock:
            current = self.get_resource_state(service)
            if not current["state_available"]:
                return self._failure(service, "CURRENT_STATE_UNAVAILABLE")
            statement = select(_history).where(
                _history.c.service == norm, _history.c.instance_id == current["instance_id"],
                _history.c.status == "APPLIED",
            ).order_by(_history.c.created_at.desc()).limit(100)
            with engine.connect() as connection:
                rows = list(connection.execute(statement).mappings())
            record = next((row for row in rows if revision is None or row["before_state"]["version"] == revision), None)
            if record is None:
                return self._failure(service, "NO_CAPTURED_ROLLBACK_REVISION" if revision else "NO_ROLLBACK_HISTORY")
            if current["version"] != record["after_version"]:
                return self._failure(service, "STALE_ROLLBACK_SNAPSHOT")
            with engine.begin() as connection:
                claimed = connection.execute(update(_history).where(
                    _history.c.id == record["id"], _history.c.status == "APPLIED",
                ).values(status="ROLLING_BACK"))
                if claimed.rowcount != 1:
                    return self._failure(service, "ROLLBACK_ALREADY_CLAIMED")
            replicas = record["before_state"]["replicas"]
            result = sandbox_manager.scale_service(norm, replicas)
            observed = self.get_resource_state(service)
            confirmed = (
                result.get("status") == "SCALED" and observed["state_available"]
                and observed["instance_id"] == current["instance_id"] and observed["replicas"] == replicas
                and result.get("version") == observed["version"]
                and observed["version"] != current["version"]
            )
            with engine.begin() as connection:
                connection.execute(update(_history).where(_history.c.id == record["id"]).values(
                    status="ROLLED_BACK" if confirmed else "ROLLBACK_FAILED",
                ))
            return {
                "status": "SUCCESS" if confirmed else "FAILED", "service": service,
                "action": "sandbox_configuration_rollback", "simulated": True,
                "restored_replicas": replicas if confirmed else None,
                "source_revision": record["before_state"]["version"],
                "state_version": observed.get("version"), "details": result,
                "timestamp": time.time(), **({} if confirmed else {"error": "ROLLBACK_NOT_CONFIRMED"}),
            }

    def health_check(self, service: str) -> dict[str, Any]:
        return sandbox_manager.get_health(self.normalize_target(service))

    def estimate_cost(self, service: str, replicas: int) -> float:
        """Hypothetical model only; local replicas incur no cloud billing charge."""
        return round(replicas * 0.24, 2)
