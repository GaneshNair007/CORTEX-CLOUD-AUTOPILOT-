"""Legacy action facade. Every action is delegated to the shared CORTEX gateway."""
import os
from pathlib import Path
from typing import Any

AUDIT_LOG_PATH = Path(os.environ.get("CORTEX_DATA_DIR", Path(__file__).parent)) / "audit.log"


def execute_action(action_type: str, params: dict[str, Any]) -> dict:
    """Return actual authorization/execution state; never simulate success."""
    from backend.interfaces import execute_action as guarded_action
    return guarded_action(action_type, params)
