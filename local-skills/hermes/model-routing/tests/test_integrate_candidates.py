"""Acceptance tests for deterministic staged local candidate integration."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "integrate-candidates.py"
PYTHON = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"


def manifest(task_id: str, repository: Path, base_commit: str, *, depends_on: list[str] | None = None, owned_file: str | None = None) -> dict:
    return {
        "version": 1,
        "task_id": task_id,
        "role": "coder",
        "role_rationale": "The coder owns this bounded repository mutation.",
        "mode": "write",
        "repository": {"path": str(repository), "base_commit": base_commit},
        "depends_on": depends_on or [],
        "ownership": {"files": [owned_file or f"{task_id}.txt"], "directory_prefixes": []},
        "validation_commands": ["true"],
        "timeout_seconds": 60,
        "output_contract": {"artifact_type": "candidate", "required_fields": ["summary", "changed_paths"]},
        "acceptance_criteria": ["The candidate is ready for staged integration."],
    }


class StagedIntegrationTests(unittest.TestCase):
    def git(self, repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=repository, capture_output=True, text=True, check=True)

    def make_repo(self, directory: Path) -> tuple[Path, str]:
        directory.mkdir(parents=True, exist_ok=True)
        repository = directory / "repository"
        repository.mkdir()
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.email", "tests@example.invalid")
        self.git(repository, "config", "user.name", "Controller tests")
        (repository / "seed.txt").write_text("seed", encoding="utf-8")
        self.git(repository, "add", "seed.txt")
        self.git(repository, "commit", "-qm", "test: seed disposable repository")
        return repository, self.git(repository, "rev-parse", "HEAD").stdout.strip()

    def add_upstream(self, directory: Path, repository: Path) -> Path:
        remote = directory / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        self.git(repository, "remote", "add", "origin", str(remote))
        self.git(repository, "push", "-qu", "origin", "HEAD")
        return remote

    def assert_result_valid(self, directory: Path, report: dict) -> None:
        artifact = directory / "integration-result.json"
        artifact.write_text(json.dumps(report), encoding="utf-8")
        result_check = subprocess.run(
            [str(PYTHON), str(ROOT / "scripts" / "validate-controller-manifest.py"), "--kind", "result", "--input", str(artifact)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result_check.returncode, 0, result_check.stderr)

    def candidate(self, directory: Path, repository: Path, base_commit: str, task_id: str, path: str, content: str) -> dict:
        worktree = directory / f"candidate-{task_id}"
        branch = f"candidate-{task_id}"
        self.git(repository, "worktree", "add", "-q", "-b", branch, str(worktree), base_commit)
        (worktree / path).write_text(content, encoding="utf-8")
        self.git(worktree, "add", path)
        self.git(worktree, "commit", "-qm", f"test: candidate {task_id}")
        return {
            "version": 1,
            "task_id": task_id,
            "ok": True,
            "state": "candidate_ready",
            "code": "candidate_ready",
            "summary": f"Candidate {task_id} is ready.",
            "base_commit": base_commit,
            "candidate_commit": self.git(worktree, "rev-parse", "HEAD").stdout.strip(),
            "candidate_branch": branch,
            "changed_paths": [path],
            "validation": [{"command": "true", "returncode": 0}],
        }

    def run_controller(self, directory: Path, tasks: list[dict], candidates: list[dict], *commands: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        batch = directory / "batch.json"
        artifacts = directory / "candidates.json"
        batch.write_text(json.dumps(tasks), encoding="utf-8")
        artifacts.write_text(json.dumps(candidates), encoding="utf-8")
        command = [str(PYTHON), str(CONTROLLER), "--batch", str(batch), "--candidates", str(artifacts)]
        for validation_command in commands:
            command.extend(["--validation-command", validation_command])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result, json.loads(result.stdout)

    def test_clean_candidates_integrate_in_dependency_order_without_pushing(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            remote = self.add_upstream(directory, repository)
            alpha = self.candidate(directory, repository, base_commit, "alpha", "alpha.txt", "alpha")
            bravo = self.candidate(directory, repository, base_commit, "bravo", "bravo.txt", "bravo")
            result, report = self.run_controller(
                directory,
                [manifest("bravo", repository, base_commit, depends_on=["alpha"]), manifest("alpha", repository, base_commit)],
                [bravo, alpha],
                "test \"$(cat alpha.txt)\" = alpha",
                "test \"$(cat bravo.txt)\" = bravo",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(report["ok"])
            self.assertEqual(report["state"], "locally_integrated")
            self.assertTrue(report["integrated_locally"])
            self.assertTrue(report["push_required"])
            self.assertEqual(report["candidate_task_ids"], ["alpha", "bravo"])
            self.assertEqual([item["command"] for item in report["validation"]], ["test \"$(cat alpha.txt)\" = alpha", "test \"$(cat bravo.txt)\" = bravo"])
            self.assertNotEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)
            self.assertEqual((repository / "alpha.txt").read_text(encoding="utf-8"), "alpha")
            self.assertEqual((repository / "bravo.txt").read_text(encoding="utf-8"), "bravo")
            self.assertEqual(self.git(repository, "status", "--porcelain").stdout, "")
            self.assertEqual(self.git(remote, "rev-parse", "HEAD").stdout.strip(), base_commit)
            self.assertEqual(self.git(repository, "rev-list", "--count", "@{u}..HEAD").stdout.strip(), "2")
            self.assert_result_valid(directory, report)

    def test_local_only_repository_integrates_without_upstream_fetch(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            alpha = self.candidate(directory, repository, base_commit, "alpha", "alpha.txt", "alpha")
            result, report = self.run_controller(directory, [manifest("alpha", repository, base_commit)], [alpha], "test -f alpha.txt")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["state"], "locally_integrated")
            self.assertEqual((repository / "alpha.txt").read_text(encoding="utf-8"), "alpha")
            self.assert_result_valid(directory, report)

    def test_conflict_or_combined_validation_failure_preserves_active_branch_and_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            alpha = self.candidate(directory, repository, base_commit, "alpha", "shared.txt", "alpha")
            bravo = self.candidate(directory, repository, base_commit, "bravo", "shared.txt", "bravo")
            result, report = self.run_controller(
                directory,
                [manifest("alpha", repository, base_commit, owned_file="shared.txt"), manifest("bravo", repository, base_commit, owned_file="shared.txt")],
                [alpha, bravo],
                "true",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "integration_conflict")
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)
            self.assertTrue(Path(report["evidence_locations"][0]).exists())
            self.assert_result_valid(directory, report)

            repository, base_commit = self.make_repo(directory / "validation")
            alpha = self.candidate(directory / "validation", repository, base_commit, "alpha", "alpha.txt", "alpha")
            result, report = self.run_controller(
                directory / "validation",
                [manifest("alpha", repository, base_commit)],
                [alpha],
                "false",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "integration_validation_failed")
            self.assertEqual(report["validation"], [{"command": "false", "returncode": 1}])
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)
            self.assertTrue(Path(report["evidence_locations"][0]).exists())
            self.assert_result_valid(directory / "validation", report)

    def test_active_head_or_upstream_change_after_validation_aborts_finalization(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            alpha = self.candidate(directory, repository, base_commit, "alpha", "alpha.txt", "alpha")
            result, report = self.run_controller(
                directory,
                [manifest("alpha", repository, base_commit)],
                [alpha],
                f"git -C {shlex.quote(str(repository))} commit --allow-empty -m 'test: external active movement'",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["state"], "base_changed")
            self.assertEqual(report["code"], "base_changed")
            self.assertFalse((repository / "alpha.txt").exists())
            self.assertTrue(Path(report["evidence_locations"][0]).exists())
            self.assert_result_valid(directory, report)

            remote = self.add_upstream(directory / "upstream", self.make_repo(directory / "upstream")[0])
            upstream_repository = directory / "upstream" / "repository"
            upstream_base = self.git(upstream_repository, "rev-parse", "HEAD").stdout.strip()
            alpha = self.candidate(directory / "upstream", upstream_repository, upstream_base, "alpha", "alpha.txt", "alpha")
            mover = directory / "move-upstream.py"
            mover.write_text(
                "import subprocess, sys\n"
                "from pathlib import Path\n"
                "remote, clone = sys.argv[1:]\n"
                "subprocess.run(['git', 'clone', '-q', remote, clone], check=True)\n"
                "subprocess.run(['git', '-C', clone, 'config', 'user.email', 'tests@example.invalid'], check=True)\n"
                "subprocess.run(['git', '-C', clone, 'config', 'user.name', 'Controller tests'], check=True)\n"
                "Path(clone, 'remote.txt').write_text('remote')\n"
                "subprocess.run(['git', '-C', clone, 'add', 'remote.txt'], check=True)\n"
                "subprocess.run(['git', '-C', clone, 'commit', '-qm', 'test: move upstream'], check=True)\n"
                "subprocess.run(['git', '-C', clone, 'push', '-q'], check=True)\n",
                encoding="utf-8",
            )
            result, report = self.run_controller(
                directory / "upstream",
                [manifest("alpha", upstream_repository, upstream_base)],
                [alpha],
                f"{shlex.quote(str(PYTHON))} {shlex.quote(str(mover))} {shlex.quote(str(remote))} {shlex.quote(str(directory / 'upstream-writer'))}",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "repository_diverged")
            self.assertEqual(self.git(upstream_repository, "rev-parse", "HEAD").stdout.strip(), upstream_base)
            self.assertFalse((upstream_repository / "alpha.txt").exists())
            self.assert_result_valid(directory / "upstream", report)

    def test_final_fetch_failure_preserves_integration_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            self.add_upstream(directory, repository)
            alpha = self.candidate(directory, repository, base_commit, "alpha", "alpha.txt", "alpha")
            result, report = self.run_controller(
                directory,
                [manifest("alpha", repository, base_commit)],
                [alpha],
                f"git -C {shlex.quote(str(repository))} remote set-url origin /does-not-exist",
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "repository_fetch_failed")
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)
            self.assertFalse((repository / "alpha.txt").exists())
            self.assertTrue(Path(report["evidence_locations"][0]).exists())
            self.assert_result_valid(directory, report)

    def test_candidate_scope_escape_is_rejected_before_integration_worktree_creation(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            escaped = self.candidate(directory, repository, base_commit, "alpha", "outside.txt", "escaped")
            result, report = self.run_controller(directory, [manifest("alpha", repository, base_commit, owned_file="alpha.txt")], [escaped], "true")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "candidate_scope_violation")
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)
            self.assertFalse((repository / "outside.txt").exists())

    def test_local_only_repository_requires_declared_combined_validation(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            candidate = self.candidate(directory, repository, base_commit, "alpha", "alpha.txt", "alpha")
            result, report = self.run_controller(directory, [manifest("alpha", repository, base_commit)], [candidate])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "integration_validation_missing")
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)
    def test_rejects_missing_or_cyclic_dependencies_before_creating_integration_worktree(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            repository, base_commit = self.make_repo(directory)
            alpha = self.candidate(directory, repository, base_commit, "alpha", "alpha.txt", "alpha")
            missing = manifest("alpha", repository, base_commit, depends_on=["missing"])
            result, report = self.run_controller(directory, [missing], [alpha], "true")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "missing_dependency")
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)

            cyclic = manifest("alpha", repository, base_commit, depends_on=["bravo"])
            bravo = manifest("bravo", repository, base_commit, depends_on=["alpha"])
            bravo_candidate = self.candidate(directory, repository, base_commit, "bravo", "bravo.txt", "bravo")
            result, report = self.run_controller(directory, [cyclic, bravo], [alpha, bravo_candidate], "true")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["code"], "dependency_cycle")
            self.assertEqual(self.git(repository, "rev-parse", "HEAD").stdout.strip(), base_commit)


if __name__ == "__main__":
    unittest.main()
