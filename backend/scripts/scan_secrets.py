"""Scan publishable source and staged Git content; never print a credential."""
import re
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = {
    "NVIDIA": r"nvapi-[A-Za-z0-9_-]{20,}",
    "CheaperInference": r"ci_live_[A-Za-z0-9_-]{16,}",
    "Google": r"AIza[A-Za-z0-9_-]{25,}",
    "OpenAI-compatible": r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}",
    "AWS": r"\bAKIA[A-Z0-9]{16}\b",
    "GitHub": r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}",
    "Private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "Assigned secret": r"(?m)^[ \t]*[A-Z_]*(?:API_KEY|SECRET_ACCESS_KEY|OPERATOR_TOKEN|ADMIN_TOKEN)[ \t]*=[ \t]*['\"]?([^\s'\"#]{16,})",
}


def findings(content: str, name: str) -> list[dict]:
    result = []
    for provider, pattern in PATTERNS.items():
        for match in re.finditer(pattern, content):
            value = match.group(0)
            if any(marker in value.lower() for marker in ("your_", "your-", "placeholder", "fake_", "test_", "example", "replace_with", "replaceme")):
                continue
            result.append({"path": name, "line": content.count("\n", 0, match.start()) + 1,
                           "provider": provider, "value": "REDACTED"})
    return result


def scan() -> dict:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    staged = set(subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT).decode().split("\0"))
    detected = []
    checked = 0
    for name in sorted(set(tracked + untracked) - {""}):
        path = ROOT / name
        if not path.is_file() or path.stat().st_size > 4_000_000 or path.suffix in (".db", ".sqlite3", ".bin", ".png", ".jpg", ".woff2"):
            continue
        if path.name == ".env" or name.startswith((".kiro/", "frontend/artifacts/")):
            continue
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        checked += 1
        detected.extend(findings(content, name))
        if name in staged:
            content = subprocess.check_output(["git", "show", f":{name}"], cwd=ROOT).decode("utf-8", errors="replace")
            detected.extend(findings(content, "staged:" + name))
    return {"files_checked": checked, "findings": detected, "status": "PASS" if not detected else "FAIL"}


if __name__ == "__main__":
    report = scan()
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report["findings"]))
