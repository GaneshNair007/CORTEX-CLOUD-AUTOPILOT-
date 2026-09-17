"""
CORTEX Cloud Autopilot — Retry Policy & Incident Action Budget
Enforces bounded retries with exponential backoff and prevents retry storms
by capping maximum autonomous actions per incident to 3.
"""

import time
import random
from typing import Callable, Any, Dict, Optional, Tuple


class IncidentBudgetTracker:
    """Tracks number of autonomous mutations per incident to prevent retry storms."""

    def __init__(self, max_actions_per_incident: int = 3):
        self.max_actions = max_actions_per_incident
        self._incident_counts: Dict[str, int] = {}

    def can_attempt_action(self, incident_id: str) -> Tuple[bool, int]:
        """Returns (can_attempt, current_count)."""
        count = self._incident_counts.get(incident_id, 0)
        if count >= self.max_actions:
            return False, count
        return True, count

    def increment(self, incident_id: str) -> int:
        count = self._incident_counts.get(incident_id, 0) + 1
        self._incident_counts[incident_id] = count
        return count

    def reset(self, incident_id: str) -> None:
        self._incident_counts.pop(incident_id, None)


class RetryExecutor:
    """Executes safe actions with bounded retries, exponential backoff, and jitter."""

    @staticmethod
    def execute_with_retry(
        func: Callable[[], Dict[str, Any]],
        max_retries: int = 2,
        base_delay_sec: float = 0.5,
        max_delay_sec: float = 4.0
    ) -> Dict[str, Any]:
        attempts = 0
        last_exception = None

        while attempts <= max_retries:
            try:
                result = func()
                if result.get("status") == "SUCCESS":
                    return result
                # If explicitly returned failure and not retryable
                if attempts == max_retries:
                    return result
            except Exception as e:
                last_exception = e
                if attempts == max_retries:
                    return {"status": "FAILED", "error": str(e), "attempts": attempts + 1}

            attempts += 1
            # Exponential backoff with jitter
            backoff = min(max_delay_sec, base_delay_sec * (2 ** (attempts - 1)))
            jitter = random.uniform(0.0, 0.2)
            time.sleep(backoff + jitter)

        return {"status": "FAILED", "error": str(last_exception) if last_exception else "Exceeded max retries"}


incident_budget = IncidentBudgetTracker(max_actions_per_incident=3)
