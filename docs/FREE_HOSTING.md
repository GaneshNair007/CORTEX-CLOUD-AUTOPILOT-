# Free hackathon hosting

Frontend: Vercel. Backend: Render free, one worker, local sandbox enabled.
The default local embedding runtime remains SentenceTransformers. Free hosting
sets CORTEX_EMBEDDING_RUNTIME=onnx and installs backend/requirements-free.txt.
Chroma supplies the same all-MiniLM-L6-v2 export; CPU inference uses one thread
and batch size one. Run python -m backend.scripts.prepare_embeddings during build.
Changing runtimes for an existing index requires python -m backend.rag.rebuild_index
with the API stopped. The migration retains the old collection as backup.

No persistent disk is configured. SQLite lifecycle and Chroma learned memories
reset when Render restarts or sleeps; canonical incident/runbook sources rebuild.
This is a sandbox demonstration, not durable production infrastructure.

Never put credentials in .env.example or Git. The NVIDIA credential committed
in 01c51d5 must be revoked; removing it from the current tree does not remove it
from history. Set a fresh NVIDIA_API_KEY directly in the Render environment.
Mutations require private role tokens; public reads expose demo state only.
