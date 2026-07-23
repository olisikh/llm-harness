"""Public CLI acceptance tests for isolated writer candidate execution."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "execute-writer-candidate.py"
RESULT_VALIDATOR = ROOT / "scripts" / "validate-controller-manifest.py"
POLICY = Path.home() / ".hermes" / "model-routing.yaml"

WRITER_FIXTURE = """#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text())
request = json.loads(sys.stdin.read())
log = Path(plan[\"log\"])
entries = json.loads(log.read_text()) if log.exists() else []
entries.append(request)
log.write_text(json.dumps(entries))
step = plan[\"steps\"][min(len(entries) - 1, len(plan[\"steps\"]) - 1)]
if step.get(\"write\"):
    target = Path(step[\"write\"][\"path\"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(step[\"write\"][\"content\"])
if step.get(\"git_action\"):
    action = subprocess.run([\"git\", step[\"git_action\"]], capture_output=True, text=True)
    Path(plan[\"git_log\"]).write_text(json.dumps({\"returncode\": action.returncode, \"stderr\": action.stderr}))
print(json.dumps(step.get(\"response\") or {\"kind\": \"success\", \"output\": {\"summary\": \"writer completed\", \"changed_paths\": []}}))
"""


def writer_manifest(repository: Path, base_commit: str, validation: list[str] | None = None) -> dict:
    return {
        "version": 1,
        "task_id": "routing-004-writer",
        "role": "coder",
        "role_rationale": "The coder owns this bounded repository mutation.",
        "mode": "write",
        "repository": {"path": str(repository), "base_commit": base_commit},
        "depends_on": [],
        "ownership": {"files": ["owned.txt"], "directory_prefixes": ["docs"]},
        "validation_commands": validation or ["test \"$(cat owned.txt)\" = green"],
        "timeout_seconds": 60,
        "output_contract": {"artifact_type": "candidate", "required_fields": ["summary", "changed_paths"]},
        "acceptance_criteria": ["The controller creates a validated candidate commit."],
    }


class WriterCandidateTests(unittest.TestCase):
    def make_repo(self, directory: Path) -> tuple[Path, str]:
        repo = directory / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.email", "tests@example.invalid")
        self.git(repo, "config", "user.name", "Controller tests")
        (repo / "owned.txt").write_text("red")
        (repo / "outside.txt").write_text("initial")
        (repo / "docs").mkdir()
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-qm", "test: seed disposable repository")
        return repo, self.git(repo, "rev-parse", "HEAD").stdout.strip()

    def git(self, repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=repository, capture_output=True, text=True, check=True)

    def run_candidate(self, directory: Path, manifest: dict, steps: list[dict]) -> tuple[subprocess.CompletedProcess[str], dict, list[dict], Path]:
        manifest_path = directory / "manifest.json"
        plan_path = directory / "plan.json"
        writer_path = directory / "writer.py"
        request_log = directory / "requests.json"
        git_log = directory / "git-action.json"
        manifest_path.write_text(json.dumps(manifest))
        writer_path.write_text(WRITER_FIXTURE)
        plan_path.write_text(json.dumps({"steps": steps, "log": str(request_log), "git_log": str(git_log)}))
        result = subprocess.run(
            [sys.executable, str(CONTROLLER), "--manifest", str(manifest_path), "--policy", str(POLICY), "--writer-command", sys.executable, str(writer_path), str(plan_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        requests = json.loads(request_log.read_text()) if request_log.exists() else []
        return result, json.loads(result.stdout), requests, git_log

    def test_clean_writer_creates_candidate_without_touching_active_checkout(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, base = self.make_repo(directory)
            result, report, requests, _ = self.run_candidate(directory, writer_manifest(repo, base), [{"write": {"path": "owned.txt", "content": "green"}}])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["state"], "candidate_ready")
            self.assertEqual(report["base_commit"], base)
            self.assertRegex(report["candidate_commit"], r"^[0-9a-f]{40}$")
            self.assertEqual(report["changed_paths"], ["owned.txt"])
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0]["model"], {"provider": "openai-codex", "model": "gpt-5.6-terra", "reasoning_effort": "high"})
            self.assertEqual(requests[0]["timeout_seconds"], 1200)
            artifact = directory / "result.json"
            artifact.write_text(json.dumps(report))
            artifact_check = subprocess.run([sys.executable, str(RESULT_VALIDATOR), "--kind", "result", "--input", str(artifact)], capture_output=True, text=True, check=False)
            self.assertEqual(artifact_check.returncode, 0, artifact_check.stderr)
            self.assertEqual(self.git(repo, "rev-parse", "HEAD").stdout.strip(), base)
            self.assertEqual((repo / "owned.txt").read_text(), "red")
            self.assertEqual(self.git(repo, "status", "--porcelain").stdout, "")

    def test_dirty_and_non_git_repositories_fail_before_worker_launch(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, base = self.make_repo(directory)
            (repo / "owned.txt").write_text("dirty")
            result, report, requests, _ = self.run_candidate(directory, writer_manifest(repo, base), [{"write": {"path": "owned.txt", "content": "green"}}])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "repository_dirty")
            self.assertEqual(requests, [])
            non_git = directory / "not-a-repository"
            non_git.mkdir()
            result, report, requests, _ = self.run_candidate(directory, writer_manifest(non_git, base), [{"write": {"path": "owned.txt", "content": "green"}}])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "repository_not_git")
            self.assertEqual(requests, [])

    def test_staged_untracked_and_operation_state_fail_before_worker_launch(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            scenarios = {
                "staged": lambda repo: (repo / "owned.txt").write_text("staged"),
                "untracked": lambda repo: (repo / "new.txt").write_text("untracked"),
                "merge": lambda repo: (repo / ".git" / "MERGE_HEAD").touch(),
                "rebase": lambda repo: (repo / ".git" / "rebase-merge").mkdir(),
            }
            for name, prepare in scenarios.items():
                with self.subTest(state=name):
                    child = directory / name
                    child.mkdir()
                    repo, base = self.make_repo(child)
                    prepare(repo)
                    if name == "staged":
                        self.git(repo, "add", "owned.txt")
                    result, report, requests, _ = self.run_candidate(child, writer_manifest(repo, base), [{"write": {"path": "owned.txt", "content": "green"}}])
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(report["code"], "git_operation_in_progress" if name in {"merge", "rebase"} else "repository_dirty")
                    self.assertEqual(requests, [])

    def test_upstream_divergence_fails_before_worker_launch(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, _ = self.make_repo(directory)
            remote = directory / "remote.git"
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            self.git(repo, "remote", "add", "origin", str(remote))
            self.git(repo, "push", "-qu", "origin", "HEAD")
            (repo / "owned.txt").write_text("ahead")
            self.git(repo, "add", "owned.txt")
            self.git(repo, "commit", "-qm", "test: create upstream divergence")
            base = self.git(repo, "rev-parse", "HEAD").stdout.strip()
            result, report, requests, _ = self.run_candidate(directory, writer_manifest(repo, base), [{"write": {"path": "owned.txt", "content": "green"}}])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "repository_diverged")
            self.assertEqual(requests, [])

    def test_scope_escape_and_symlink_escape_are_rejected_in_the_isolated_worktree(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, base = self.make_repo(directory)
            result, report, _, _ = self.run_candidate(directory, writer_manifest(repo, base), [{"write": {"path": "outside.txt", "content": "escaped"}}])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["state"], "scope_violation")
            self.assertEqual(report["changed_paths"], ["outside.txt"])
            self.assertEqual((repo / "outside.txt").read_text(), "initial")
            self.git(repo, "checkout", "--", ".")
            (repo / "docs" / "escape").symlink_to("../outside.txt")
            self.git(repo, "add", "docs/escape")
            self.git(repo, "commit", "-qm", "test: add scoped symlink")
            base = self.git(repo, "rev-parse", "HEAD").stdout.strip()
            result, report, _, _ = self.run_candidate(directory, writer_manifest(repo, base), [{"write": {"path": "docs/escape", "content": "escaped"}}])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["state"], "scope_violation")
            self.assertEqual((repo / "outside.txt").read_text(), "initial")

    def test_preexisting_owned_symlink_is_rejected_before_an_ignored_target_can_change(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, _ = self.make_repo(directory)
            (repo / ".gitignore").write_text("ignored-target\n")
            (repo / "docs" / "ignored-link").symlink_to("../ignored-target")
            self.git(repo, "add", ".gitignore", "docs/ignored-link")
            self.git(repo, "commit", "-qm", "test: add owned symlink")
            base = self.git(repo, "rev-parse", "HEAD").stdout.strip()
            result, report, requests, _ = self.run_candidate(directory, writer_manifest(repo, base), [{"write": {"path": "docs/ignored-link", "content": "escaped"}}])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["state"], "scope_violation")
            self.assertEqual(requests, [])
            self.assertFalse((repo / "ignored-target").exists())

    def test_failed_validation_gets_one_same_model_repair_then_full_validation(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, base = self.make_repo(directory)
            result, report, requests, _ = self.run_candidate(
                directory,
                writer_manifest(repo, base, ["test \"$(cat owned.txt)\" = green", "test -f owned.txt"]),
                [{"write": {"path": "owned.txt", "content": "red"}}, {"write": {"path": "owned.txt", "content": "green"}}],
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["repair_count"], 1)
            self.assertEqual(len(requests), 2)
            self.assertFalse(requests[0]["repair"])
            self.assertTrue(requests[1]["repair"])
            self.assertEqual(requests[0]["model"], requests[1]["model"])
            self.assertEqual(report["validation"], [
                {"command": "test \"$(cat owned.txt)\" = green", "returncode": 1},
                {"command": "test -f owned.txt", "returncode": 0},
                {"command": "test \"$(cat owned.txt)\" = green", "returncode": 0},
                {"command": "test -f owned.txt", "returncode": 0},
            ])

    def test_transport_failure_advances_to_the_next_writer_model_only(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, base = self.make_repo(directory)
            result, report, requests, _ = self.run_candidate(
                directory,
                writer_manifest(repo, base),
                [{"response": {"kind": "transport_failure", "category": "timeout"}}, {"write": {"path": "owned.txt", "content": "green"}}],
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["selected_model"], {"provider": "ollama-cloud", "model": "kimi-k2.7-code"})
            self.assertEqual([request["model"]["model"] for request in requests], ["gpt-5.6-terra", "kimi-k2.7-code"])
            self.assertFalse(requests[1]["repair"])

    def test_worker_git_stage_and_commit_are_blocked_before_controller_commits(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repo, base = self.make_repo(directory)
            for action in ("add", "commit"):
                with self.subTest(action=action):
                    result, report, _, git_log = self.run_candidate(directory, writer_manifest(repo, base), [{"write": {"path": "owned.txt", "content": "green"}, "git_action": action}])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(report["state"], "candidate_ready")
                    attempt = json.loads(git_log.read_text())
                    self.assertNotEqual(attempt["returncode"], 0)
                    self.assertIn("blocked", attempt["stderr"])
                    self.assertEqual(self.git(repo, "rev-parse", "HEAD").stdout.strip(), base)


if __name__ == "__main__":
    unittest.main()
