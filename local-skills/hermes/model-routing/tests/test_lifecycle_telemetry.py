"""Acceptance tests for lifecycle cleanup and metadata-only telemetry."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import telemetry_store

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "scripts" / "manage-lifecycle.py"
RESULT_VALIDATOR = ROOT / "scripts" / "validate-controller-manifest.py"


def run_lifecycle(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'scripts'}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return subprocess.run(["python3", str(LIFECYCLE), *args], cwd=cwd, capture_output=True, text=True, env=env, check=False)


def make_result(task_id: str, *, ok: bool, state: str, code: str, evidence: list[str], branch: str | None = None, repository: Path | None = None) -> dict:
    report = {
        "version": 1,
        "task_id": task_id,
        "ok": ok,
        "state": state,
        "code": code,
        "summary": "test result",
        "selected_model": {"provider": "openai-codex", "model": "gpt-5.6-terra", "reasoning_effort": "high"},
        "timeout_seconds": 60,
        "duration_ms": 1234,
        "repair_count": 0,
        "evidence": [],
        "evidence_locations": evidence,
        "validation": [{"command": "true", "returncode": 0}],
    }
    if branch is not None:
        report["candidate_branch"] = branch
    if repository is not None:
        report["repository_path"] = str(repository)
    return report


def make_repo(directory: Path) -> tuple[Path, str]:
    repository = directory / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "tests@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "Controller tests"], check=True)
    (repository / "seed.txt").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "test: seed"], check=True)
    base = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    return repository, base


class TelemetryStoreTests(unittest.TestCase):
    def test_allows_valid_metadata_record_and_prunes_by_age(self):
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "telemetry.jsonl"
            record = {
                "run_id": "run-1",
                "task_id": "task-1",
                "role": "coder",
                "provider": "openai-codex",
                "model": "gpt-5.6-terra",
                "duration_ms": 1000,
                "repair_count": 0,
                "outcome": "success",
                "validation_passed": True,
                "scope_violation": False,
            }
            telemetry_store.record(record, log)
            _, kept, removed = telemetry_store.prune(log, max_age_days=30, now=datetime.now(timezone.utc) + timedelta(days=31))
            self.assertEqual(kept, 0)
            self.assertEqual(removed, 1)

    def test_rejects_records_with_content_or_secret_keys(self):
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "telemetry.jsonl"
            for key in ("prompt", "output", "stdout", "secret", "api_key", "credential"):
                with self.assertRaises(ValueError):
                    telemetry_store.record({"run_id": "x", "task_id": "x", "outcome": "success", key: "leak"}, log)

    def test_rejects_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "telemetry.jsonl"
            with self.assertRaises(ValueError):
                telemetry_store.record({"run_id": "x", "task_id": "x", "outcome": "user_screamed"}, log)

    def test_size_pruning_removes_oldest_first(self):
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "telemetry.jsonl"
            for index in range(5):
                telemetry_store.record(
                    {"run_id": f"run-{index}", "task_id": "x", "outcome": "success", "duration_ms": index},
                    log,
                )
            _, kept, removed = telemetry_store.prune(log, max_size_bytes=1)
            self.assertEqual(kept, 0)
            self.assertEqual(removed, 5)


class LifecycleCleanupTests(unittest.TestCase):
    def test_cleanup_removes_successful_controller_worktree_and_branch(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = make_repo(directory)
            worktree_parent = directory / "model-routing-task-abc123"
            worktree = worktree_parent / "worktree"
            subprocess.run(["git", "-C", str(repository), "worktree", "add", "-b", "model-routing/task-abc123", str(worktree), base_commit], check=True)
            (worktree / "owned.txt").write_text("green", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "owned.txt"], check=True)
            subprocess.run(["git", "-C", str(worktree), "commit", "-qm", "candidate"], check=True)
            result_path = directory / "result.json"
            result_path.write_text(json.dumps(make_result("task-abc123", ok=True, state="candidate_ready", code="candidate_ready", evidence=[str(worktree_parent)], branch="model-routing/task-abc123")), encoding="utf-8")
            completed = run_lifecycle("--cleanup", "--result", str(result_path), "--repository", str(repository))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(worktree_parent.exists())
            self.assertEqual(
                subprocess.run(["git", "-C", str(repository), "rev-parse", "--verify", "refs/heads/model-routing/task-abc123^{commit}"], capture_output=True, text=True, check=False).stdout.strip(),
                "",
            )
            updated = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["evidence_locations"], [])

    def test_cleanup_retains_failed_evidence_within_24h(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = make_repo(directory)
            worktree_parent = directory / "model-routing-task-abc123"
            worktree = worktree_parent / "worktree"
            subprocess.run(["git", "-C", str(repository), "worktree", "add", "-b", "model-routing/task-abc123", str(worktree), base_commit], check=True)
            result_path = directory / "result.json"
            result_path.write_text(json.dumps(make_result("task-abc123", ok=False, state="validation_failure", code="worker_failed", evidence=[str(worktree_parent)], branch="model-routing/task-abc123")), encoding="utf-8")
            completed = run_lifecycle("--cleanup", "--result", str(result_path), "--repository", str(repository))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(worktree_parent.exists())
            updated = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["evidence_locations"], [str(worktree_parent)])

    def test_cleanup_does_not_remove_active_branch_or_user_worktree(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = make_repo(directory)
            user_worktree = directory / "user-feature"
            subprocess.run(["git", "-C", str(repository), "worktree", "add", "-b", "user-feature", str(user_worktree), base_commit], check=True)
            result_path = directory / "result.json"
            result_path.write_text(json.dumps(make_result("task", ok=True, state="candidate_ready", code="candidate_ready", evidence=[str(user_worktree)])), encoding="utf-8")
            completed = run_lifecycle("--cleanup", "--result", str(result_path), "--repository", str(repository))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(user_worktree.exists())
            updated = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["evidence_locations"], [str(user_worktree)])

    def test_cleanup_idempotent(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = make_repo(directory)
            worktree_parent = directory / "model-routing-task-abc123"
            worktree = worktree_parent / "worktree"
            subprocess.run(["git", "-C", str(repository), "worktree", "add", "-b", "model-routing/task-abc123", str(worktree), base_commit], check=True)
            result_path = directory / "result.json"
            result_path.write_text(json.dumps(make_result("task-abc123", ok=True, state="candidate_ready", code="candidate_ready", evidence=[str(worktree_parent)], branch="model-routing/task-abc123")), encoding="utf-8")
            self.assertEqual(run_lifecycle("--cleanup", "--result", str(result_path), "--repository", str(repository)).returncode, 0)
            self.assertEqual(run_lifecycle("--cleanup", "--result", str(result_path), "--repository", str(repository)).returncode, 0)
            self.assertFalse(worktree_parent.exists())

    def test_result_remains_schema_valid_after_cleanup(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = make_repo(directory)
            worktree_parent = directory / "model-routing-task-abc123"
            worktree = worktree_parent / "worktree"
            subprocess.run(["git", "-C", str(repository), "worktree", "add", "-b", "model-routing/task-abc123", str(worktree), base_commit], check=True)
            (worktree / "owned.txt").write_text("green", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "owned.txt"], check=True)
            subprocess.run(["git", "-C", str(worktree), "commit", "-qm", "candidate"], check=True)
            result_path = directory / "result.json"
            result_path.write_text(json.dumps(make_result("task-abc123", ok=True, state="candidate_ready", code="candidate_ready", evidence=[str(worktree_parent)], branch="model-routing/task-abc123")), encoding="utf-8")
            self.assertEqual(run_lifecycle("--cleanup", "--result", str(result_path), "--repository", str(repository)).returncode, 0)
            check = subprocess.run([str(Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"), str(RESULT_VALIDATOR), "--kind", "result", "--input", str(result_path)], capture_output=True, text=True, check=False)
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_telemetry_record_cli_records_only_metadata(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            log = directory / "telemetry.jsonl"
            env = os.environ.copy()
            env["MODEL_ROUTING_TELEMETRY_LOG"] = str(log)
            env["PYTHONPATH"] = f"{ROOT / 'scripts'}{os.pathsep}{env.get('PYTHONPATH', '')}"
            result_path = directory / "result.json"
            result_path.write_text(json.dumps(make_result("task-x", ok=True, state="candidate_ready", code="candidate_ready", evidence=[])), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(LIFECYCLE), "--record-telemetry", "--result", str(result_path)],
                cwd=directory,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            lines = log.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            for forbidden in ("prompt", "output", "source", "secret", "command"):
                self.assertNotIn(forbidden, record)
            self.assertEqual(record["outcome"], "success")
            self.assertEqual(record["role"], "unknown")

    def test_prune_telemetry_cli(self):
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "telemetry.jsonl"
            for index in range(3):
                telemetry_store.record({"run_id": f"run-{index}", "task_id": "x", "outcome": "success", "duration_ms": index}, log)
            env = os.environ.copy()
            env["MODEL_ROUTING_TELEMETRY_LOG"] = str(log)
            env["PYTHONPATH"] = f"{ROOT / 'scripts'}{os.pathsep}{env.get('PYTHONPATH', '')}"
            completed = subprocess.run(["python3", str(LIFECYCLE), "--prune-telemetry"], cwd=Path(raw), capture_output=True, text=True, env=env, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(completed.stdout)
            self.assertGreaterEqual(summary["kept"], 0)


if __name__ == "__main__":
    unittest.main()
