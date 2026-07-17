#!/usr/bin/env python3
"""Resolve a configured non-secret user path for portable skills."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.agent_paths import artifact_directory, configured_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="kind", required=True)

    artifact = subparsers.add_parser("artifact", help="print a configured artifact directory")
    artifact.add_argument("name")
    artifact.add_argument("--create", action="store_true", help="create the directory if missing")

    path = subparsers.add_parser("path", help="print a configured named path")
    path.add_argument("name")

    args = parser.parse_args()
    try:
        if args.kind == "artifact":
            print(artifact_directory(args.name, create=args.create))
        else:
            print(configured_path(args.name))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
