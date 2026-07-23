#!/usr/bin/env python3
"""Validate a Conventional Commit message without printing its contents."""

from __future__ import annotations

import re
import sys
from pathlib import Path

TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"
HEADER = re.compile(
    rf"^(?:{TYPES})(?:\([^)\r\n]+\))?!?:\s+\S.*$"
)


def fail(message: str) -> None:
    print(f"invalid conventional commit: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate-conventional-commit.py MESSAGE_FILE")

    message = Path(sys.argv[1]).read_text(encoding="utf-8")
    lines = message.splitlines()
    if not lines:
        fail("message is empty")

    header = lines[0]
    if len(header) > 72:
        fail("header exceeds 72 characters")
    if not HEADER.fullmatch(header):
        fail("header must match <type>(<optional-scope>)<optional-!>: <description>")

    print("conventional_commit=valid")
    print(f"header_length={len(header)}")


if __name__ == "__main__":
    main()
