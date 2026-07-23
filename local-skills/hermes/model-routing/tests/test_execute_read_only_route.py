"""Public CLI acceptance tests for deterministic read-only controller routes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "execute-read-only-route.py"
RESULT_VALIDATOR = ROOT / "scripts" / "validate-controller-manifest.py"
POLICY = Path.home() / ".hermes" / "model-routing.yaml"


def read_only_manifest(role: str) -> dict:
    return {
        "version": 1,
        "task_id": "routing-003-read-only",
        "role": role,
        "role_rationale": "The route is read-only and bounded.",
        "mode": "read_only",
        "repository": {"path": "/unused", "base_commit": "0123456789abcdef"},
        "depends_on": [],
        "ownership": {"files": ["docs/report.md"], "directory_prefixes": []},
        "validation_commands": [],
        "timeout_seconds": 60,
        "output_contract": {"artifact_type": "findings", "required_fields": ["summary"]},
        "acceptance_criteria": ["Return one summary."],
    }


PROVIDER_FIXTURE = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

plan_path = Path(sys.argv[1])
plan = json.loads(plan_path.read_text())
request = json.loads(sys.stdin.read())
log = Path(plan[\"log\"])
entries = json.loads(log.read_text()) if log.exists() else []
entries.append(request)
log.write_text(json.dumps(entries))
index = len(entries) - 1
response = plan[\"responses\"][min(index, len(plan[\"responses\"]) - 1)]
print(json.dumps(response))
"""


class ReadOnlyRouteTests(unittest.TestCase):
    def run_route(self, manifest: dict, responses: list[dict], *, policy: Path = POLICY) -> tuple[subprocess.CompletedProcess[str], dict, list[dict]]:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            manifest_path = directory_path / "manifest.json"
            plan_path = directory_path / "plan.json"
            provider_path = directory_path / "provider.py"
            log_path = directory_path / "requests.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            provider_path.write_text(PROVIDER_FIXTURE, encoding="utf-8")
            plan_path.write_text(json.dumps({"log": str(log_path), "responses": responses}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CONTROLLER), "--manifest", str(manifest_path), "--policy", str(policy), "--provider-command", sys.executable, str(provider_path), str(plan_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            requests = json.loads(log_path.read_text()) if log_path.exists() else []
        return result, json.loads(result.stdout), requests

    def test_each_read_only_role_uses_its_first_semantic_model_and_timeout(self):
        expected = {
            "cheap_worker": ("openai-codex", "gpt-5.6-luna", 300),
            "coding_expert": ("openai-codex", "gpt-5.6-sol", 600),
            "researcher": ("openai-codex", "gpt-5.6-terra", 900),
        }
        for role, (provider, model, timeout_seconds) in expected.items():
            with self.subTest(role=role):
                result, report, requests = self.run_route(read_only_manifest(role), [{"kind": "success", "output": {"summary": "done"}}])
                self.assertEqual(result.returncode, 0)
                self.assertEqual(report["state"], "candidate_ready")
                self.assertEqual(report["selected_model"], {"provider": provider, "model": model, "reasoning_effort": "high" if role != "cheap_worker" else "low"})
                self.assertEqual(report["timeout_seconds"], timeout_seconds)
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]["model"], report["selected_model"])
                self.assertIn("route=success", result.stderr)

    def test_success_result_is_a_versioned_controller_artifact(self):
        _, report, _ = self.run_route(read_only_manifest("cheap_worker"), [{"kind": "success", "output": {"summary": "done"}}])
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "result.json"
            artifact.write_text(json.dumps(report), encoding="utf-8")
            result = subprocess.run([sys.executable, str(RESULT_VALIDATOR), "--kind", "result", "--input", str(artifact)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_transport_failure_advances_once_and_records_metadata_only_evidence(self):
        result, report, requests = self.run_route(
            read_only_manifest("cheap_worker"),
            [{"kind": "transport_failure", "category": "timeout"}, {"kind": "success", "output": {"summary": "recovered"}}],
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(requests), 2)
        self.assertEqual(report["selected_model"]["provider"], "ollama-cloud")
        self.assertEqual(report["evidence"], [{"attempt": 1, "category": "timeout", "provider": "openai-codex", "model": "gpt-5.6-luna"}])
        self.assertNotIn("output", json.dumps(report["evidence"]))

    def test_non_transport_failure_does_not_switch_models(self):
        result, report, requests = self.run_route(read_only_manifest("researcher"), [{"kind": "failure", "category": "tool_failure"}])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["state"], "validation_failure")
        self.assertEqual(report["code"], "non_switchable_failure")
        self.assertEqual(len(requests), 1)

    def test_invalid_output_receives_one_same_model_repair_then_returns_control(self):
        result, report, requests = self.run_route(
            read_only_manifest("coding_expert"),
            [{"kind": "success", "output": {}}, {"kind": "success", "output": {}}],
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["code"], "output_validation_failed")
        self.assertEqual(report["repair_count"], 1)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["model"], requests[1]["model"])
        self.assertTrue(requests[1]["repair"])

    def test_missing_reasoning_effort_is_not_sent(self):
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.yaml"
            source = POLICY.read_text(encoding="utf-8").replace(
                "  coding_expert:\n    models:\n      - provider: openai-codex\n        model: gpt-5.6-sol\n        reasoning_effort: high\n",
                "  coding_expert:\n    models:\n      - provider: openai-codex\n        model: gpt-5.6-sol\n",
            )
            policy.write_text(source, encoding="utf-8")
            result, report, requests = self.run_route(read_only_manifest("coding_expert"), [{"kind": "success", "output": {"summary": "done"}}], policy=policy)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("reasoning_effort", report["selected_model"])
        self.assertNotIn("reasoning_effort", requests[0]["model"])


if __name__ == "__main__":
    unittest.main()
