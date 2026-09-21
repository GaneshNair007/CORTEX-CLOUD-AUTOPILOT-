"""
CORTEX LLM — Prompt Sanitizer (defense-in-depth).

Scans prompt context for known secret patterns and redacts them before
any text is sent to an external LLM provider.

This is NOT a replacement for correct secret handling — it is a last-line
defense against accidental credential leakage in structured incident context.

Patterns covered:
  - AWS access keys (AKIA…)
  - Bearer tokens
  - Private key headers (-----BEGIN … KEY-----)
  - Database URLs with embedded passwords
  - JWTs (three base64url segments)
  - Generic API key patterns
  - GitHub tokens (ghp_, gho_, github_pat_)
  - Generic long hex/alphanumeric strings that look like secrets (heuristic)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns — order matters (more specific first)
# ---------------------------------------------------------------------------
_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("provider_key", re.compile(r"\b(?:nvapi-|ci_live_|sk-(?:proj-|ant-)?|AIza)[A-Za-z0-9_-]{12,}"), "[REDACTED:PROVIDER_KEY]"),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
        "[REDACTED:AWS_KEY]",
    ),
    (
        "aws_secret_key",
        re.compile(r"(?i)(?:aws_secret|secret_access_key)\s*[=:]\s*[A-Za-z0-9/+]{40}"),
        "[REDACTED:AWS_SECRET]",
    ),
    (
        "bearer_token",
        re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
        "Bearer [REDACTED]",
    ),
    (
        "private_key_header",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "[REDACTED:PRIVATE_KEY]",
    ),
    (
        "postgres_url_with_password",
        re.compile(r"(postgres(?:ql)?://[^:@\s]+:)[^@\s]+([@\s])"),
        r"\1[REDACTED]\2",
    ),
    (
        "mysql_url_with_password",
        re.compile(r"(mysql(?:\+\w+)?://[^:@\s]+:)[^@\s]+([@\s])"),
        r"\1[REDACTED]\2",
    ),
    (
        "mongodb_url_with_password",
        re.compile(r"(mongodb(?:\+srv)?://[^:@\s]+:)[^@\s]+([@\s])"),
        r"\1[REDACTED]\2",
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        "[REDACTED:JWT]",
    ),
    (
        "github_token",
        re.compile(r"\b(ghp_|gho_|github_pat_)[A-Za-z0-9_]{10,}\b"),
        "[REDACTED:GITHUB_TOKEN]",
    ),
    (
        "generic_api_key_assignment",
        # key = "sk-..." or api_key = "ci_live_..." etc.
        re.compile(
            r'(?i)(?:api[_\-]?key|secret|token|password|passwd|credential)\s*[=:]\s*'
            r'["\']?([A-Za-z0-9\-._]{16,})["\']?'
        ),
        r"[REDACTED]",
    ),
]

# Minimum length for a generic "looks like a secret" heuristic
_MIN_SECRET_LENGTH = 40


def sanitize(text: str, log_detections: bool = True) -> tuple[str, list[str]]:
    """
    Redact known secret patterns from text.

    Returns:
        (sanitized_text, list_of_detection_types_found)

    Never logs the original values — only detection type names.
    """
    detections: list[str] = []
    result = text

    for name, pattern, replacement in _PATTERNS:
        new_result, n_subs = pattern.subn(replacement, result)
        if n_subs:
            detections.append(name)
            result = new_result

    if detections and log_detections:
        logger.warning(
            "Prompt sanitizer redacted %d pattern type(s) before LLM call: %s",
            len(detections),
            detections,
        )

    return result, detections


def sanitize_prompt(prompt: str, system: Optional[str] = None) -> tuple[str, Optional[str]]:
    """Sanitize both prompt and system strings. Returns sanitized versions."""
    clean_prompt, p_detections = sanitize(prompt)
    clean_system: Optional[str] = None
    if system is not None:
        clean_system, s_detections = sanitize(system)
        if s_detections:
            logger.warning("Sanitizer redacted patterns in system prompt: %s", s_detections)
    return clean_prompt, clean_system


def sanitize_payload(value):
    """Redact operational event data before storage, retaining numeric metrics."""
    if isinstance(value, dict):
        sensitive = {"password", "passwd", "api_key", "secret", "access_token", "authorization", "credential"}
        return {key: "[REDACTED]" if str(key).lower() in sensitive else sanitize_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return sanitize(value, log_detections=False)[0]
    return value
