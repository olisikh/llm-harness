#!/usr/bin/env python3
"""Integrate validated writer candidates in an isolated worktree without pushing."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-controller-manifest.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("controller_contract", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("The controller contract validator is unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repository), *args], capture_output=True, text=True, check=False)


def git_output(repository: Path, *args: str) -> str | None:
    result = git(repository, *args)
    return result.stdout.strip() if result.returncode == 0 else None


def failure(code: str, summary: str, *, state: str = "validation_failure", evidence_locations: list[str] | None = None, validation: list[dict[str, Any]] | None = None, base_commit: str | None = None, candidate_task_ids: list[str] | None = None, candidate_commits: list[str] | None = None, integration_branch: str | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "version": 1,
        "task_id": "integration",
        "ok": False,
        "state": state,
        "code": code,
        "summary": summary,
        "evidence": [],
        "evidence_locations": evidence_locations or [],
        "changed_paths": [],
        "validation": validation or [],
        "push_required": False,
    }
    if base_commit is not None:
        report["base_commit"] = base_commit
    if candidate_task_ids is not None:
        report["candidate_task_ids"] = candidate_task_ids
    if candidate_commits is not None:
        report["candidate_commits"] = candidate_commits
    if integration_branch is not None:
        report["integration_branch"] = integration_branch
    return report


def operation_in_progress(repository: Path) -> bool:
    git_dir = git_output(repository, "rev-parse", "--git-dir")
    if git_dir is None:
        return False
    path = (repository / git_dir).resolve()
    return any((path / marker).exists() for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-apply", "rebase-merge"))


def preflight(repository: Path, base_commit: str, *, fetch_upstream: bool) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not repository.is_dir() or git_output(repository, "rev-parse", "--is-inside-work-tree") != "true":
        return failure("repository_not_git", "The integration repository is not a Git worktree."), None, None
    top_level = git_output(repository, "rev-parse", "--show-toplevel")
    if top_level is None or Path(top_level).resolve() != repository.resolve():
        return failure("repository_not_git", "The integration repository must name the Git worktree root."), None, None
    if operation_in_progress(repository):
        return failure("git_operation_in_progress", "The integration repository has a Git operation in progress."), None, None
    if git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout:
        return failure("repository_dirty", "The integration repository has modified, staged, or untracked state."), None, None
    resolved_base = git_output(repository, "rev-parse", "--verify", f"{base_commit}^{{commit}}")
    if resolved_base is None or git_output(repository, "rev-parse", "HEAD") != resolved_base:
        return failure("base_changed", "The active repository HEAD does not match the manifest base commit.", state="base_changed"), None, None
    active_branch = git_output(repository, "symbolic-ref", "--quiet", "--short", "HEAD")
    if active_branch is None:
        return failure("active_branch_unavailable", "Local integration requires an active branch rather than a detached HEAD."), None, None
    upstream = git_output(repository, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if fetch_upstream and upstream is not None:
        if git(repository, "fetch", "--prune").returncode != 0:
            return failure("repository_fetch_failed", "The repository upstream could not be fetched."), None, None
        divergence = git_output(repository, "rev-list", "--left-right", "--count", "@{u}...HEAD")
        if divergence is None or divergence != "0\t0":
            return failure("repository_diverged", "The integration repository is ahead of or behind its upstream."), None, None
    return None, resolved_base, active_branch


def load_documents(batch_path: Path, candidates_path: Path, validator: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks = json.loads(batch_path.read_text(encoding="utf-8"), object_pairs_hook=validator.unique_object)
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"), object_pairs_hook=validator.unique_object)
    if not isinstance(tasks, list) or not tasks:
        raise validator.ContractFailure("schema_violation", "An integration batch must be a non-empty JSON array.")
    if not isinstance(candidates, list):
        raise validator.ContractFailure("schema_violation", "Candidate artifacts must be a JSON array.")
    task_schema = json.loads((ROOT / "schemas" / "controller-task.v1.schema.json").read_text(encoding="utf-8"))
    result_schema = json.loads((ROOT / "schemas" / "controller-result.v1.schema.json").read_text(encoding="utf-8"))
    task_ids: set[str] = set()
    for task in tasks:
        validator.validate_document(task, "task", task_schema)
        if task["task_id"] in task_ids:
            raise validator.ContractFailure("duplicate_task_id", "Integration task IDs must be unique.")
        task_ids.add(task["task_id"])
    candidate_ids: set[str] = set()
    for candidate in candidates:
        validator.validate_document(candidate, "result", result_schema)
        if candidate["task_id"] in candidate_ids:
            raise validator.ContractFailure("duplicate_candidate_task", "Candidate artifacts must identify unique tasks.")
        candidate_ids.add(candidate["task_id"])
    return tasks, candidates


def order_tasks(tasks: list[dict[str, Any]]) -> list[str]:
    by_id = {task["task_id"]: task for task in tasks}
    for task in tasks:
        if any(dependency not in by_id for dependency in task["depends_on"]):
            raise ValueError("missing_dependency")
    ordered: list[str] = []
    complete: set[str] = set()
    while len(complete) < len(by_id):
        ready = sorted(task_id for task_id, task in by_id.items() if task_id not in complete and all(dependency in complete for dependency in task["depends_on"]))
        if not ready:
            raise ValueError("dependency_cycle")
        ordered.extend(ready)
        complete.update(ready)
    return ordered


def owned(path: str, ownership: dict[str, list[str]]) -> bool:
    return path in ownership["files"] or any(path == prefix or path.startswith(f"{prefix}/") for prefix in ownership["directory_prefixes"])


def validate_candidates(tasks: list[dict[str, Any]], candidates: list[dict[str, Any]], repository: Path, base_commit: str) -> tuple[list[str], list[str]]:
    task_by_id = {task["task_id"]: task for task in tasks}
    expected_ids = {task_id for task_id, task in task_by_id.items() if task["mode"] == "write"}
    candidate_by_id = {candidate["task_id"]: candidate for candidate in candidates}
    if set(candidate_by_id) != expected_ids:
        raise ValueError("candidate_set_invalid")
    for task in tasks:
        if Path(task["repository"]["path"]).resolve() != repository or task["repository"]["base_commit"] != base_commit:
            raise ValueError("integration_repository_mismatch")
    ordered_ids = [task_id for task_id in order_tasks(tasks) if task_id in expected_ids]
    commits: list[str] = []
    for task_id in ordered_ids:
        task = task_by_id[task_id]
        candidate = candidate_by_id[task_id]
        if candidate.get("ok") is not True or candidate.get("state") != "candidate_ready" or candidate.get("code") != "candidate_ready":
            raise ValueError("candidate_not_ready")
        if candidate.get("base_commit") != base_commit or not isinstance(candidate.get("candidate_commit"), str):
            raise ValueError("candidate_base_mismatch")
        commit = candidate["candidate_commit"]
        if git_output(repository, "rev-parse", "--verify", f"{commit}^{{commit}}") is None:
            raise ValueError("candidate_commit_missing")
        if git(repository, "merge-base", "--is-ancestor", base_commit, commit).returncode != 0:
            raise ValueError("candidate_base_mismatch")
        changed_paths = [path for path in git(repository, "diff", "--name-only", f"{base_commit}..{commit}").stdout.splitlines() if path]
        if not changed_paths or any(not owned(path, task["ownership"]) for path in changed_paths):
            raise ValueError("candidate_scope_violation")
        commits.append(commit)
    return ordered_ids, commits


def run_validation(worktree: Path, commands: list[str]) -> tuple[bool, list[dict[str, Any]]]:
    reports: list[dict[str, Any]] = []
    for command in commands:
        result = subprocess.run(command, cwd=worktree, shell=True, capture_output=True, text=True, check=False)
        reports.append({"command": command, "returncode": result.returncode})
    return all(report["returncode"] == 0 for report in reports), reports


def integrate(tasks: list[dict[str, Any]], candidates: list[dict[str, Any]], validation_commands: list[str]) -> dict[str, Any]:
    if not validation_commands:
        return failure("integration_validation_missing", "Staged integration requires at least one declared combined validation command.")
    first = tasks[0]
    repository = Path(first["repository"]["path"]).resolve()
    requested_base = first["repository"]["base_commit"]
    preflight_error, base_commit, active_branch = preflight(repository, requested_base, fetch_upstream=True)
    if preflight_error is not None:
        return preflight_error
    assert base_commit is not None and active_branch is not None
    try:
        task_ids, commits = validate_candidates(tasks, candidates, repository, base_commit)
    except ValueError as error:
        return failure(str(error), str(error).replace("_", " ").capitalize() + ".", base_commit=base_commit)
    evidence_root = Path(tempfile.mkdtemp(prefix="model-routing-integration-"))
    worktree = evidence_root / "worktree"
    branch = f"model-routing/integration-{uuid.uuid4().hex[:12]}"
    if git(repository, "worktree", "add", "-b", branch, str(worktree), base_commit).returncode != 0:
        return failure("worktree_failure", "The integration worktree could not be created.", evidence_locations=[str(evidence_root)], base_commit=base_commit, candidate_task_ids=task_ids, candidate_commits=commits)
    for commit in commits:
        if git(worktree, "cherry-pick", "--no-edit", commit).returncode != 0:
            return failure("integration_conflict", "A candidate commit conflicts during staged integration.", evidence_locations=[str(evidence_root)], base_commit=base_commit, candidate_task_ids=task_ids, candidate_commits=commits, integration_branch=branch)
    checks_passed, validation = run_validation(worktree, validation_commands)
    if not checks_passed:
        return failure("integration_validation_failed", "Combined integration validation failed.", evidence_locations=[str(evidence_root)], validation=validation, base_commit=base_commit, candidate_task_ids=task_ids, candidate_commits=commits, integration_branch=branch)
    final_error, final_base, final_branch = preflight(repository, base_commit, fetch_upstream=True)
    if final_error is not None:
        if final_error["state"] == "base_changed":
            final_error.update({"evidence_locations": [str(evidence_root)], "validation": validation, "base_commit": base_commit, "candidate_task_ids": task_ids, "candidate_commits": commits, "integration_branch": branch})
            return final_error
        return failure(final_error["code"], final_error["summary"], evidence_locations=[str(evidence_root)], validation=validation, base_commit=base_commit, candidate_task_ids=task_ids, candidate_commits=commits, integration_branch=branch)
    if final_base != base_commit or final_branch != active_branch:
        return failure("base_changed", "The active branch changed before local finalization.", state="base_changed", evidence_locations=[str(evidence_root)], validation=validation, base_commit=base_commit, candidate_task_ids=task_ids, candidate_commits=commits, integration_branch=branch)
    finalized = git(repository, "merge", "--ff-only", branch)
    integrated_commit = git_output(worktree, "rev-parse", "HEAD")
    if finalized.returncode != 0 or integrated_commit is None or git_output(repository, "rev-parse", "HEAD") != integrated_commit:
        return failure("base_changed", "The active branch changed before the safe local fast-forward.", state="base_changed", evidence_locations=[str(evidence_root)], validation=validation, base_commit=base_commit, candidate_task_ids=task_ids, candidate_commits=commits, integration_branch=branch)
    return {
        "version": 1,
        "task_id": "integration",
        "ok": True,
        "state": "locally_integrated",
        "code": "locally_integrated",
        "summary": "Candidate commits passed combined validation and were integrated locally.",
        "evidence": [],
        "evidence_locations": [str(evidence_root)],
        "base_commit": base_commit,
        "candidate_task_ids": task_ids,
        "candidate_commits": commits,
        "integration_branch": branch,
        "integration_commit": git_output(repository, "rev-parse", "HEAD"),
        "integrated_locally": True,
        "changed_paths": [],
        "validation": validation,
        "push_required": True,
    }


def emit(report: dict[str, Any]) -> int:
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    status = "success" if report["ok"] else "failure"
    print(f"integration={status} code={report['code']} summary={report['summary']}", file=sys.stderr)
    return 0 if report["ok"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, type=Path, help="JSON array of validated task manifests")
    parser.add_argument("--candidates", required=True, type=Path, help="JSON array of validated candidate result artifacts")
    parser.add_argument("--validation-command", action="append", default=[], help="Combined validation command run in the integration worktree")
    args = parser.parse_args()
    validator = load_validator()
    try:
        tasks, candidates = load_documents(args.batch, args.candidates, validator)
        return emit(integrate(tasks, candidates, args.validation_command))
    except validator.DuplicateJsonKey as error:
        return emit(failure("duplicate_json_key", f"Duplicate JSON key: {error}."))
    except validator.ContractFailure as error:
        return emit(failure(error.code, error.summary))
    except (OSError, json.JSONDecodeError) as error:
        return emit(failure("input_unavailable", str(error)))


if __name__ == "__main__":
    raise SystemExit(main())
