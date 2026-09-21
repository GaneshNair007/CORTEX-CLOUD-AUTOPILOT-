"""Isolated SQL/logs and a private local lab; never touch an operator's services."""
import os
import tempfile
from pathlib import Path
import pytest

TEST_DATA = Path(tempfile.mkdtemp(prefix="cortex-tests-"))
os.environ["CORTEX_DATA_DIR"] = str(TEST_DATA)
os.environ["CORTEX_CHROMA_DIR"] = str(TEST_DATA / "chroma")
os.environ["CORTEX_PUBLIC_READS"] = "true"
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
for name in ("LLM_PRIMARY_PROVIDER", "LLM_PROVIDER", "NVIDIA_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CHEAPERINFERENCE_API_KEY"):
    os.environ.pop(name, None)
os.environ["LLM_MODE"] = "heuristic"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["DOCKER_HOST"] = "tcp://127.0.0.1:1"

# Set provider and ports before test-module imports instantiate the gateway.
from sandbox.manager import sandbox_manager
for spec in sandbox_manager.specs.values():
    spec["port"] += 20000
from backend.providers import set_active_provider, LocalSandboxProvider
set_active_provider(LocalSandboxProvider())


@pytest.fixture(scope="session", autouse=True)
def isolated_lab():
    sandbox_manager.start_all()
    yield
    sandbox_manager.stop_all()
