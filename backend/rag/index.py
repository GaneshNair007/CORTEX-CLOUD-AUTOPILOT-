"""Single persistent Chroma adapter with lazy model loading and explicit failures."""
import os
from pathlib import Path
from threading import RLock
from typing import Any
from backend.retrieval.models import IndexDocument
from backend.config.environment import load_environment

load_environment()

COLLECTION_NAME = "sre_knowledge_base"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_DB_DIR = Path(os.environ.get("CORTEX_CHROMA_DIR", Path(__file__).parent / "chroma_db"))


class SemanticUnavailable(RuntimeError):
    """Semantic index is missing, incompatible, or unreachable."""


class ChromaIndex:
    def __init__(self, path: Path = CHROMA_DB_DIR):
        self.path = path
        self._client = None
        self._embedding = None
        self._lock = RLock()

    def client(self):
        with self._lock:
            if self._client is None:
                import chromadb
                from chromadb.config import Settings
                self._client = chromadb.PersistentClient(path=str(self.path), settings=Settings(anonymized_telemetry=False))
            return self._client

    def embedding(self):
        with self._lock:
            if self._embedding is None:
                runtime = os.environ.get("CORTEX_EMBEDDING_RUNTIME", "sentence_transformers")
                if runtime == "onnx":
                    from backend.rag.onnx_embedding import LowMemoryMiniLM
                    self._embedding = LowMemoryMiniLM(preferred_providers=["CPUExecutionProvider"])
                elif runtime == "sentence_transformers":
                    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
                    self._embedding = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME, device="cpu")
                else:
                    raise ValueError("CORTEX_EMBEDDING_RUNTIME must be onnx or sentence_transformers")
            return self._embedding

    def collection(self):
        try:
            collection = self.client().get_collection(COLLECTION_NAME, embedding_function=None)
            if (collection.metadata or {}).get("schema_version") != 2:
                raise SemanticUnavailable("index schema incompatible; run python -m backend.rag.rebuild_index")
            return self.client().get_collection(COLLECTION_NAME, embedding_function=self.embedding())
        except SemanticUnavailable:
            raise
        except Exception as exc:
            raise SemanticUnavailable(f"semantic index unavailable ({type(exc).__name__})") from exc

    def query(self, query: str, where: dict[str, Any], limit: int) -> list[tuple[IndexDocument, float]]:
        try:
            with self._lock:
                collection = self.collection()
                if not collection.count():
                    return []
                result = collection.query(query_texts=[query], n_results=min(limit, collection.count()),
                                          where=where, include=["documents", "metadatas", "distances"])
            return [(IndexDocument(id=doc_id, text=doc, metadata=meta), max(0., min(1., 1 - float(distance))))
                    for doc_id, doc, meta, distance in zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0])]
        except SemanticUnavailable:
            raise
        except Exception as exc:
            raise SemanticUnavailable(f"semantic query failed ({type(exc).__name__})") from exc

    def upsert(self, documents: list[IndexDocument], revision: int) -> None:
        if not documents:
            return
        try:
            with self._lock:
                collection = self.collection()
                for offset in range(0, len(documents), 100):
                    batch = documents[offset:offset + 100]
                    collection.upsert(ids=[d.id for d in batch], documents=[d.text for d in batch], metadatas=[d.metadata for d in batch])
                # Chroma rejects hnsw:space in modify(), even if unchanged. The
                # cosine index configuration is fixed when the collection is built.
                metadata = {k: v for k, v in (collection.metadata or {}).items() if not k.startswith("hnsw:")}
                collection.modify(metadata={**metadata, "index_revision": revision})
        except SemanticUnavailable:
            raise
        except Exception as exc:
            raise SemanticUnavailable(f"semantic upsert failed ({type(exc).__name__})") from exc


index = ChromaIndex()
