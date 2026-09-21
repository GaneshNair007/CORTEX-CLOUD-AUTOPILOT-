"""SQL source of truth, transactional memory outbox, and SQLite FTS5 BM25.

No incident files are scanned per query. Filter values and FTS tokens are bound,
and field names can only originate in the server's filter builder.
"""
import hashlib
import json
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from sqlalchemy import Column, Integer, String, Text, text
from sqlalchemy.engine import Connection, Engine
from backend.persistence.models import Base
from .models import IndexDocument
from .normalization import tokens


class KnowledgeDocumentRecord(Base):
    __tablename__ = "knowledge_documents"
    id = Column(String(256), primary_key=True)
    document = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    index_state = Column(String(16), nullable=False, default="PENDING", index=True)


class IncidentMemoryRecord(Base):
    __tablename__ = "incident_memories"
    id = Column(String(256), primary_key=True)
    incident_id = Column(String(128), nullable=False, index=True)
    memory_status = Column(String(32), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    updated_at = Column(String(64), nullable=False)


class KnowledgeRevision(Base):
    __tablename__ = "knowledge_revision"
    id = Column(Integer, primary_key=True)
    revision = Column(Integer, nullable=False, default=0)


FILTER_FIELDS = frozenset("schema_version deleted deprecated tenant_id document_type verified environment environment_scope timestamp_epoch service technology_primary failure_mode resource_type memory_status".split())


def sql_filter(where: dict[str, Any], params: dict[str, Any]) -> str:
    """Translate the same safe internal filter used by Chroma into bound SQL."""
    expressions = []
    for key, value in where.items():
        if key in ("$and", "$or"):
            joiner = " AND " if key == "$and" else " OR "
            expressions.append("(" + joiner.join(sql_filter(v, params) for v in value) + ")")
            continue
        if key not in FILTER_FIELDS:
            raise ValueError(f"unsupported internal filter field: {key}")
        field = f"json_extract(k.metadata_json, '$.{key}')"
        operators = value if isinstance(value, dict) else {"$eq": value}
        for op, expected in operators.items():
            if op in ("$in", "$nin"):
                placeholders = []
                for v in expected:
                    name = f"p{len(params)}"
                    params[name] = v
                    placeholders.append(f":{name}")
                expressions.append(f"{field} {'NOT IN' if op == '$nin' else 'IN'} ({','.join(placeholders)})")
            else:
                symbol = {"$eq": "=", "$ne": "!=", "$gte": ">=", "$lte": "<="}.get(op)
                if not symbol:
                    raise ValueError("unsupported internal filter operator")
                name = f"p{len(params)}"
                params[name] = expected
                expressions.append(f"{field} {symbol} :{name}")
    return " AND ".join(expressions) or "1=1"


class KnowledgeRepository:
    def __init__(self, engine: Engine):
        self.engine = engine
        self._lock = RLock()
        if engine.dialect.name != "sqlite":
            raise ValueError("Current lexical adapter requires SQLite FTS5; configure an adapter before changing databases")
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(id UNINDEXED, title, document, signatures)"))
            conn.execute(text("INSERT OR IGNORE INTO knowledge_revision(id, revision) VALUES (1, 0)"))

    @property
    def revision(self) -> int:
        with self.engine.connect() as conn:
            return int(conn.execute(text("SELECT revision FROM knowledge_revision WHERE id=1")).scalar_one())

    def _upsert(self, conn: Connection, document: IndexDocument) -> None:
        metadata = json.dumps(document.metadata, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256((document.text + metadata).encode()).hexdigest()
        old = conn.execute(text("SELECT content_hash FROM knowledge_documents WHERE id=:id"), {"id": document.id}).scalar()
        if old == digest:
            return
        conn.execute(text("""INSERT INTO knowledge_documents(id,document,metadata_json,content_hash,index_state)
            VALUES (:id,:document,:metadata,:digest,'PENDING') ON CONFLICT(id) DO UPDATE SET
            document=excluded.document, metadata_json=excluded.metadata_json,
            content_hash=excluded.content_hash, index_state='PENDING'"""),
            {"id": document.id, "document": document.text, "metadata": metadata, "digest": digest})
        conn.execute(text("DELETE FROM knowledge_fts WHERE id=:id"), {"id": document.id})
        conn.execute(text("INSERT INTO knowledge_fts(id,title,document,signatures) VALUES (:id,:title,:document,:signatures)"),
                     {"id": document.id, "title": document.metadata.get("title", document.id), "document": document.text,
                      "signatures": " ".join(tokens(document.text + " " + metadata))})
        conn.execute(text("UPDATE knowledge_revision SET revision=revision+1 WHERE id=1"))

    def upsert(self, documents: list[IndexDocument]) -> None:
        with self._lock, self.engine.begin() as conn:
            for document in documents:
                self._upsert(conn, document)

    def write_memory(self, document: IndexDocument, payload: dict[str, Any]) -> None:
        """Persist lifecycle evidence and its pending index document atomically."""
        with self._lock, self.engine.begin() as conn:
            conn.execute(text("""INSERT INTO incident_memories(id,incident_id,memory_status,payload_json,updated_at)
                VALUES (:id,:incident,:status,:payload,:now) ON CONFLICT(id) DO UPDATE SET
                memory_status=excluded.memory_status,payload_json=excluded.payload_json,updated_at=excluded.updated_at"""),
                {"id": document.id, "incident": payload["incident_id"], "status": document.metadata["memory_status"],
                 "payload": json.dumps(payload, default=str), "now": datetime.now(timezone.utc).isoformat()})
            self._upsert(conn, document)

    def mark_indexed(self, documents: list[IndexDocument]) -> None:
        """Do not acknowledge a concurrent newer version of a document."""
        with self.engine.begin() as conn:
            for document in documents:
                metadata = json.dumps(document.metadata, sort_keys=True, ensure_ascii=False)
                digest = hashlib.sha256((document.text + metadata).encode()).hexdigest()
                conn.execute(text("UPDATE knowledge_documents SET index_state='INDEXED' WHERE id=:id AND content_hash=:digest"),
                             {"id": document.id, "digest": digest})

    def documents(self, pending_only: bool = False) -> list[IndexDocument]:
        # Used only for migration/replay, never normal candidate generation.
        with self.engine.connect() as conn:
            rows = conn.execute(text("SELECT id, document, metadata_json FROM knowledge_documents" +
                                     (" WHERE index_state='PENDING'" if pending_only else "") + " ORDER BY id"))
            return [IndexDocument(id=r.id, text=r.document, metadata=json.loads(r.metadata_json)) for r in rows]

    def lexical_search(self, query: str, where: dict[str, Any], limit: int) -> list[tuple[IndexDocument, float]]:
        terms = tokens(query)[:64]
        if not terms:
            return []
        match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        params: dict[str, Any] = {"match": match, "limit": limit}
        predicate = sql_filter(where, params)
        with self.engine.connect() as conn:
            rows = conn.execute(text(f"""SELECT k.id,k.document,k.metadata_json,bm25(knowledge_fts,0,3,1,2) AS rank
                FROM knowledge_fts JOIN knowledge_documents k ON knowledge_fts.id=k.id
                WHERE knowledge_fts MATCH :match AND {predicate} ORDER BY rank,k.id LIMIT :limit"""), params).all()
        if not rows:
            return []
        best = max(-float(r.rank) for r in rows) or 1
        return [(IndexDocument(id=r.id, text=r.document, metadata=json.loads(r.metadata_json)),
                 max(0., min(1., -float(r.rank) / best))) for r in rows]

    def authoritative_documents(self, ids: list[str], where: dict[str, Any]) -> dict[str, IndexDocument]:
        """Re-check SQL visibility/trust after vector lookup, including pending changes."""
        if not ids:
            return {}
        params: dict[str, Any] = {f"id{i}": value for i, value in enumerate(ids)}
        placeholders = ",".join(f":id{i}" for i in range(len(ids)))
        predicate = sql_filter(where, params)
        with self.engine.connect() as conn:
            rows = conn.execute(text(f"SELECT k.id,k.document,k.metadata_json FROM knowledge_documents k WHERE k.id IN ({placeholders}) AND {predicate}"), params)
            return {r.id: IndexDocument(id=r.id, text=r.document, metadata=json.loads(r.metadata_json)) for r in rows}
