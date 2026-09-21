"""Structured retrieval telemetry contains IDs/counts, never incident text/secrets."""
import logging
import json

logger = logging.getLogger("cortex.retrieval")


def event(name: str, incident_id: str | None, **fields) -> None:
    logger.info(json.dumps({"event": name, "incident_id": incident_id, **fields}, sort_keys=True))
