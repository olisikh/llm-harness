"""Acceptance tests for the side-effect-free controller contract CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-controller-manifest.py"


def valid_task(*, role: str = "coder", mode: str = "write") -> dict:
    return {
        "version": 1,
        "task_id": "routing-002-contracts",
        "role": role,
        "role_rationale": "The coder owns this bounded implementation.",
        "mode": mode,
        "repository": {"path": "/work/repo", "base_commit": "0123456789abcdef"},
        "depends_on": [],
        "ownership": {"files": ["src/controller.py"], "directory_prefixes": []},
        "validation_commands": ["python -m unittest"],
        "timeout_seconds": 600,
        "output_contract": {"artifact_type": "candidate", "required_fields": ["summary", "changed_paths"]},
        "acceptance_criteria": ["The declared command passes."],
    }


def valid_result(state: str = "candidate_ready") -> dict:
    code = "schema_violation" if state == "validation_failure" else state
    return {
        "version": 1,
        "task_id": "routing-002-contracts",
        "state": state,
        "code": code,
        "summary": "Candidate is ready for controller validation.",
    }


class ValidateControllerManifestTests(unittest.TestCase):
    def run_contract(self, document: dict, *, kind: str = "task") -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / f"{kind}.json"
            manifest_path.write_text(json.dumps(document), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--kind", kind, "--input", str(manifest_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        return result, json.loads(result.stdout)

    def assert_rejected(self, document: dict, code: str, *, kind: str = "task") -> None:
        result, report = self.run_contract(document, kind=kind)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report["ok"])
        self.assertEqual(report["code"], code)
        self.assertIn(f"code={code}", result.stderr)

    def test_valid_writer_manifest_emits_json_and_human_summary(self):
        result, report = self.run_contract(valid_task())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["code"], "ok")
        self.assertEqual(report["kind"], "task")
        self.assertEqual(report["normalized_ownership"], {"files": ["src/controller.py"], "directory_prefixes": []})
        self.assertIn("manifest=valid", result.stderr)

    def test_read_only_manifest_can_omit_writer_validation(self):
        manifest = valid_task(role="researcher", mode="read_only")
        manifest["validation_commands"] = []
        manifest["output_contract"]["artifact_type"] = "findings"
        result, report = self.run_contract(manifest)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ok"])

    def test_result_schema_accepts_every_stable_state(self):
        for state in ("validation_failure", "scope_violation", "candidate_ready", "base_changed", "review_rejected", "locally_integrated"):
            with self.subTest(state=state):
                result, report = self.run_contract(valid_result(state), kind="result")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(report["state"], state)

    def test_rejects_unknown_fields_and_duplicate_json_keys(self):
        manifest = valid_task()
        manifest["provider"] = "must-not-be-here"
        self.assert_rejected(manifest, "unknown_field")
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "duplicate.json"
            manifest_path.write_text('{"version": 1, "version": 1}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--input", str(manifest_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["code"], "duplicate_json_key")

    def test_validator_creates_no_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "task.json"
            source = json.dumps(valid_task())
            manifest_path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--input", str(manifest_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), source)
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()), ["task.json"])

    def test_rejects_malformed_task_id(self):
        manifest = valid_task()
        manifest["task_id"] = "Task 2!"
        self.assert_rejected(manifest, "malformed_task_id")

    def test_rejects_duplicate_and_self_dependencies(self):
        duplicate = valid_task()
        duplicate["depends_on"] = ["routing-001", "routing-001"]
        self.assert_rejected(duplicate, "duplicate_dependency")
        self_dependency = valid_task()
        self_dependency["depends_on"] = [self_dependency["task_id"]]
        self.assert_rejected(self_dependency, "self_dependency")

    def test_rejects_empty_or_traversing_ownership_and_unrestricted_globs(self):
        empty = valid_task()
        empty["ownership"] = {"files": [], "directory_prefixes": []}
        self.assert_rejected(empty, "schema_violation")
        traversal = valid_task()
        traversal["ownership"]["files"] = ["../secrets.txt"]
        self.assert_rejected(traversal, "path_traversal")
        glob = valid_task()
        glob["ownership"]["directory_prefixes"] = ["src/**"]
        self.assert_rejected(glob, "unrestricted_glob")

    def test_rejects_invalid_role_mode_and_unvalidated_writer(self):
        invalid_mode = valid_task(role="researcher", mode="write")
        self.assert_rejected(invalid_mode, "invalid_role_mode")
        missing_validation = valid_task()
        missing_validation["validation_commands"] = []
        self.assert_rejected(missing_validation, "writer_validation_missing")

    def test_normalizes_paths_before_returning_the_contract(self):
        manifest = valid_task()
        manifest["ownership"] = {"files": ["./src//controller.py"], "directory_prefixes": ["docs/./routing"]}
        result, report = self.run_contract(manifest)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["normalized_ownership"], {"files": ["src/controller.py"], "directory_prefixes": ["docs/routing"]})

    def test_fails_closed_for_schema_version_and_invalid_result_state(self):
        wrong_version = valid_task()
        wrong_version["version"] = 2
        self.assert_rejected(wrong_version, "unsupported_schema_version")
        invalid_state = valid_result("pending")
        self.assert_rejected(invalid_state, "schema_violation", kind="result")
        invalid_code = valid_result()
        invalid_code["code"] = "not_a_stable_code"
        self.assert_rejected(invalid_code, "invalid_result_code", kind="result")


if __name__ == "__main__":
    unittest.main()
