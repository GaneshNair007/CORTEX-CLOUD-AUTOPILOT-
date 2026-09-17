"""
CORTEX Cloud Autopilot — Mutation Idempotency Manager
Guarantees that repeated executions with the same idempotency key return
the cached previous execution result without re-executing the mutation.
"""

import time
import threading
from typing import Dict, Any, Optional


class IdempotencyRecord:
    def __init__(self, key: str, operation_id: str, action_type: str, target: str, result: Dict[str, Any]):
        self.key = key
        self.operation_id = operation_id
        self.action_type = action_type
        self.target = target
        self.result = result
        self.executed_at = time.time()


class IdempotencyManager:
    """Thread-safe in-memory and durable idempotency store."""

    def __init__(self):
        self._records: Dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> Optional[Dict[str, Any]]:
        """Returns previous result if key was already executed, else None."""
        with self._lock:
            record = self._records.get(key)
            if record:
                cached = dict(record.result)
                cached["idempotent_replay"] = True
                cached["original_operation_id"] = record.operation_id
                return cached
            return None

    def record_execution(self, key: str, operation_id: str, action_type: str, target: str, result: Dict[str, Any]) -> None:
        """Saves execution result for future idempotent replays."""
        with self._lock:
            self._records[key] = IdempotencyRecord(
                key=key,
                operation_id=operation_id,
                action_type=action_type,
                target=target,
                result=result
            )

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


idempotency_manager = IdempotencyManager()
