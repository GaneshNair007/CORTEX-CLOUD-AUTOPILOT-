"""Idempotent index initialization and readiness, outside module import paths."""
from backend.rag.index import COLLECTION_NAME
from .engine import get_engine


def index_status() -> dict:
    try:
        engine = get_engine()
        collection = engine.semantic.client().get_collection(COLLECTION_NAME, embedding_function=None)
        schema = (collection.metadata or {}).get("schema_version")
        count = collection.count()
        return {"status": "ready" if schema == 2 and count > 0 else "degraded", "schema": schema, "documents": count,
                "index_revision": (collection.metadata or {}).get("index_revision"), "sql_revision": engine.repository.revision}
    except Exception as exc:
        return {"status": "degraded", "reason": type(exc).__name__, "semantic_available": False}


def initialize() -> dict:
    """Build absent/incompatible indexes once, otherwise replay pending SQL writes."""
    engine = get_engine()
    if index_status()["status"] != "ready":
        from backend.rag.rebuild_index import rebuild
        rebuild(engine.repository, engine.semantic)
    else:
        from .memory_writer import IncidentMemoryWriter
        IncidentMemoryWriter(engine.repository, engine.semantic).replay_pending()
    return index_status()
