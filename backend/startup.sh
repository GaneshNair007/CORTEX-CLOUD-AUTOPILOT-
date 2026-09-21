#!/bin/sh
# Run from the repository root regardless of the launch directory.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(dirname -- "$SCRIPT_DIR")
cd "$REPO_DIR"

: "${CORTEX_DATA_DIR:=$SCRIPT_DIR/data}"
: "${CORTEX_CHROMA_DIR:=$CORTEX_DATA_DIR/chroma}"
export CORTEX_DATA_DIR CORTEX_CHROMA_DIR
mkdir -p "$CORTEX_DATA_DIR" "$CORTEX_CHROMA_DIR"

# The API lifespan checks schema/count and replays pending SQL index writes.
# One worker owns the local sandbox, SQLite approval state and Chroma collection.
exec python -m uvicorn backend.api_server:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1