"""Regression tests for writer candidate telemetry and controller commit path."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "execute-writer-candidate.py"
POLICY = Path.home() / ".hermes" / "model-routing.yaml"
PYTHON = sys.executable

WRITER_FIXTURE = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

request = json.loads(sys.stdin.read())
repo = Path(request["execution_spec"]["repository"]["path"])
(repo / "owned.txt").write_text("green", encoding="utf-8")
output = {"summary": "feat(controller): complete " + request["task_id"]}
print(json.dumps({"kind": "success", "output": output}))
"""


def make_manifest(repository: Path, base_commit: str) -> dict:
    return {
        "version": 1,
        "task_id": "task-e2e-001",
        "role": "coder",
        "role_rationale": "Make a controlled change.",
        "mode": "write",
        "repository": {"path": str(repository), "base_commit": base_commit},
        "depends_on": [],
        "ownership": {"files": ["owned.txt"], "directory_prefixes": []},
        "validation_commands": ["test -f owned.txt"],
        "timeout_seconds": 60,
        "output_contract": {"artifact_type": "candidate", "required_fields": ["summary"]},
        "acceptance_criteria": ["Create owned.txt."],
    }


def test_successful_writer_records_telemetry_and_returns_candidate_commit():
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        repository = directory / "repo"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.email", "tests@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Controller tests"], check=True)
        (repository / "README.md").write_text("seed", encoding="utf-8")
        subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repository), "commit", "-qm", "test: seed"], check=True)
        base = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

        manifest_path = directory / "manifest.json"
        writer_path = directory / "writer.py"
        manifest_path.write_text(json.dumps(make_manifest(repository, base)), encoding="utf-8")
        writer_path.write_text(WRITER_FIXTURE, encoding="utf-8")
        writer_path.chmod(0o755)

        result = subprocess.run(
            [PYTHON, str(CONTROLLER), "--manifest", str(manifest_path), "--policy", str(POLICY), "--writer-command", PYTHON, str(writer_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["ok"] is True, report
        assert report["state"] == "candidate_ready", report
        assert report["candidate_commit"]
        assert report["candidate_branch"].startswith("model-routing/task-e2e-001-")
        assert "owned.txt" in report["changed_paths"]
        assert all(item["returncode"] == 0 for item in report["validation"])
