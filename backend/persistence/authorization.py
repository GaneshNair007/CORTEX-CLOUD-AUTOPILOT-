"""Durable, single-use approval records and shared governance state.

SQL is authoritative. Approval consumption uses a compare-and-set transaction;
an approval is never an instruction to skip current policy evaluation.
"""
import hashlib
import json
import time
from collections.abc import MutableMapping
from datetime import datetime, timezone
from sqlalchemy import Table, Column, String, Float, Text, select, update, delete
from backend.persistence.database import engine
from backend.persistence.models import Base
from backend.models.proposals import ApprovalRecord, ActionProposal

approvals = Table("authorization_tokens", Base.metadata,
    Column("id", String, primary_key=True), Column("status", String, nullable=False),
    Column("expires", Float, nullable=False), Column("binding", String, nullable=False),
    Column("payload", Text, nullable=False))
governance = Table("governance_settings", Base.metadata,
    Column("id", String, primary_key=True), Column("payload", Text, nullable=False))


def binding(record: ApprovalRecord | ActionProposal) -> str:
    """Bind all executable inputs and the proposal version, excluding prose."""
    data = {key: getattr(record, key) for key in (
        "proposal_id", "incident_id", "action_type", "target", "params", "state_version")}
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ApprovalStore(MutableMapping):
    """Mapping compatibility with durable transitions and atomic consumption."""
    def __init__(self, database=engine):
        self.database = database
        approvals.create(database, checkfirst=True)

    def __getitem__(self, key: str) -> ApprovalRecord:
        with self.database.connect() as conn:
            row = conn.execute(select(approvals).where(approvals.c.id == key)).mappings().first()
        if row is None:
            raise KeyError(key)
        record = ApprovalRecord.model_validate_json(row["payload"])
        record.status = row["status"]
        if record.status in {"PENDING", "APPROVED"} and row["expires"] <= time.time():
            record.status = "EXPIRED"
        return record

    def __setitem__(self, key: str, value: ApprovalRecord) -> None:
        values = dict(id=key, status=value.status, expires=value.expires_at.timestamp(),
                      binding=binding(value), payload=value.model_dump_json())
        with self.database.begin() as conn:
            conn.execute(approvals.insert().values(**values))

    def __delitem__(self, key: str) -> None:
        with self.database.begin() as conn:
            conn.execute(delete(approvals).where(approvals.c.id == key))

    def __iter__(self):
        with self.database.connect() as conn:
            return iter(list(conn.execute(select(approvals.c.id)).scalars()))

    def __len__(self):
        return sum(1 for _ in self)

    def resolve(self, key: str, approved: bool, actor: str) -> ApprovalRecord | None:
        record = self.get(key)
        if record is None or record.status != "PENDING":
            return record
        record.status = "APPROVED" if approved else "REJECTED"
        record.approver = actor
        record.resolved_at = datetime.now(timezone.utc)
        with self.database.begin() as conn:
            conn.execute(update(approvals).where(approvals.c.id == key,
                approvals.c.status == "PENDING", approvals.c.expires > time.time()).values(
                status=record.status, payload=record.model_dump_json()))
        return self.get(key)

    def consume(self, key: str, proposal: ActionProposal, resource_version: str) -> bool:
        record = self.get(key)
        if record is None or record.resource_version != resource_version:
            return False
        with self.database.begin() as conn:
            result = conn.execute(update(approvals).where(
                approvals.c.id == key, approvals.c.status == "APPROVED",
                approvals.c.expires > time.time(), approvals.c.binding == binding(proposal)
            ).values(status="CONSUMED"))
            return result.rowcount == 1


def get_governance() -> dict:
    """Read current shared state, including changes made by another worker."""
    governance.create(engine, checkfirst=True)
    with engine.connect() as conn:
        payload = conn.execute(select(governance.c.payload).where(governance.c.id == "global")).scalar()
    state = json.loads(payload) if payload else {"autonomy_level": 2, "kill_switch_engaged": False}
    with engine.connect() as conn:
        for row in conn.execute(select(governance).where(governance.c.id != "global")).mappings():
            state[row["id"]] = json.loads(row["payload"])
    return state


def set_governance(key: str, value) -> None:
    from sqlalchemy.dialects.sqlite import insert
    governance.create(engine, checkfirst=True)
    with engine.begin() as conn:
        stmt = insert(governance).values(id=key, payload=json.dumps(value))
        conn.execute(stmt.on_conflict_do_update(index_elements=["id"], set_={"payload": stmt.excluded.payload}))
