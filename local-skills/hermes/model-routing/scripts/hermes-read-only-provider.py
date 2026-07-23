#!/usr/bin/env python3
"""Adapter that invokes Hermes once for an isolated controller smoke route.

It accepts the controller provider-command protocol on stdin and emits only a
minimal contract response. The child prompt contains no repository contents;
controller telemetry stores only the selected route metadata.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    request = json.loads(sys.stdin.read())
    model = request["model"]
    hermes = os.environ.get("HERMES_BIN", str(Path.home() / ".hermes/hermes-agent/venv/bin/hermes"))
    prompt = (
        "Perform this isolated read-only controller smoke check. "
        "Do not use tools, access files, or make changes. Reply with one concise sentence. "
        f"Role: {request['role']}. Required output field: summary."
    )
    command = [hermes, "--provider", model["provider"], "--model", model["model"], "--safe-mode", "--cli", "-z", prompt]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=request["timeout_seconds"], check=False)
    except subprocess.TimeoutExpired:
        print(json.dumps({"kind": "transport_failure", "category": "timeout"}))
        return 0
    if completed.returncode != 0:
        print(json.dumps({"kind": "transport_failure", "category": "provider_error"}))
        return 0
    print(json.dumps({"kind": "success", "output": {"summary": "Hermes read-only smoke route completed."}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
