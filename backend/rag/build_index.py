"""Legacy index command redirected to the intentional schema-v2 rebuild."""
from pathlib import Path
from backend.rag.documents import incident_document, runbook_document, load_sources
from backend.rag.rebuild_index import main as build_chroma_index


def parse_incident(file_path: Path) -> tuple:
    document = incident_document(file_path)
    return document.id, document.text, document.metadata


def parse_runbook(file_path: Path) -> tuple:
    document = runbook_document(file_path)
    return document.id, document.text, document.metadata


def load_all_documents() -> tuple:
    docs = load_sources()
    incidents = sum(d.metadata['document_type'] == 'incident' for d in docs)
    return [d.id for d in docs], [d.text for d in docs], [d.metadata for d in docs], incidents, len(docs) - incidents


if __name__ == '__main__':
    build_chroma_index()
