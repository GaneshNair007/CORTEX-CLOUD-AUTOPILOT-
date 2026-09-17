"""
CORTEX Cloud Autopilot — Resource Action Locks
Enforces mutually exclusive execution locks per target service to prevent
concurrent or conflicting mutations from stepping on each other.
"""

import time
import asyncio
import threading
from typing import Dict, Optional, Set


class ResourceLockManager:
    """Per-resource concurrency lock manager."""

    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._active_holders: Dict[str, str] = {}  # service -> operation_id
        self._meta_lock = threading.Lock()

    def acquire(self, target: str, operation_id: str, timeout_sec: float = 0.5) -> bool:
        """
        Attempts to acquire lock on target resource.
        Returns True if acquired, False if already held by another operation.
        """
        with self._meta_lock:
            if target not in self._locks:
                self._locks[target] = threading.Lock()
            lock = self._locks[target]

        acquired = lock.acquire(timeout=timeout_sec)
        if acquired:
            with self._meta_lock:
                self._active_holders[target] = operation_id
            return True
        return False

    def release(self, target: str, operation_id: str) -> bool:
        """Releases the lock on the target resource if held by operation_id."""
        with self._meta_lock:
            holder = self._active_holders.get(target)
            if holder != operation_id:
                return False

            if target in self._locks:
                try:
                    self._locks[target].release()
                except RuntimeError:
                    pass
                del self._active_holders[target]
                return True
            return False

    def is_locked(self, target: str) -> bool:
        with self._meta_lock:
            return target in self._active_holders

    def get_holder(self, target: str) -> Optional[str]:
        with self._meta_lock:
            return self._active_holders.get(target)


resource_lock_manager = ResourceLockManager()
