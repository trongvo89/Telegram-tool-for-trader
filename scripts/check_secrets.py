#!/usr/bin/env python3
"""Fail CI if likely credential values appear in tracked files.

Catches the specific class of mistake where a real Telegram bot token or
32-char hex API key gets checked into .env.example or similar. Placeholder
values (REPLACE_WITH_*, CHANGE_ME, xxxx...) are allowed.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TELEGRAM_TOKEN = re.compile(r"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b")
HEX_KEY_32 = re.compile(r"\b[a-f0-9]{32}\b")

PLACEHOLDER_MARKERS = ("REPLACE_WITH_", "CHANGE_ME", "YOUR_", "xxxx", "stub")

SKIP_PREFIXES = (".git/", "__pycache__/", ".venv/", "node_modules/", "dist/", "build/")
SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".whl")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], check=True, capture_output=True, text=True
    ).stdout
    return [line for line in out.splitlines() if line]


def looks_like_placeholder(value: str) -> bool:
    return any(marker in value for marker in PLACEHOLDER_MARKERS)


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        text = path.read_text(errors="ignore")
    except (OSError, UnicodeDecodeError):
        return findings
    for i, line in enumerate(text.splitlines(), start=1):
        if looks_like_placeholder(line):
            continue
        for pattern, label in ((TELEGRAM_TOKEN, "telegram-token"), (HEX_KEY_32, "32-hex-key")):
            m = pattern.search(line)
            if m:
                findings.append(f"{path}:{i}  [{label}] {m.group(0)[:6]}...")
    return findings


def main() -> int:
    all_findings: list[str] = []
    for f in tracked_files():
        if f.startswith(SKIP_PREFIXES) or f.endswith(SKIP_SUFFIXES):
            continue
        if f == "scripts/check_secrets.py":
            continue
        all_findings.extend(scan_file(Path(f)))

    if all_findings:
        print("Potential credentials detected in tracked files:")
        print()
        for line in all_findings:
            print(f"  {line}")
        print()
        print(
            "If this is a real secret, ROTATE the credential immediately and move "
            "the value to a git-ignored .env file. If it's a false positive, adjust "
            "scripts/check_secrets.py allow-list."
        )
        return 1

    print("No credentials detected in tracked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
