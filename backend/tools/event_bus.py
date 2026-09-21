"""
AI SRE System - Event Bus & Event Timeline Engine
Provides a thread-safe event bus for publishing agent timeline events (incident detection,
diagnosis, memory retrieval, action execution, resolution) to an in-memory queue
and persisting them to `tools/events.jsonl`.

Public Interface:
    def emit_event(event: dict) -> None
    def get_events() -> list[dict]
    def clear_events() -> None

Example Usage:
    from tools.event_bus import emit_event, get_events

    emit_event({
        "type": "incident_detected",
        "payload": {"service": "payment-api", "severity": "P1"}
    })
    
    timeline = get_events()
"""

import sys
import os
import json
import uuid
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tools.event_bus")

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVENTS_FILE_PATH = Path(os.environ["CORTEX_DATA_DIR"]) / "events.jsonl" if os.environ.get("CORTEX_DATA_DIR") else PROJECT_ROOT / "tools" / "events.jsonl"

# Thread-safe in-memory store
_event_lock = threading.Lock()
_event_queue: List[Dict[str, Any]] = []


def _persist_event(event: Dict[str, Any]) -> None:
    """
    Appends an event dictionary to `tools/events.jsonl` in JSON Lines format.

    Args:
        event: Dictionary payload of the event.
    """
    try:
        EVENTS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENTS_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Failed to persist event to file '{EVENTS_FILE_PATH}': {e}")


def emit_event(event: Dict[str, Any]) -> None:
    """
    Publishes an event to the thread-safe event bus queue and persists it to disk.

    Args:
        event: Dictionary containing event type and payload.
               Example: {"type": "incident_detected", "payload": {"service": "payment-api"}}
    """
    # 1. Graceful Validation
    if not isinstance(event, dict):
        logger.warning(f"Invalid event emitted. Expected dict, got {type(event).__name__}.")
        return

    event_type = event.get("type")
    if not event_type or not isinstance(event_type, str):
        logger.warning("Event missing valid string 'type' field. Event ignored.")
        return

    from backend.llm.sanitizer import sanitize_payload
    payload = sanitize_payload(event.get("payload", {}))
    if not isinstance(payload, dict):
        logger.warning(f"Event payload for type '{event_type}' must be a dictionary. Converting to dict.")
        payload = {"data": str(payload)}

    # 2. Enrich Event Metadata
    enriched_event: Dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "payload": payload
    }

    # 3. Thread-Safe Store & File Append
    with _event_lock:
        _event_queue.append(enriched_event)
        _persist_event(enriched_event)

    logger.info(f"Emitted event [{enriched_event['event_id'][:8]}] type='{event_type}'")


def get_events() -> List[Dict[str, Any]]:
    """
    Returns a copy of all events currently stored in the in-memory queue.

    Returns:
        List of event dictionaries in chronological order.
    """
    with _event_lock:
        return list(_event_queue)


def clear_events() -> None:
    """
    Clears all events from the in-memory event queue.
    Note: Does not delete the historical events file on disk.
    """
    with _event_lock:
        _event_queue.clear()
    logger.info("In-memory event queue cleared.")


def run_cli_demo() -> None:
    """
    CLI demonstration emitting a complete AI SRE incident lifecycle timeline.
    """
    print("\n" + "=" * 65)
    print("        AI SRE System - Event Bus Timeline CLI Demo")
    print("=" * 65)

    clear_events()

    # Define a realistic AI SRE remediation lifecycle
    timeline_events = [
        {
            "type": "incident_detected",
            "payload": {
                "service": "payment-api",
                "severity": "P1",
                "symptom": "HTTP 504 Gateway Timeout spike on /v1/checkout"
            }
        },
        {
            "type": "diagnosis_started",
            "payload": {
                "agent": "DiagnosticAgent-01",
                "phase": "Log Analysis & Topology Inspection"
            }
        },
        {
            "type": "memory_retrieved",
            "payload": {
                "query": "Payment Gateway API high latency and 504 timeouts",
                "matched_incident_id": "INC-2026-005",
                "matched_runbook": "RB-004_api_gateway_504_timeouts.md",
                "confidence_score": 0.92
            }
        },
        {
            "type": "action_executed",
            "payload": {
                "action": "restart_service",
                "service": "payment-api",
                "status": "success",
                "latency_ms": 340
            }
        },
        {
            "type": "incident_resolved",
            "payload": {
                "service": "payment-api",
                "resolution_time_seconds": 18,
                "status": "Healthy (p99 latency 120ms)"
            }
        }
    ]

    print("\nEmitting lifecycle events...\n")
    for ev in timeline_events:
        emit_event(ev)

    events = get_events()

    print("\n" + "-" * 65)
    print("                      LIVE EVENT TIMELINE")
    print("-" * 65)

    for idx, e in enumerate(events, 1):
        ts = e["timestamp"].split("T")[1][:8]
        ev_type = e["type"].upper()
        payload = e["payload"]
        print(f"[{idx}] {ts} UTC  |  Type: {ev_type:<20}")
        print(f"     Payload: {json.dumps(payload)}")
        print()

    print("-" * 65)
    print(f"Total events in memory: {len(events)}")
    print(f"Events persisted to:    '{EVENTS_FILE_PATH}'")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_cli_demo()
