# Build from the repository root: docker build -f backend/Dockerfile -t cortex-backend .
FROM python:3.12-slim AS dependencies

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt /tmp/requirements.txt
# Install CPU PyTorch first so sentence-transformers does not pull CUDA packages.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /tmp/requirements.txt
# A failed download fails the build; runtime never silently pretends to have embeddings.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', device='cpu')"

FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 cortex
WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
COPY --from=dependencies --chown=cortex:cortex /opt/huggingface /opt/huggingface
COPY --chown=cortex:cortex backend /app/backend
COPY --chown=cortex:cortex sandbox /app/sandbox
RUN mkdir -p /app/runtime/chroma && chown -R cortex:cortex /app/runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/huggingface \
    HF_HUB_OFFLINE=1 \
    LLM_PRIMARY_PROVIDER=nvidia \
    CORTEX_DATA_DIR=/app/runtime \
    CORTEX_CHROMA_DIR=/app/runtime/chroma \
    CORTEX_START_SANDBOX=false \
    CORTEX_PUBLIC_READS=false \
    PORT=8000
USER cortex
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/healthz', timeout=4)"
CMD ["sh", "backend/startup.sh"]