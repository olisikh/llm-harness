"""Skill-level functional evaluation for Task 10.

Validates that the canonical Hermes-only model-routing skill, the profile
policy, the controller contracts, and the native-delegation guard describe one
enforceable workflow.

Coverage:
- role choice maps every role to the correct contract/mode;
- native read-only delegation guard allows read-only tools and blocks mutation;
- writer isolation is enforced by the controller manifest contract;
- model-failure classification matches the policy transport-failure list;
- final-review triggering depends on the presence of a writer task.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCHEMAS = ROOT / "schemas"
POLICY = Path.home() / ".hermes" / "model-routing.yaml"
GUARD = Path.home() / ".hermes" / "plugins" / "model-routing-guard" / "guard.py"
PYTHON = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
TASK_SCHEMA = SCHEMAS / "controller-task.v1.schema.json"
RESULT_SCHEMA = SCHEMAS / "controller-result.v1.schema.json"


class SkillPolicyAlignmentTests(unittest.TestCase):
    def _run_validator(self, kind: str, document: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = directory / "input.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            command = [
                str(PYTHON),
                str(SCRIPTS / "validate-controller-manifest.py"),
                "--kind",
                kind,
                "--input",
                str(path),
            ]
            return subprocess.run(command, capture_output=True, text=True, check=False)

    def _manifest(self, *, task_id: str, role: str, mode: str) -> dict:
        return {
            "version": 1,
            "task_id": task_id,
            "role": role,
            "role_rationale": "Skill evaluation manifest.",
            "mode": mode,
            "repository": {"path": str(Path.home() / ".hermes"), "base_commit": "59ad700294046c69ad3e9cc48c16bc1097fb0177"},
            "depends_on": [],
            "ownership": {"files": ["README.md"], "directory_prefixes": []},
            "validation_commands": ["true"],
            "timeout_seconds": 60,
            "output_contract": {"artifact_type": "findings", "required_fields": ["summary"]},
            "acceptance_criteria": ["Pass validation."],
        }

    def test_role_contracts_match_policy(self):
        policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
        expected_policy_modes = {
            "cheap_worker": "read_only",
            "coder": "writer",
            "coding_expert": "read_only",
            "researcher": "read_only",
            "final_reviewer": "read_only",
        }
        expected_manifest_modes = {
            "cheap_worker": "read_only",
            "coder": "write",
            "coding_expert": "read_only",
            "researcher": "read_only",
            "final_reviewer": "read_only",
        }
        for role in expected_policy_modes:
            with self.subTest(role=role):
                self.assertIn(role, policy["roles"], f"role {role} missing from policy")
                self.assertEqual(policy["roles"][role]["contract"]["mode"], expected_policy_modes[role])
                result = self._run_validator("task", self._manifest(task_id=role.replace("_", "-"), role=role, mode=expected_manifest_modes[role]))
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_writer_requires_validation_commands(self):
        manifest = self._manifest(task_id="writer-test", role="coder", mode="write")
        manifest["validation_commands"] = []
        result = self._run_validator("task", manifest)
        self.assertEqual(result.returncode, 2)
        self.assertIn("writer_validation_missing", result.stdout)

    def test_read_only_role_rejects_write_mode(self):
        result = self._run_validator("task", self._manifest(task_id="cheap-test", role="cheap_worker", mode="write"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid_role_mode", result.stdout)

    def test_guard_allows_read_only_tools(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            request_path = directory / "request.json"
            request_path.write_text(
                json.dumps(
                    {
                        "contract": {"role": "cheap_worker", "mode": "read_only"},
                        "tools": ["read_file", "search_files", "web_search", "web_extract", "vision_analyze"],
                        "native_spec": {"provider": "openai-codex", "model": "gpt-5.6-luna", "reasoning_effort": "low"},
                        "policy": str(POLICY),
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(PYTHON), str(GUARD), "--request", str(request_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertTrue(report["allowed"])
            self.assertEqual(report["code"], "allowed")

    def test_guard_blocks_native_writer_and_terminal(self):
        cases = [
            {"contract": {"role": "coder", "mode": "write"}, "tools": ["read_file"], "code": "mode_not_read_only"},
            {"contract": {"role": "cheap_worker", "mode": "read_only"}, "tools": ["terminal"], "code": "blocked_tool:terminal"},
            {"contract": {"role": "cheap_worker", "mode": "read_only"}, "tools": ["execute_code"], "code": "blocked_tool:execute_code"},
            {"contract": {"role": "cheap_worker", "mode": "read_only"}, "tools": ["write_file"], "code": "blocked_tool:write_file"},
            {"contract": {"role": "cheap_worker", "mode": "read_only"}, "tools": ["mcp__vikunja__vikunja_tasks"], "code": "blocked_namespace:mcp__vikunja__vikunja_tasks"},
            {"contract": {"role": "cheap_worker", "mode": "read_only"}, "tools": ["mcp__voicebox__voicebox_speak"], "code": "blocked_namespace:mcp__voicebox__voicebox_speak"},
        ]
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            for case in cases:
                with self.subTest(code=case["code"]):
                    request_path = directory / "request.json"
                    request_path.write_text(json.dumps(case), encoding="utf-8")
                    result = subprocess.run(
                        [str(PYTHON), str(GUARD), "--request", str(request_path)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    report = json.loads(result.stdout)
                    self.assertFalse(report["allowed"])
                    self.assertEqual(report["code"], case["code"])

    def test_transport_failures_classified_in_policy(self):
        policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
        required = {"rate_limit", "timeout", "provider_error", "unavailable_model", "authentication_error", "connection_error"}
        configured = set(policy["switching"]["transport_failures"])
        self.assertTrue(required.issubset(configured), f"missing transport failures: {required - configured}")

    def test_final_review_triggered_by_writer(self):
        validator = self._load_validator()
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            read_only_batch = [
                self._manifest(task_id="ro-one", role="cheap_worker", mode="read_only"),
                self._manifest(task_id="ro-two", role="researcher", mode="read_only"),
            ]
            writer_batch = read_only_batch + [
                self._manifest(task_id="wr-one", role="coder", mode="write"),
            ]
            read_only_path = directory / "ro.json"
            writer_path = directory / "wr.json"
            read_only_path.write_text(json.dumps(read_only_batch), encoding="utf-8")
            writer_path.write_text(json.dumps(writer_batch), encoding="utf-8")

            integration = {
                "version": 1,
                "task_id": "integration",
                "ok": True,
                "state": "locally_integrated",
                "code": "locally_integrated",
                "summary": "Integration passed.",
                "evidence": [],
                "evidence_locations": [],
                "base_commit": "59ad700294046c69ad3e9cc48c16bc1097fb0177",
                "candidate_task_ids": [],
                "candidate_commits": [],
                "integration_branch": "model-routing/integration-test",
                "integration_commit": "59ad700294046c69ad3e9cc48c16bc1097fb0177",
                "integrated_locally": True,
                "changed_paths": [],
                "validation": [],
                "push_required": True,
            }
            integration_path = directory / "integration.json"
            integration_path.write_text(json.dumps(integration), encoding="utf-8")

            def gate(batch_path: Path) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        str(PYTHON),
                        str(SCRIPTS / "final-review-gate.py"),
                        "--batch",
                        str(batch_path),
                        "--integration-report",
                        str(integration_path),
                        "--policy",
                        str(POLICY),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

            ro_result = gate(read_only_path)
            self.assertEqual(ro_result.returncode, 0, ro_result.stderr)
            report = json.loads(ro_result.stdout)
            self.assertEqual(report["state"], "locally_integrated")
            self.assertIn("bypassed", report["summary"].lower())

            wr_result = gate(writer_path)
            self.assertEqual(wr_result.returncode, 2, wr_result.stderr)
            report = json.loads(wr_result.stdout)
            self.assertEqual(report["code"], "reviewer_command_missing")

    def _load_validator(self):
        spec = importlib.util.spec_from_file_location("controller_contract", SCRIPTS / "validate-controller-manifest.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_schemas_parse_and_validate(self):
        task_schema = json.loads(TASK_SCHEMA.read_text(encoding="utf-8"))
        result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(task_schema["$id"], "https://olisikh.github.io/llm-harness/schemas/controller-task.v1.schema.json")
        self.assertEqual(result_schema["$id"], "https://olisikh.github.io/llm-harness/schemas/controller-result.v1.schema.json")

    def test_skill_metadata_frontmatter(self):
        skill_md = ROOT / "SKILL.md"
        source = skill_md.read_text(encoding="utf-8")
        if not source.startswith("---"):
            self.fail("SKILL.md must start with YAML frontmatter")
        _, frontmatter, _ = source.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        self.assertEqual(metadata["name"], "model-routing")
        self.assertIn("Hermes", metadata["description"])
        self.assertIn("deterministic", metadata["description"].lower())


if __name__ == "__main__":
    unittest.main()
