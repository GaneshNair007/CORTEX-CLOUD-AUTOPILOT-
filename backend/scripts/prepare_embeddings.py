"""Download and verify the configured embedding model during deployment build."""
from backend.rag.index import index


def main() -> None:
    """Warm the model and validate dimensions before starting the API."""
    vectors = index.embedding()(["PostgreSQL connection pool exhaustion"])
    if len(vectors) != 1 or len(vectors[0]) != 384:
        raise RuntimeError("MiniLM embedding validation failed")
    print("MiniLM cache ready: 384 dimensions")


if __name__ == "__main__":
    main()
