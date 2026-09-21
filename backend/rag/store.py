"""Legacy JSONL compatibility/export store, not the production retrieval path.

Normal retrieval uses backend.retrieval with SQL/FTS and Chroma. Verified memory
is written through IncidentMemoryWriter; these helpers only serve old callers.
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MEMORY_FILE = DATA_DIR / "memory_store.jsonl"


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _corpus() -> list[dict]:
    docs = []
    for path in sorted(DATA_DIR.glob("*.json")):
        docs.extend(json.loads(path.read_text(encoding="utf-8")))
    if MEMORY_FILE.exists():
        for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                docs.append({
                    "id": f"memory-{rec['id']}",
                    "kind": "incident",
                    "title": f"(remembered) {rec['title']}",
                    "text": f"{rec['description']}\nResolved hypothesis: {rec['hypothesis'][:300]}",
                })
    return docs


def retrieve(query: str, k: int) -> list[dict]:
    q = _tokenize(query)
    scored = []
    for doc in _corpus():
        overlap = len(q & _tokenize(f"{doc['title']} {doc['text']}"))
        if overlap:
            scored.append({**doc, "score": overlap / max(len(q), 1)})
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:k]


def remember(record: dict) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
