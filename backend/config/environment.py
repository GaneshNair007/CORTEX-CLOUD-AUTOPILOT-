"""One environment source for API and module CLIs; process values take precedence."""
from pathlib import Path
from dotenv import load_dotenv


def load_environment() -> None:
    """Load only backend/.env; PYTHON_DOTENV_DISABLED isolates test processes."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
