"""Recoverable schema migration; run with the API stopped.

Sources and SQL memories are preserved. A verified shadow replaces the active
collection only after indexing succeeds; the previous collection remains as backup.
"""
import json
import uuid
from collections import Counter
from backend.rag.documents import load_sources, make_document
from backend.rag.index import index, ChromaIndex, COLLECTION_NAME
from backend.retrieval.repository import KnowledgeRepository


def rebuild(repository: KnowledgeRepository, semantic: ChromaIndex, *, sources=None) -> dict:
    """Inspect, migrate, verify unique IDs and return actual index statistics."""
    repository.upsert(load_sources() if sources is None else sources)
    client = semantic.client()
    names = {c.name for c in client.list_collections()}
    previous = client.get_collection(COLLECTION_NAME, embedding_function=semantic.embedding()) if COLLECTION_NAME in names else None
    old_schema = (previous.metadata or {}).get("schema_version", 1) if previous else None
    existing_sql_ids = {d.id for d in repository.documents()}
    if previous:
        for offset in range(0, previous.count(), 200):
            page = previous.get(limit=200, offset=offset, include=["documents", "metadatas"])
            imports = []
            for doc_id, content, meta in zip(page["ids"], page["documents"], page["metadatas"]):
                if doc_id not in existing_sql_ids:
                    payload = {**(meta or {}), "id": doc_id, "verified": False, "memory_status": "UNVERIFIED"}
                    imports.append(make_document(payload, content or "", str(payload.get("document_type", "incident")), str(payload.get("filename", ""))))
            repository.upsert(imports)
    docs = repository.documents()
    shadow_name = f"sre_rebuild_{uuid.uuid4().hex}"
    shadow = client.create_collection(shadow_name, embedding_function=semantic.embedding(),
                                     metadata={"hnsw:space": "cosine", "schema_version": 2, "index_revision": repository.revision})
    for offset in range(0, len(docs), 100):
        batch = docs[offset:offset + 100]
        shadow.upsert(ids=[d.id for d in batch], documents=[d.text for d in batch], metadatas=[d.metadata for d in batch])
    actual_ids = set(shadow.get(include=[])['ids'])
    if actual_ids != {d.id for d in docs}:
        raise RuntimeError(f"rebuild verification failed; active collection unchanged; inspect {shadow_name}")
    backup = None
    if previous:
        backup = f"sre_backup_{uuid.uuid4().hex}"
        previous.modify(name=backup)
    try:
        shadow.modify(name=COLLECTION_NAME)
    except Exception:
        if previous:
            previous.modify(name=COLLECTION_NAME)
        raise
    repository.mark_indexed(docs)
    counts = Counter(d.metadata["document_type"] for d in docs)
    return {"incidents": counts["incident"], "runbooks": counts["runbook"], "memories": counts["memory"],
            "total": len(actual_ids), "schema": 2, "previous_schema": old_schema,
            "index_revision": repository.revision, "backup_collection": backup}


def main() -> None:
    from backend.persistence.database import engine
    print(json.dumps(rebuild(KnowledgeRepository(engine), index), indent=2))


if __name__ == "__main__":
    main()
