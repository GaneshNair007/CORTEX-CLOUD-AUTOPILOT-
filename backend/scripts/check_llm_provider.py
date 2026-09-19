"""CORTEX LLM provider configuration doctor.

Usage:
    python backend/scripts/check_llm_provider.py
    python backend/scripts/check_llm_provider.py --live

The default mode performs NO paid inference request. It only validates the
local environment configuration. ``--live`` performs one intentionally tiny
request through the existing CORTEX LLMClient and prints provider/model/latency
without ever printing the API key.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _masked(value: str | None) -> str:
    if not value:
        return "NOT SET"
    if len(value) <= 8:
        return "SET (hidden)"
    return f"SET ({value[:3]}...{value[-4:]}, hidden)"


def _load_env_file_if_present() -> None:
    """Load backend/.env without requiring python-dotenv.

    Existing process environment variables always win. This parser intentionally
    supports only simple KEY=VALUE lines, which is enough for the documented
    CORTEX configuration.
    """
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def inspect_config() -> tuple[bool, list[str]]:
    _load_env_file_if_present()

    mode = (os.environ.get("LLM_MODE") or "auto").lower()
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

    print("\nCORTEX LLM PROVIDER CHECK")
    print("=" * 64)
    print(f"LLM_MODE          : {mode}")
    print(f"GEMINI_API_KEY    : {_masked(gemini_key)}")
    print(f"OPENAI_API_KEY    : {_masked(openai_key)}")
    print(f"OPENAI_BASE_URL   : {openai_base}")
    print(f"OPENAI_MODEL      : {openai_model}")
    print(f"GEMINI_MODEL      : {gemini_model}")
    print("=" * 64)

    errors: list[str] = []
    warnings: list[str] = []

    cheaper = "cheaperinference.com" in openai_base.lower()

    if gemini_key and gemini_key.startswith("ci_live_"):
        errors.append(
            "A CheaperInference ci_live_* key is assigned to GEMINI_API_KEY. "
            "Move it to OPENAI_API_KEY and set LLM_MODE=openai."
        )

    if cheaper:
        if mode != "openai":
            errors.append(
                "CheaperInference is OpenAI-compatible, so LLM_MODE must be 'openai'."
            )
        if not openai_key:
            errors.append("OPENAI_API_KEY is required for CheaperInference.")
        elif not openai_key.startswith("ci_live_"):
            warnings.append(
                "OPENAI_API_KEY does not look like a ci_live_* CheaperInference key. "
                "This may still be intentional, but verify the credential."
            )
        if not openai_base.rstrip("/").endswith("/v1"):
            warnings.append(
                "CheaperInference base URL normally ends with /v1: "
                "https://api.cheaperinference.com/v1"
            )

    if mode == "gemini":
        if not gemini_key:
            errors.append("LLM_MODE=gemini requires GEMINI_API_KEY or GOOGLE_API_KEY.")
        elif gemini_key.startswith("ci_live_"):
            errors.append("ci_live_* is not a direct Google Gemini credential.")

    if mode == "openai" and not openai_key:
        errors.append("LLM_MODE=openai requires OPENAI_API_KEY.")

    if mode == "auto":
        warnings.append(
            "LLM_MODE is not explicit. CORTEX will auto-detect a provider from available keys. "
            "For deployments, set LLM_MODE explicitly."
        )

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR:   {error}")

    if errors:
        print("\nRESULT: CONFIGURATION INVALID")
        return False, errors

    print("\nRESULT: CONFIGURATION LOOKS VALID")
    if cheaper:
        print(f"Provider: CheaperInference (OpenAI-compatible) / model={openai_model}")
    elif mode == "gemini":
        print(f"Provider: Direct Google Gemini / model={gemini_model}")
    elif mode == "openai":
        print(f"Provider: OpenAI-compatible / model={openai_model}")
    else:
        print(f"Provider mode: {mode}")
    return True, []


def live_test() -> int:
    ok, _ = inspect_config()
    if not ok:
        return 2

    print("\nLIVE TEST")
    print("-" * 64)
    print("Sending one tiny inference request. This may consume provider credit.")

    try:
        from llm.client import LLMClient, LLMError

        client = LLMClient()
        started = time.perf_counter()
        result = client.generate(
            "Reply with exactly CORTEX_OK and nothing else.",
            system="This is a connectivity test. Follow the requested exact output.",
            temperature=0.0,
            max_tokens=16,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        text = str(result.get("text", "")).strip()

        print(f"Provider mode : {client.mode}")
        print(f"Model         : {client.model}")
        print(f"Latency       : {elapsed_ms:.1f} ms")
        print(f"Response      : {text[:120]}")

        if "CORTEX_OK" in text:
            print("RESULT        : LIVE PROVIDER CALL SUCCESS")
            return 0

        print("RESULT        : PROVIDER RESPONDED, BUT TEST TEXT WAS UNEXPECTED")
        return 1
    except Exception as exc:
        print(f"RESULT        : LIVE PROVIDER CALL FAILED")
        print(f"Error         : {exc}")
        return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the CORTEX LLM provider configuration.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Perform one tiny live inference request (may consume provider credit).",
    )
    args = parser.parse_args()

    if args.live:
        return live_test()

    ok, _ = inspect_config()
    print("\nNo network inference call was made. Use --live to test the provider itself.")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
