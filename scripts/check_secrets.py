"""Fail CI if potential secrets are committed outside of documented example files."""
from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALLOWED_PATH_PATTERNS = [
    "*.md",
    "*test*",
    "*/node_modules/*",
    "*/.git/*",
    "*/coverage/*",
    "*/dist/*",
    "*/__pycache__/*",
    "*.lock",
]

# Example/placeholder values that are safe to keep in the repo.
SAFE_VALUE_PATTERNS = [
    re.compile(r"\b(x+|y+|z+|-+|_+|\*+)\b", re.IGNORECASE),
    re.compile(r"your[-_].*", re.IGNORECASE),
    re.compile(r"example", re.IGNORECASE),
    re.compile(r"changeme", re.IGNORECASE),
    re.compile(r"<[^>]+>"),
    re.compile(r"\$\{[^}]*\}"),
    re.compile(r"\{\{[^}]*\}\}"),
    re.compile(r"ci-test-secret"),
    re.compile(r"dummy", re.IGNORECASE),
    re.compile(r"placeholder", re.IGNORECASE),
    re.compile(r"sample[_-]?key", re.IGNORECASE),
    re.compile(r"localhost|\b127\.0\.0\.1\b|\b0\.0\.0\.0\b"),
]

SECRET_RULES = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----")),
    ("Supabase service key", re.compile(r"\bsupabase_service_key\s*[=:]\s*['\"](?!$)[^'\"]{20,}['\"]", re.IGNORECASE)),
    ("Stripe key", re.compile(r"\bsk_live_[0-9a-zA-Z]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}\b")),
    ("JWT hard-coded secret", re.compile(r"(?i)\bjwt_secret(?:_key)?\s*[:=]\s*['\"][^'\"$\{]{16,}['\"]")),
    ("Generic API secret assignment", re.compile(r"(?i)\b(api_secret|secret_key|client_secret|password)\b\s*[:=]\s*['\"](?!\s*['\"])(?![^'\"]*(?:example|changeme|placeholder|dummy|\$\{))[^'\"]{12,}['\"]")),
]


def is_allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(f"/{rel}", pat) for pat in ALLOWED_PATH_PATTERNS)


def value_looks_safe(line: str) -> bool:
    return any(p.search(line) for p in SAFE_VALUE_PATTERNS)


def main() -> int:
    findings: list[str] = []
    scanned = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or is_allowed(path):
            continue
        if path.suffix.lower() not in {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
            ".env", ".toml", ".cfg", ".ini", ".sh", ".ps1", ".sql", ".conf",
            ".cjs", ".mjs", ".html", "",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), start=1):
            if value_looks_safe(line):
                continue
            for label, pattern in SECRET_RULES:
                if pattern.search(line):
                    findings.append(
                        f"{path.relative_to(ROOT).as_posix()}:{lineno}: {label}"
                    )

    if findings:
        print("SECRET SCAN FAILED - potential credentials detected:\n")
        for finding in findings:
            print(f"  {finding}")
        print("\nRemove the secret, move it to an untracked .env file, or add a documented exception.")
        return 1

    print(f"Secret scan passed ({scanned} files scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
