"""
CORTEX Cloud Autopilot — Sandbox Environment Manager
Manages the local cloud lab of 8 microservices. Runs real uvicorn processes
on designated local ports, exposing live telemetry and health endpoints.
"""

import os
import sys
import time
import socket
import threading
import uvicorn
import httpx
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sandbox.services.service_template import create_microservice_app

SERVICE_SPECS = {
    "api-gateway": {"port": 8010, "dependencies": ["auth-service", "order-service", "payment-service"]},
    "auth-service": {"port": 8011, "dependencies": ["redis"]},
    "payment-service": {"port": 8012, "dependencies": ["postgres"]},
    "order-service": {"port": 8013, "dependencies": ["postgres", "inventory-service"]},
    "inventory-service": {"port": 8014, "dependencies": ["postgres"]},
    "notification-worker": {"port": 8015, "dependencies": ["order-service"]},
    "redis": {"port": 8016, "dependencies": []},
    "postgres": {"port": 8017, "dependencies": []},
}


class SandboxManager:
    _instance: Optional["SandboxManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.servers: Dict[str, uvicorn.Server] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.running = False
        self.specs = SERVICE_SPECS

    @classmethod
    def get_instance(cls) -> "SandboxManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = SandboxManager()
            return cls._instance

    def _is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    def start_service(self, name: str) -> bool:
        """Starts a single microservice on its designated port."""
        if name not in self.specs:
            return False

        port = self.specs[name]["port"]
        deps = self.specs[name]["dependencies"]

        if self._is_port_in_use(port):
            # Already running on this port
            return True

        app = create_microservice_app(name, port, deps)
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
        server = uvicorn.Server(config)
        self.servers[name] = server

        t = threading.Thread(target=server.run, daemon=True, name=f"sandbox-{name}")
        t.start()
        self.threads[name] = t

        # Wait for port to become available
        for _ in range(30):
            if self._is_port_in_use(port):
                return True
            time.sleep(0.05)
        return True

    def start_all(self):
        """Starts all 8 sandbox microservices concurrently."""
        for name in self.specs:
            self.start_service(name)
        self.running = True

    def stop_all(self):
        """Stops all running sandbox microservices."""
        for name, server in list(self.servers.items()):
            server.should_exit = True
        self.servers.clear()
        self.threads.clear()
        self.running = False

    def restart_service(self, name: str) -> Dict[str, Any]:
        """Real restart: resets internal state and faults via HTTP endpoint."""
        if name not in self.specs:
            return {"status": "FAILED", "error": f"Unknown service: {name}"}

        port = self.specs[name]["port"]
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.post(f"http://127.0.0.1:{port}/restart")
                if res.status_code == 200:
                    return {"status": "SUCCESS", "service": name, "action": "restart"}
        except Exception:
            pass

        # If process was dead, revive it
        self.start_service(name)
        return {"status": "SUCCESS", "service": name, "action": "restarted_and_revived"}

    def scale_service(self, name: str, replicas: int) -> Dict[str, Any]:
        """Real scaling: updates active replica count and recalculates latency."""
        if name not in self.specs:
            return {"status": "FAILED", "error": f"Unknown service: {name}"}

        port = self.specs[name]["port"]
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.post(f"http://127.0.0.1:{port}/scale", params={"replicas": replicas})
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}
        return {"status": "SCALED", "service": name, "replicas": replicas}

    def get_health(self, name: str) -> Dict[str, Any]:
        """Queries the real HTTP /health probe of the service."""
        if name not in self.specs:
            return {"status": "UNKNOWN", "error": f"Unknown service {name}"}

        port = self.specs[name]["port"]
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"http://127.0.0.1:{port}/health")
                return res.json()
        except Exception as e:
            return {"status": "DOWN", "service": name, "error": str(e)}

    def get_metrics(self, name: str) -> Dict[str, Any]:
        """Scrapes the real HTTP /metrics/json probe of the service."""
        if name not in self.specs:
            return {"status": "UNKNOWN", "error": f"Unknown service {name}"}

        port = self.specs[name]["port"]
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"http://127.0.0.1:{port}/metrics/json")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            pass

        return {
            "service": name,
            "status": "DOWN",
            "replicas": 0,
            "rps": 0.0,
            "error_rate_pct": 100.0,
            "p95_latency_ms": 30000.0,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "timestamp": time.time(),
        }

    def inject_fault(self, name: str, fault_type: str, duration_sec: int = 30, intensity: float = 1.0) -> Dict[str, Any]:
        """Injects a real chaos fault into the live running service."""
        if name not in self.specs:
            return {"status": "FAILED", "error": f"Unknown service {name}"}

        port = self.specs[name]["port"]
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.post(
                    f"http://127.0.0.1:{port}/fault/inject",
                    json={"fault_type": fault_type, "duration_sec": duration_sec, "intensity": intensity}
                )
                return res.json()
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}


# Global singleton access
sandbox_manager = SandboxManager.get_instance()
