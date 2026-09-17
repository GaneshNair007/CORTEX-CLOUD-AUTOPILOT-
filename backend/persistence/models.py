"""
CORTEX Cloud Autopilot — Relational Persistence Models (SQLAlchemy)
Stores incidents, action proposals, approvals, execution audits, and idempotency records.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, index=True)
    service = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False)
    title = Column(String(256), nullable=False)
    root_cause = Column(Text, nullable=True)
    status = Column(String(32), default="OPEN", index=True)
    raw_telemetry = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


class OperationRecord(Base):
    __tablename__ = "operations"

    proposal_id = Column(String(64), primary_key=True, index=True)
    action_type = Column(String(64), nullable=False, index=True)
    target = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="PROPOSED", index=True)
    risk_score = Column(Integer, default=0)
    parameters_json = Column(Text, nullable=True)
    guard_decision = Column(String(32), nullable=True)
    execution_result_json = Column(Text, nullable=True)
    verification_outcome = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    executed_at = Column(DateTime, nullable=True)


class ApprovalRecordDB(Base):
    __tablename__ = "approvals"

    approval_id = Column(String(64), primary_key=True, index=True)
    proposal_id = Column(String(64), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    target = Column(String(64), nullable=False)
    risk_score = Column(Integer, default=0)
    reason = Column(Text, nullable=False)
    status = Column(String(32), default="PENDING", index=True)
    approver = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)


class IdempotencyRecordDB(Base):
    __tablename__ = "idempotency_keys"

    idempotency_key = Column(String(128), primary_key=True, index=True)
    operation_id = Column(String(64), nullable=False)
    action_type = Column(String(64), nullable=False)
    target = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    result_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
