"""
CORTEX Cloud Autopilot — Anti-Thrashing & Cooldown Enforcement
Prevents rapid flapping / oscillation of infrastructure mutations.
"""

import time
import threading
from typing import Dict, Optional, Tuple


class AntiThrashingManager:
    """Tracks per-service mutation timestamps and enforces strict cooldowns."""

    def __init__(self, default_cooldown_seconds: float = 60.0):
        self.default_cooldown = default_cooldown_seconds
        self._last_mutations: Dict[str, float] = {}  # service -> timestamp
        self._last_actions: Dict[str, str] = {}     # service -> action_type
        self._lock = threading.Lock()

    def check_cooldown(self, service: str, required_cooldown: Optional[float] = None) -> Tuple[bool, float]:
        """
        Checks if service is currently in a cooldown window.
        Returns: (can_mutate: bool, remaining_seconds: float)
        """
        cooldown = required_cooldown if required_cooldown is not None else self.default_cooldown
        with self._lock:
            last_time = self._last_mutations.get(service)
            if last_time is None:
                return True, 0.0

            elapsed = time.time() - last_time
            if elapsed < cooldown:
                remaining = round(cooldown - elapsed, 1)
                return False, remaining
            return True, 0.0

    def record_mutation(self, service: str, action_type: str) -> None:
        """Records a successful mutation timestamp."""
        with self._lock:
            self._last_mutations[service] = time.time()
            self._last_actions[service] = action_type

    def reset_cooldown(self, service: str) -> None:
        """Clears cooldown for service (useful in testing)."""
        with self._lock:
            self._last_mutations.pop(service, None)
            self._last_actions.pop(service, None)


anti_thrashing_manager = AntiThrashingManager()
