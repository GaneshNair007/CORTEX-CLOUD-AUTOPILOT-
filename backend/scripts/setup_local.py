"""Create local configuration and missing role tokens without revealing secrets."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets

from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parents[1]
TOKEN_NAMES = ("CORTEX_ADMIN_TOKEN", "CORTEX_OPERATOR_TOKEN", "CORTEX_VIEWER_TOKEN")


def setup_local(env_path: Path, template_path: Path) -> list[str]:
    """Preserve existing values; append only missing or blank authentication tokens.

    The exclusive lock prevents simultaneous setup runs from generating conflicting
    values. Existing provider credentials are never changed or returned.
    """
    lock_path = env_path.with_name(env_path.name + ".setup.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(descriptor)
        if not env_path.exists():
            with env_path.open("x", encoding="utf-8", newline="\n") as target:
                target.write(template_path.read_text(encoding="utf-8"))
            if os.name != "nt":
                env_path.chmod(0o600)
        config = dotenv_values(env_path, interpolate=False)
        present = [config[name] for name in TOKEN_NAMES if config.get(name)]
        if any(len(value.strip()) < 32 for value in present):
            raise ValueError("Existing role token is too short; replace it locally with at least 32 characters")
        if len(present) != len(set(present)):
            raise ValueError("Existing role tokens must be distinct; replace duplicated values locally")
        generated = {name: secrets.token_urlsafe(32) for name in TOKEN_NAMES if not config.get(name)}
        if generated:
            with env_path.open("a", encoding="utf-8", newline="\n") as target:
                target.write("\n# Locally generated role credentials; do not share or commit.\n")
                for name, value in generated.items():
                    target.write(f"{name}={value}\n")
                target.flush()
                os.fsync(target.fileno())
        return list(generated)
    finally:
        lock_path.unlink(missing_ok=True)


def main() -> int:
    """Initialize backend/.env using safe, idempotent local defaults."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        generated = setup_local(BACKEND / ".env", BACKEND / ".env.example")
    except FileExistsError:
        print("Local setup is locked by another run; retry after it finishes.")
        return 2
    except (OSError, ValueError) as exc:
        print(str(exc) if isinstance(exc, ValueError) else "Unable to write local configuration; check file permissions.")
        return 2
    print("Local configuration ready. Role tokens created: " + (", ".join(generated) or "none; existing values preserved"))
    print("Provider credentials were preserved. Add a fresh NVIDIA key only in backend/.env before live inference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
