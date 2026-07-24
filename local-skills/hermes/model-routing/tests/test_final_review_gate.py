"""Acceptance tests for the final Sol review gate."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "final-review-gate.py"
PYTHON = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
POLICY = ROOT / "tests" / "data" / "policy.yaml"


def manifest(task_id: str, mode: str, repository: Path, base_commit: str, role: str = "coder") -> dict:
    return {
        "version": 1,
        "task_id": task_id,
        "role": role,
        "role_rationale": f"Rationale for {task_id}.",
        "mode": mode,
        "repository": {"path": str(repository), "base_commit": base_commit},
        "depends_on": [],
        "ownership": {"files": [f"{task_id}.txt"], "directory_prefixes": []},
        "validation_commands": ["true"],
        "timeout_seconds": 60,
        "output_contract": {"artifact_type": "findings" if mode == "read_only" else "candidate", "required_fields": ["summary"]},
        "acceptance_criteria": ["Criterion."],
    }


def integration_report(base_commit: str, integration_commit: str | None, ok: bool = True, state: str = "locally_integrated", code: str | None = None) -> dict:
    report: dict = {
        "version": 1,
        "task_id": "integration",
        "ok": ok,
        "state": state,
        "code": code or state,
        "summary": "Integration report.",
        "base_commit": base_commit,
        "candidate_task_ids": ["alpha"],
        "candidate_commits": [base_commit],
        "validation": [{"command": "true", "returncode": 0}],
    }
    if integration_commit is not None:
        report["integration_commit"] = integration_commit
    return report


class FinalReviewGateTests(unittest.TestCase):
    def git(self, repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=repository, capture_output=True, text=True, check=True)

    def make_repo(self, directory: Path) -> tuple[Path, str, str]:
        directory.mkdir(parents=True, exist_ok=True)
        repository = directory / "repository"
        repository.mkdir()
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.email", "tests@example.invalid")
        self.git(repository, "config", "user.name", "Controller tests")
        (repository / "seed.txt").write_text("seed", encoding="utf-8")
        self.git(repository, "add", "seed.txt")
        self.git(repository, "commit", "-qm", "test: seed disposable repository")
        base_commit = self.git(repository, "rev-parse", "HEAD").stdout.strip()
        (repository / "alpha.txt").write_text("alpha", encoding="utf-8")
        self.git(repository, "add", "alpha.txt")
        self.git(repository, "commit", "-qm", "test: integration commit")
        integration_commit = self.git(repository, "rev-parse", "HEAD").stdout.strip()
        return repository, base_commit, integration_commit

    def assert_result_valid(self, directory: Path, report: dict) -> None:
        artifact = directory / "review-result.json"
        artifact.write_text(json.dumps(report), encoding="utf-8")
        result_check = subprocess.run(
            [str(PYTHON), str(ROOT / "scripts" / "validate-controller-manifest.py"), "--kind", "result", "--input", str(artifact)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result_check.returncode, 0, result_check.stderr)

    def run_gate(self, directory: Path, tasks: list[dict], report: dict, reviewer_command: list[str] | None = None, policy: bool = False, unresolved: list[str] | None = None) -> tuple[subprocess.CompletedProcess[str], dict]:
        batch = directory / "batch.json"
        integration = directory / "integration.json"
        batch.write_text(json.dumps(tasks), encoding="utf-8")
        integration.write_text(json.dumps(report), encoding="utf-8")
        command = [str(PYTHON), str(CONTROLLER), "--batch", str(batch), "--integration-report", str(integration)]
        if reviewer_command:
            command.extend(["--reviewer-command", *reviewer_command])
        if policy:
            command.extend(["--policy", str(POLICY)])
        for issue in unresolved or []:
            command.extend(["--unresolved-issue", issue])
        env = os.environ.copy()
        env["MODEL_ROUTING_REVIEW_TIMEOUT_SECONDS"] = "2"
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
        return result, json.loads(result.stdout)

    def make_reviewer(self, directory: Path, body: str) -> Path:
        reviewer = directory / "reviewer.py"
        reviewer.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"{body}\n",
            encoding="utf-8",
        )
        reviewer.chmod(0o755)
        return reviewer

    def test_direct_parent_only_read_only_request_bypasses_review(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "read_only", repository, base_commit, role="cheap_worker")],
                integration_report(base_commit, integration_commit),
                reviewer_command=["false"],
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(report["ok"])
            self.assertEqual(report["state"], "locally_integrated")
            self.assert_result_valid(directory, report)

    def test_pass_reviewer_approves_integration(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            reviewer = self.make_reviewer(
                directory,
                "request = json.load(sys.stdin)\n"
                "assert 'diff' in request and request['diff']\n"
                "assert request['validation'] == [{'command': 'true', 'returncode': 0}]\n"
                "json.dump({'kind': 'success', 'verdict': 'PASS', 'findings': []}, sys.stdout)",
            )
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
                reviewer_command=[str(PYTHON), str(reviewer)],
                policy=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(report["ok"])
            self.assertEqual(report["state"], "locally_integrated")
            self.assert_result_valid(directory, report)

    def test_reject_reviewer_stops_automation(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            reviewer = self.make_reviewer(
                directory,
                "json.dump({'kind': 'success', 'verdict': 'REJECT', 'findings': [{'severity': 'blocking', 'summary': 'Bad.'}]}, sys.stdout)",
            )
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
                reviewer_command=[str(PYTHON), str(reviewer)],
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(report["ok"])
            self.assertEqual(report["state"], "review_rejected")
            self.assert_result_valid(directory, report)

    def test_pass_with_blocking_finding_treats_as_reject(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            reviewer = self.make_reviewer(
                directory,
                "json.dump({'kind': 'success', 'verdict': 'PASS', 'findings': [{'severity': 'blocking', 'summary': 'Oops.'}]}, sys.stdout)",
            )
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
                reviewer_command=[str(PYTHON), str(reviewer)],
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["state"], "review_rejected")
            self.assert_result_valid(directory, report)

    def test_malformed_verdict_returns_validation_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            reviewer = self.make_reviewer(
                directory,
                "json.dump({'kind': 'success', 'verdict': 'MAYBE'}, sys.stdout)",
            )
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
                reviewer_command=[str(PYTHON), str(reviewer)],
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "malformed_verdict")
            self.assert_result_valid(directory, report)

    def test_missing_reviewer_command_when_writer_used_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "reviewer_command_missing")
            self.assert_result_valid(directory, report)

    def test_unsuccessful_integration_report_rejected_before_review(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit, ok=False, state="validation_failure", code="integration_validation_failed"),
                reviewer_command=[str(PYTHON), "-c", "import json,sys;json.dump({'kind':'success','verdict':'PASS','findings':[]},sys.stdout)"],
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "integration_not_ready")
            self.assert_result_valid(directory, report)

    def test_reviewer_transport_failure_reported_not_bypassed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
                reviewer_command=["false"],
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "reviewer_transport_failure")
            self.assert_result_valid(directory, report)

    def test_reviewer_timeout_reports_transport_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            reviewer = self.make_reviewer(directory, "import time\ntime.sleep(10)")
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
                reviewer_command=[str(PYTHON), str(reviewer)],
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "reviewer_transport_failure")
            self.assert_result_valid(directory, report)

    def test_policy_verifies_fixed_sol_high_reviewer(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit, integration_commit = self.make_repo(directory)
            bad_policy = directory / "bad-policy.yaml"
            bad_policy.write_text(
                "version: 1\n"
                "roles:\n"
                "  final_reviewer:\n"
                "    contract:\n"
                "      mode: read_only\n"
                "    models:\n"
                "      - provider: openai-codex\n"
                "        model: gpt-5.6-terra\n"
                "        reasoning_effort: high\n",
                encoding="utf-8",
            )
            reviewer = self.make_reviewer(directory, "json.dump({'kind': 'success', 'verdict': 'PASS', 'findings': []}, sys.stdout)")
            result, report = self.run_gate(
                directory,
                [manifest("alpha", "write", repository, base_commit)],
                integration_report(base_commit, integration_commit),
                reviewer_command=[str(PYTHON), str(reviewer)],
                policy=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            command = [str(PYTHON), str(CONTROLLER), "--batch", str(directory / "batch.json"), "--integration-report", str(directory / "integration.json"), "--policy", str(bad_policy), "--reviewer-command", str(PYTHON), str(reviewer)]
            env = os.environ.copy()
            env["MODEL_ROUTING_REVIEW_TIMEOUT_SECONDS"] = "2"
            result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "invalid_reviewer_role")
            self.assert_result_valid(directory, report)


if __name__ == "__main__":
    unittest.main()
