"""SQL idempotency claims. Interrupted mutations require reconciliation, never replay."""
import json
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from backend.persistence.database import engine
from backend.persistence.models import IdempotencyRecordDB


class IdempotencyManager:
    def __init__(self, database=engine):
        self.database = database
        self.table = IdempotencyRecordDB.__table__
        self.table.create(database, checkfirst=True)

    def check(self, key: str) -> dict | None:
        with self.database.connect() as conn:
            row = conn.execute(select(self.table).where(self.table.c.idempotency_key == key)).mappings().first()
        if row is None:
            return None
        result = json.loads(row["result_payload"])
        if row["status"] == "RUNNING":
            result["status"] = "BLOCKED"
            result["output"] = {"reason": "Operation in progress or interrupted; reconcile before retry", "outcome": "UNKNOWN"}
        result["original_operation_id"] = row["operation_id"]
        return result

    def reserve(self, key, operation_id, proposal) -> bool:
        from backend.models.proposals import ExecutionResult
        result = ExecutionResult(operation_id=operation_id, proposal_id=proposal.proposal_id,
            action_type=proposal.action_type, target=proposal.target, params=proposal.params,
            status="BLOCKED", idempotency_key=key).model_dump(mode="json")
        try:
            with self.database.begin() as conn:
                conn.execute(self.table.insert().values(idempotency_key=key, operation_id=operation_id,
                    action_type=proposal.action_type, target=proposal.target, status="RUNNING", result_payload=json.dumps(result)))
            return True
        except IntegrityError:
            return False

    def record_execution(self, key, operation_id, action_type, target, result) -> None:
        with self.database.begin() as conn:
            conn.execute(update(self.table).where(self.table.c.idempotency_key == key,
                self.table.c.operation_id == operation_id).values(status=result["status"], result_payload=json.dumps(result)))

    def clear(self) -> None:
        """Test/admin reconciliation only; never exposed as an API endpoint."""
        with self.database.begin() as conn:
            conn.execute(delete(self.table))


idempotency_manager = IdempotencyManager()
