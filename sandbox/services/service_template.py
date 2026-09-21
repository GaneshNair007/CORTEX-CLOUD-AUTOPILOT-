"""Explicit local workload model served by real, authenticated loopback HTTP apps.

Replica count and latency/error projections are simulation state, not containers or
production request statistics. CPU/memory observations describe this Python process.
"""

import asyncio
import os
import secrets
import threading
import time
import uuid
from typing import Any, Literal

import psutil
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, model_validator


class FaultConfig(BaseModel):
    """Bounded lab-only faults; unsupported inputs cannot report success."""
    fault_type: Literal["cpu_stress", "latency", "error_burst", "crash"]
    duration_sec: int = Field(default=30, ge=1, le=120)
    intensity: float = Field(default=1.0, ge=0, le=10000, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid_intensity(self) -> "FaultConfig":
        if self.fault_type == "error_burst" and self.intensity > 100:
            raise ValueError("error_burst intensity must be a percentage between 0 and 100")
        if self.fault_type == "cpu_stress" and self.intensity > 1:
            raise ValueError("cpu_stress intensity must be between 0 and 1")
        return self


def create_microservice_app(
    service_name: str, port: int, dependencies: list[str] | None = None,
    mutation_token: str | None = None,
) -> FastAPI:
    """Build one lab service; only its manager holds the mutation credential."""
    app = FastAPI(title=f"CORTEX Sandbox — {service_name}", version="2.0.0")
    start_time = time.time()
    dependencies = dependencies or []
    expected_token = mutation_token or secrets.token_urlsafe(32)
    lock = threading.RLock()
    state: dict[str, Any] = {
        "status": "UP", "ready": True, "replicas": 1, "revision": 0,
        "instance_id": uuid.uuid4().hex, "request_count": 0, "error_count": 0,
        "base_latency_ms": 45.0, "active_faults": {},
        "extra_latency_ms": 0.0, "error_injection_pct": 0.0,
    }
    process = psutil.Process(os.getpid())

    def authorize(authorization: str | None = Header(default=None)) -> None:
        supplied = authorization.removeprefix("Bearer ") if authorization else ""
        if not supplied or not secrets.compare_digest(supplied, expected_token):
            raise HTTPException(status_code=401, detail="Sandbox manager authorization required")

    def identity() -> dict[str, Any]:
        return {
            "service": service_name, "sandbox": True, "simulated": True,
            "instance_id": state["instance_id"],
            "version": f'{state["instance_id"]}:{state["revision"]}',
            "replicas": state["replicas"],
        }

    @app.get("/")
    def root() -> dict[str, Any]:
        with lock:
            return {**identity(), "status": state["status"], "port": port}

    @app.get("/health")
    def health(response: Response) -> dict[str, Any]:
        with lock:
            if state["status"] != "UP":
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                **identity(), "status": state["status"], "ready": state["ready"],
                "uptime_seconds": round(time.time() - start_time, 1),
            }

    @app.get("/ready")
    def ready(response: Response) -> dict[str, Any]:
        with lock:
            is_ready = state["ready"] and state["status"] == "UP"
            if not is_ready:
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {**identity(), "ready": is_ready, "dependencies": dependencies}

    def snapshot() -> dict[str, Any]:
        with lock:
            uptime = max(time.time() - start_time, 0.001)
            try:
                cpu: float | None = process.cpu_percent(interval=None)
                memory: float | None = process.memory_percent()
            except (psutil.Error, OSError):
                cpu, memory = None, None
            return {
                **identity(), "status": state["status"], "metrics_available": True,
                "source": "sandbox_model", "measurement_scope": "local_workload_model",
                "process_metrics_scope": "shared_python_process",
                "rps": round(state["request_count"] / uptime, 3),
                "observed_requests": state["request_count"],
                "observed_errors": state["error_count"],
                "error_rate_pct": 100.0 if state["status"] == "DOWN" else state["error_injection_pct"],
                "p95_latency_ms": 30000.0 if state["status"] == "DOWN" else round(state["base_latency_ms"] + state["extra_latency_ms"], 2),
                "cpu_percent": cpu, "memory_percent": memory, "timestamp": time.time(),
                "active_faults": list(state["active_faults"]),
            }

    @app.get("/metrics/json")
    def metrics_json() -> dict[str, Any]:
        """Return explicitly modeled SLO values and observed process counters."""
        return snapshot()

    @app.get("/metrics")
    def metrics_prometheus() -> Response:
        """Expose model names in Prometheus format without claiming a Prometheus backend."""
        current = snapshot()
        names = {
            "sandbox_modeled_latency_ms": "p95_latency_ms",
            "sandbox_modeled_error_rate_pct": "error_rate_pct",
            "sandbox_configured_replicas": "replicas",
            "sandbox_observed_requests_total": "observed_requests",
            "sandbox_process_cpu_percent": "cpu_percent",
            "sandbox_process_memory_percent": "memory_percent",
        }
        lines = ['# Local sandbox model; these are not production SLO measurements.']
        for metric, key in names.items():
            if current[key] is not None:
                lines.append(f'{metric}{{service="{service_name}",simulated="true"}} {current[key]}')
        return Response(content="\n".join(lines) + "\n", media_type="text/plain")

    @app.get("/work")
    async def work(response: Response) -> dict[str, Any]:
        """Optional real HTTP workload showing the configured lab delay/error model."""
        with lock:
            state["request_count"] += 1
            sequence = state["request_count"]
            delay = (state["base_latency_ms"] + state["extra_latency_ms"]) / 1000.0
            failed = state["status"] != "UP" or (sequence * 37 % 100) < state["error_injection_pct"]
        await asyncio.sleep(delay)
        with lock:
            if failed:
                state["error_count"] += 1
                response.status_code = 503
            return {**identity(), "status": "FAILED" if failed else "OK"}

    @app.post("/scale", dependencies=[Depends(authorize)])
    def scale(replicas: int = Query(ge=1, le=50)) -> dict[str, Any]:
        with lock:
            state["replicas"] = replicas
            state["base_latency_ms"] = max(8.0, 45.0 / replicas)
            state["revision"] += 1
            return {**identity(), "status": "SCALED", "operation": "sandbox_replica_model_update"}

    def reset_faults() -> None:
        state["status"] = "UP"
        state["ready"] = True
        state["active_faults"].clear()
        state["extra_latency_ms"] = 0.0
        state["error_injection_pct"] = 0.0
        state["revision"] += 1

    @app.post("/restart", dependencies=[Depends(authorize)])
    def restart() -> dict[str, Any]:
        with lock:
            reset_faults()
            return {**identity(), "status": "RESTARTED", "operation": "sandbox_state_reset"}

    @app.post("/fault/inject", dependencies=[Depends(authorize)])
    def inject_fault(fault: FaultConfig) -> dict[str, Any]:
        with lock:
            fault_id = uuid.uuid4().hex
            state["active_faults"][fault.fault_type] = {**fault.model_dump(), "id": fault_id}
            state["revision"] += 1
            if fault.fault_type == "latency":
                state["extra_latency_ms"] = fault.intensity
            elif fault.fault_type == "error_burst":
                state["error_injection_pct"] = fault.intensity
            elif fault.fault_type == "crash":
                state["status"], state["ready"] = "DOWN", False
            elif fault.fault_type == "cpu_stress":
                def burn_cpu() -> None:
                    stop_at = time.monotonic() + fault.duration_sec
                    while time.monotonic() < stop_at:
                        with lock:
                            active = state["active_faults"].get("cpu_stress", {}).get("id") == fault_id
                        if not active:
                            return
                        deadline = time.monotonic() + 0.01 * fault.intensity
                        while time.monotonic() < deadline:
                            sum(value * value for value in range(100))
                        time.sleep(0.01 * (1.0 - fault.intensity))
                threading.Thread(target=burn_cpu, daemon=True, name=f"lab-cpu-{service_name}").start()
            return {**identity(), "injected_fault": fault.fault_type, "status": "APPLIED"}

    @app.post("/fault/clear", dependencies=[Depends(authorize)])
    def clear_faults() -> dict[str, Any]:
        with lock:
            reset_faults()
            return {**identity(), "status": "FAULTS_CLEARED"}

    return app
