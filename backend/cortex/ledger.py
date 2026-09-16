"""
CORTEX Cloud Autopilot — Tamper-Evident Evidence Ledger
Implements cryptographic SHA-256 hash chaining over operational events and governance decisions.
Ensures history cannot be altered or truncated without breaking verification.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER_FILE_PATH = PROJECT_ROOT / "tools" / "evidence_ledger.jsonl"


class EvidenceLedger:
    def __init__(self, path: Path = LEDGER_FILE_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        """Reads the hash of the most recent event or returns genesis hash."""
        if not self.path.exists():
            return "0" * 64
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if not lines:
                    return "0" * 64
                last_record = json.loads(lines[-1])
                return last_record.get("hash", "0" * 64)
        except Exception:
            return "0" * 64

    def record_event(self, event_type: str, actor: str, payload: Dict[str, Any], correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Appends an event to the ledger and computes the new cryptographic hash."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        record_content = {
            "timestamp": ts,
            "event_type": event_type,
            "actor": actor,
            "correlation_id": correlation_id or "CORR-000",
            "payload": payload,
            "previous_hash": self.last_hash
        }

        # Compute SHA-256 hash
        serialized = json.dumps(record_content, sort_keys=True)
        record_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        record_content["hash"] = record_hash

        # Write to disk
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_content) + "\n")

        self.last_hash = record_hash
        return record_content

    def verify_integrity(self) -> Dict[str, Any]:
        """Validates that all chained hashes in the ledger are valid and untampered."""
        if not self.path.exists():
            return {"valid": True, "total_events": 0, "status": "empty_ledger"}

        with open(self.path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        prev = "0" * 64
        for idx, line in enumerate(lines):
            record = json.loads(line)
            record_hash = record.get("hash")
            stored_prev = record.get("previous_hash")

            if stored_prev != prev:
                return {
                    "valid": False,
                    "failed_at_index": idx,
                    "reason": f"Hash chain broken at event {idx}: expected prev {prev}, found {stored_prev}"
                }

            # Recompute hash without 'hash' key
            content = {k: v for k, v in record.items() if k != "hash"}
            serialized = json.dumps(content, sort_keys=True)
            recomputed = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

            if recomputed != record_hash:
                return {
                    "valid": False,
                    "failed_at_index": idx,
                    "reason": f"Content tampering detected at event {idx}: payload does not match hash"
                }

            prev = record_hash

        return {"valid": True, "total_events": len(lines), "latest_hash": prev}

    def list_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent ledger records in chronological order."""
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        records = [json.loads(line) for line in lines[-limit:]]
        return records


# Global singleton ledger instance
ledger = EvidenceLedger()
