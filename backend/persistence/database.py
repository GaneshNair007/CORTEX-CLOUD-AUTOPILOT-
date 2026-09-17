"""
CORTEX Cloud Autopilot — Database Engine & Persistence Layer
Provides thread-safe relational persistence backed by SQLite.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

try:
    from backend.persistence.models import (
        Base,
        IncidentRecord,
        OperationRecord,
        ApprovalRecordDB,
        IdempotencyRecordDB
    )
except ImportError:
    from persistence.models import (
        Base,
        IncidentRecord,
        OperationRecord,
        ApprovalRecordDB,
        IdempotencyRecordDB
    )

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cortex_control_plane.db"
os.makedirs(DB_PATH.parent, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initializes all database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


class DatabaseManager:
    """Manages transactional database operations for the control plane."""

    def __init__(self):
        init_db()

    def get_session(self) -> Session:
        return SessionFactory()

    # --- Incidents ---
    def record_incident(
        self,
        incident_id: str,
        service: str,
        severity: str,
        title: str,
        root_cause: Optional[str] = None,
        raw_telemetry: Optional[Dict[str, Any]] = None
    ) -> IncidentRecord:
        with self.get_session() as session:
            rec = session.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
            if not rec:
                rec = IncidentRecord(
                    id=incident_id,
                    service=service,
                    severity=severity,
                    title=title,
                    root_cause=root_cause,
                    status="OPEN",
                    raw_telemetry=json.dumps(raw_telemetry) if raw_telemetry else None,
                    detected_at=datetime.now(timezone.utc)
                )
                session.add(rec)
            else:
                rec.severity = severity
                rec.title = title
                rec.root_cause = root_cause or rec.root_cause
                if raw_telemetry:
                    rec.raw_telemetry = json.dumps(raw_telemetry)
            session.commit()
            session.refresh(rec)
            return rec

    def resolve_incident(self, incident_id: str) -> bool:
        with self.get_session() as session:
            rec = session.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
            if rec:
                rec.status = "RESOLVED"
                rec.resolved_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False

    def list_incidents(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            q = session.query(IncidentRecord)
            if status:
                q = q.filter(IncidentRecord.status == status)
            records = q.order_by(IncidentRecord.detected_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "service": r.service,
                    "severity": r.severity,
                    "title": r.title,
                    "root_cause": r.root_cause,
                    "status": r.status,
                    "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                    "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None
                }
                for r in records
            ]

    # --- Operations ---
    def record_operation(
        self,
        proposal_id: str,
        action_type: str,
        target: str,
        status: str = "PROPOSED",
        risk_score: int = 0,
        parameters: Optional[Dict[str, Any]] = None,
        guard_decision: Optional[str] = None
    ):
        with self.get_session() as session:
            rec = session.query(OperationRecord).filter(OperationRecord.proposal_id == proposal_id).first()
            if not rec:
                rec = OperationRecord(
                    proposal_id=proposal_id,
                    action_type=action_type,
                    target=target,
                    status=status,
                    risk_score=risk_score,
                    parameters_json=json.dumps(parameters) if parameters else None,
                    guard_decision=guard_decision,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(rec)
            else:
                rec.status = status
                rec.guard_decision = guard_decision or rec.guard_decision
            session.commit()

    def update_operation_result(
        self,
        proposal_id: str,
        status: str,
        execution_result: Optional[Dict[str, Any]] = None,
        verification_outcome: Optional[str] = None
    ):
        with self.get_session() as session:
            rec = session.query(OperationRecord).filter(OperationRecord.proposal_id == proposal_id).first()
            if rec:
                rec.status = status
                rec.executed_at = datetime.now(timezone.utc)
                if execution_result:
                    rec.execution_result_json = json.dumps(execution_result)
                if verification_outcome:
                    rec.verification_outcome = verification_outcome
                session.commit()

    def list_operations(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            records = session.query(OperationRecord).order_by(OperationRecord.created_at.desc()).limit(limit).all()
            return [
                {
                    "proposal_id": r.proposal_id,
                    "action_type": r.action_type,
                    "target": r.target,
                    "status": r.status,
                    "risk_score": r.risk_score,
                    "guard_decision": r.guard_decision,
                    "verification_outcome": r.verification_outcome,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "executed_at": r.executed_at.isoformat() if r.executed_at else None
                }
                for r in records
            ]

    # --- Approvals ---
    def record_approval(
        self,
        approval_id: str,
        proposal_id: str,
        action_type: str,
        target: str,
        risk_score: int,
        reason: str,
        expires_at: datetime
    ):
        with self.get_session() as session:
            rec = ApprovalRecordDB(
                approval_id=approval_id,
                proposal_id=proposal_id,
                action_type=action_type,
                target=target,
                risk_score=risk_score,
                reason=reason,
                status="PENDING",
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc)
            )
            session.add(rec)
            session.commit()

    def resolve_approval(self, approval_id: str, status: str, approver: str = "operator") -> bool:
        with self.get_session() as session:
            rec = session.query(ApprovalRecordDB).filter(ApprovalRecordDB.approval_id == approval_id).first()
            if rec:
                rec.status = status
                rec.approver = approver
                rec.resolved_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False

    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            now = datetime.now(timezone.utc)
            records = session.query(ApprovalRecordDB).filter(
                ApprovalRecordDB.status == "PENDING",
                ApprovalRecordDB.expires_at > now
            ).all()
            return [
                {
                    "approval_id": r.approval_id,
                    "proposal_id": r.proposal_id,
                    "action_type": r.action_type,
                    "target": r.target,
                    "risk_score": r.risk_score,
                    "reason": r.reason,
                    "status": r.status,
                    "expires_at": r.expires_at.isoformat()
                }
                for r in records
            ]


db_manager = DatabaseManager()
