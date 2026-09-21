"""Manage explicitly simulated services on real, private loopback HTTP endpoints."""

import copy
import secrets
import socket
import threading
import time
from typing import Any

import httpx
import uvicorn

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
    """Own local service lifecycles; validate responses instead of assuming success."""
    _instance: "SandboxManager | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.servers: dict[str, uvicorn.Server] = {}
        self.threads: dict[str, threading.Thread] = {}
        self.running = False
        self.specs = copy.deepcopy(SERVICE_SPECS)
        self._mutation_token = secrets.token_urlsafe(32)
        self._lifecycle_lock = threading.RLock()
        self._client = httpx.Client(timeout=2.0, trust_env=False)

    @classmethod
    def get_instance(cls) -> "SandboxManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.2)
            return connection.connect_ex(("127.0.0.1", port)) == 0

    def _url(self, name: str, path: str) -> str:
        return f'http://127.0.0.1:{self.specs[name]["port"]}{path}'

    def _client_ready(self) -> httpx.Client:
        with self._lifecycle_lock:
            if self._client.is_closed:
                self._client = httpx.Client(timeout=2.0, trust_env=False)
            return self._client

    def start_service(self, name: str) -> bool:
        """Start only owned lab apps; an unrelated listener is not a successful start."""
        if name not in self.specs:
            return False
        with self._lifecycle_lock:
            port = self.specs[name]["port"]
            if self._is_port_in_use(port):
                return name in self.servers and self.get_health(name).get("sandbox") is True
            app = create_microservice_app(
                name, port, self.specs[name]["dependencies"], mutation_token=self._mutation_token,
            )
            config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
            server = uvicorn.Server(config)
            self.servers[name] = server
            thread = threading.Thread(target=server.run, daemon=True, name=f"sandbox-{name}")
            self.threads[name] = thread
            thread.start()
            for _ in range(40):
                if self._is_port_in_use(port) and self.get_health(name).get("status") == "UP":
                    return True
                if not thread.is_alive():
                    break
                time.sleep(0.05)
            server.should_exit = True
            return False

    def start_all(self) -> dict[str, bool]:
        """Return the actual readiness of each requested service."""
        result = {name: self.start_service(name) for name in self.specs}
        self.running = all(result.values())
        return result

    def stop_all(self) -> None:
        """Stop only this manager's servers and wait for their listening sockets to close."""
        for server in list(self.servers.values()):
            server.should_exit = True
        for thread in list(self.threads.values()):
            thread.join(timeout=3.0)
        self.servers.clear()
        self.threads.clear()
        self.running = False
        self._client.close()

    def _mutate(self, name: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if name not in self.specs:
            return {"status": "FAILED", "error": "UNKNOWN_SERVICE", "service": name}
        try:
            response = self._client_ready().post(
                self._url(name, path), headers={"Authorization": f"Bearer {self._mutation_token}"}, **kwargs,
            )
            if response.status_code != 200:
                return {"status": "FAILED", "error": "SANDBOX_HTTP_ERROR", "http_status": response.status_code, "service": name}
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("service") != name or payload.get("sandbox") is not True:
                return {"status": "FAILED", "error": "INVALID_SANDBOX_RESPONSE", "service": name}
            return payload
        except (httpx.HTTPError, ValueError) as error:
            return {"status": "FAILED", "error": type(error).__name__, "service": name}

    def restart_service(self, name: str) -> dict[str, Any]:
        """Reset an owned sandbox service; revive only after observing a successful start."""
        result = self._mutate(name, "/restart")
        if result.get("status") == "RESTARTED":
            health = self.get_health(name)
            if health.get("status") == "UP" and health.get("version") == result.get("version"):
                return {**result, "status": "SUCCESS", "action": "sandbox_state_reset"}
            return {"status": "FAILED", "error": "RESTART_NOT_CONFIRMED", "service": name}
        if name in self.specs and not self._is_port_in_use(self.specs[name]["port"]):
            if self.start_service(name):
                health = self.get_health(name)
                if health.get("status") == "UP":
                    return {**health, "status": "SUCCESS", "action": "sandbox_process_revived"}
        return result

    def scale_service(self, name: str, replicas: int) -> dict[str, Any]:
        """Change a modeled replica count; no extra OS processes/containers are implied."""
        if isinstance(replicas, bool) or not isinstance(replicas, int) or not 1 <= replicas <= 50:
            return {"status": "FAILED", "error": "INVALID_REPLICA_COUNT", "service": name}
        return self._mutate(name, "/scale", params={"replicas": replicas})

    def get_health(self, name: str) -> dict[str, Any]:
        """Read a registered service identity and readiness, without healthy defaults."""
        if name not in self.specs:
            return {"status": "UNKNOWN", "service": name, "error": "UNKNOWN_SERVICE"}
        try:
            response = self._client_ready().get(self._url(name, "/health"))
            if response.status_code not in (200, 503):
                return {"status": "UNKNOWN", "service": name, "error": "HEALTH_HTTP_ERROR", "http_status": response.status_code}
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("service") != name or payload.get("sandbox") is not True:
                return {"status": "UNKNOWN", "service": name, "error": "UNRECOGNIZED_SERVICE"}
            if response.status_code == 503:
                payload["status"] = "DOWN"
            return payload
        except (httpx.HTTPError, ValueError) as error:
            return {"status": "DOWN", "service": name, "error": type(error).__name__, "probe_available": False}

    def get_metrics(self, name: str) -> dict[str, Any]:
        """Read explicit workload-model observations; unavailable values stay absent."""
        missing = {"service": name, "status": "UNKNOWN", "metrics_available": False, "source": "unavailable", "simulated": True}
        if name not in self.specs:
            return {**missing, "error": "UNKNOWN_SERVICE"}
        try:
            response = self._client_ready().get(self._url(name, "/metrics/json"))
            if response.status_code != 200:
                return {**missing, "error": "METRICS_HTTP_ERROR", "http_status": response.status_code}
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("service") != name or payload.get("sandbox") is not True:
                return {**missing, "error": "UNRECOGNIZED_SERVICE"}
            return {**payload, "simulated": True, "source": "sandbox_model"}
        except (httpx.HTTPError, ValueError) as error:
            return {**missing, "error": type(error).__name__}

    def get_all_statuses(self) -> dict[str, dict[str, Any]]:
        """Compatibility inventory containing observed health, not generated status."""
        return {name: self.get_health(name) for name in self.specs}

    def inject_fault(self, name: str, fault_type: str, duration_sec: int = 30, intensity: float = 1.0) -> dict[str, Any]:
        """Submit a bounded fault through the manager-authenticated local endpoint."""
        return self._mutate(
            name, "/fault/inject",
            json={"fault_type": fault_type, "duration_sec": duration_sec, "intensity": intensity},
        )

    def clear_faults(self, name: str) -> dict[str, Any]:
        """Clear a lab fault when the caller has passed gateway authorization."""
        return self._mutate(name, "/fault/clear")


sandbox_manager = SandboxManager.get_instance()
