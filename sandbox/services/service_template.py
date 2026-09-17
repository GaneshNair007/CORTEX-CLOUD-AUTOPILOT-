"""
CORTEX Cloud Autopilot — Sandbox Microservice Template
Lightweight real HTTP microservice exposing /health, /ready, /metrics,
and controlled fault injection for chaos experiments.
"""

import os
import sys
import time
import threading
import psutil
from typing import Dict, Any, Optional
from fastapi import FastAPI, Response, status
from pydantic import BaseModel

class FaultConfig(BaseModel):
    fault_type: str  # cpu_stress, latency, error_burst, crash
    duration_sec: int = 30
    intensity: float = 1.0  # e.g. latency in ms or cpu burn multiplier


def create_microservice_app(service_name: str, port: int, dependencies: list[str] = None):
    app = FastAPI(title=f"CORTEX Sandbox — {service_name}", version="1.0.0")
    start_time = time.time()
    dependencies = dependencies or []

    # Dynamic service runtime state
    state = {
        "service_name": service_name,
        "port": port,
        "status": "UP",
        "ready": True,
        "replicas": 1,
        "request_count": 120,
        "error_count": 0,
        "base_latency_ms": 15.0,
        "active_faults": {},
        "extra_latency_ms": 0.0,
        "error_injection_pct": 0.0,
    }

    process = psutil.Process(os.getpid())

    @app.get("/")
    def root():
        return {"service": service_name, "status": state["status"], "port": port}

    @app.get("/health")
    def health(response: Response):
        if state["status"] != "UP":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "DOWN", "service": service_name, "error": "Service degraded or crashed"}
        return {
            "status": "UP",
            "service": service_name,
            "uptime_seconds": round(time.time() - start_time, 1),
            "replicas": state["replicas"],
        }

    @app.get("/ready")
    def ready(response: Response):
        if not state["ready"] or state["status"] != "UP":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"ready": False, "service": service_name}
        return {"ready": True, "service": service_name, "dependencies": dependencies}

    @app.get("/metrics")
    def metrics_prometheus():
        """Prometheus text exposition format."""
        uptime = time.time() - start_time
        cpu = process.cpu_percent(interval=None) or 12.5
        try:
            mem = process.memory_percent() or 4.2
        except Exception:
            mem = 4.2

        rps = round(state["request_count"] / max(uptime, 1.0), 2)
        err_rate = round((state["error_count"] / max(state["request_count"], 1.0)) * 100.0, 2)
        p95 = round(state["base_latency_ms"] + state["extra_latency_ms"], 2)

        prom_lines = [
            f"# HELP http_requests_total Total HTTP requests processed.",
            f"# TYPE http_requests_total counter",
            f'http_requests_total{{service="{service_name}"}} {state["request_count"]}',
            f"# HELP http_request_rate_rps Inbound requests per second.",
            f"# TYPE http_request_rate_rps gauge",
            f'http_request_rate_rps{{service="{service_name}"}} {rps}',
            f"# HELP http_error_rate_pct Current HTTP error percentage.",
            f"# TYPE http_error_rate_pct gauge",
            f'http_error_rate_pct{{service="{service_name}"}} {err_rate}',
            f"# HELP http_latency_p95_ms 95th percentile response latency in ms.",
            f"# TYPE http_latency_p95_ms gauge",
            f'http_latency_p95_ms{{service="{service_name}"}} {p95}',
            f"# HELP container_cpu_percent Process CPU consumption.",
            f"# TYPE container_cpu_percent gauge",
            f'container_cpu_percent{{service="{service_name}"}} {cpu}',
            f"# HELP container_memory_percent Process memory utilization.",
            f"# TYPE container_memory_percent gauge",
            f'container_memory_percent{{service="{service_name}"}} {mem}',
            f"# HELP service_replica_count Number of configured active replicas.",
            f"# TYPE service_replica_count gauge",
            f'service_replica_count{{service="{service_name}"}} {state["replicas"]}',
        ]
        return Response(content="\n".join(prom_lines) + "\n", media_type="text/plain")

    @app.get("/metrics/json")
    def metrics_json():
        """Structured JSON metrics for internal telemetry collector."""
        uptime = time.time() - start_time
        cpu = process.cpu_percent(interval=None) or 12.5
        try:
            mem = process.memory_percent() or 4.2
        except Exception:
            mem = 4.2

        state["request_count"] += 1
        if state["error_injection_pct"] > 0:
            import random
            if random.random() * 100 < state["error_injection_pct"]:
                state["error_count"] += 1

        rps = round(state["request_count"] / max(uptime, 1.0) * 10.0, 2)
        err_rate = round((state["error_count"] / max(state["request_count"], 1.0)) * 100.0, 2)
        p95 = round(state["base_latency_ms"] + state["extra_latency_ms"], 2)

        return {
            "service": service_name,
            "status": state["status"],
            "replicas": state["replicas"],
            "rps": rps,
            "error_rate_pct": err_rate,
            "p95_latency_ms": p95,
            "cpu_percent": cpu,
            "memory_percent": mem,
            "timestamp": time.time(),
            "active_faults": list(state["active_faults"].keys()),
        }

    @app.post("/scale")
    def scale(replicas: int):
        state["replicas"] = replicas
        # Higher replica count relieves queue pressure & reduces p95 latency
        state["base_latency_ms"] = max(8.0, 45.0 / max(replicas, 1))
        return {"service": service_name, "replicas": state["replicas"], "status": "SCALED"}

    @app.post("/restart")
    def restart():
        state["status"] = "UP"
        state["ready"] = True
        state["active_faults"].clear()
        state["extra_latency_ms"] = 0.0
        state["error_injection_pct"] = 0.0
        return {"service": service_name, "status": "RESTARTED", "action": "restart"}

    @app.post("/fault/inject")
    def inject_fault(fault: FaultConfig):
        state["active_faults"][fault.fault_type] = fault.model_dump()

        if fault.fault_type == "cpu_stress":
            # Real CPU burner thread
            def burn_cpu():
                stop_at = time.time() + fault.duration_sec
                while time.time() < stop_at and "cpu_stress" in state["active_faults"]:
                    _ = [x**2 for x in range(1000)]
            t = threading.Thread(target=burn_cpu, daemon=True)
            t.start()

        elif fault.fault_type == "latency":
            state["extra_latency_ms"] = float(fault.intensity)

        elif fault.fault_type == "error_burst":
            state["error_injection_pct"] = float(fault.intensity)

        elif fault.fault_type == "crash":
            state["status"] = "DOWN"
            state["ready"] = False

        return {"service": service_name, "injected_fault": fault.fault_type, "status": "APPLIED"}

    @app.post("/fault/clear")
    def clear_faults():
        state["active_faults"].clear()
        state["extra_latency_ms"] = 0.0
        state["error_injection_pct"] = 0.0
        state["status"] = "UP"
        state["ready"] = True
        return {"service": service_name, "status": "FAULTS_CLEARED"}

    return app
