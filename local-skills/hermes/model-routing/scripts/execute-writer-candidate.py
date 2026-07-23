#!/usr/bin/env python3
"""Create one validated writer candidate in a dedicated Git worktree."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-controller-manifest.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("controller_contract", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("The controller contract validator is unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def model_metadata(entry: dict[str, Any]) -> dict[str, str]:
    metadata = {"provider": entry["provider"], "model": entry["model"]}
    if "reasoning_effort" in entry:
        metadata["reasoning_effort"] = entry["reasoning_effort"]
    return metadata


def git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repository), *args], capture_output=True, text=True, check=False)


def git_output(repository: Path, *args: str) -> str | None:
    completed = git(repository, *args)
    return completed.stdout.strip() if completed.returncode == 0 else None


def failure(
    code: str,
    summary: str,
    *,
    state: str = "validation_failure",
    selected_model: dict[str, str] | None = None,
    timeout_seconds: int = 0,
    repair_count: int = 0,
    evidence_locations: list[str] | None = None,
    changed_paths: list[str] | None = None,
    validation: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "task_id": "controller-error",
        "ok": False,
        "state": state,
        "code": code,
        "summary": summary,
        "selected_model": selected_model or {},
        "timeout_seconds": timeout_seconds,
        "repair_count": repair_count,
        "evidence": [],
        "evidence_locations": evidence_locations or [],
        "changed_paths": changed_paths or [],
        "validation": validation or [],
    }


def load_manifest(manifest_path: Path, validator: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    document = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=validator.unique_object)
    schema = json.loads((ROOT / "schemas" / "controller-task.v1.schema.json").read_text(encoding="utf-8"))
    report = validator.validate_document(document, "task", schema)
    if document["mode"] != "write":
        raise validator.ContractFailure("invalid_role_mode", "Writer candidates require a write manifest mode.", "mode")
    return document, report


def operation_in_progress(repository: Path) -> bool:
    git_dir = git_output(repository, "rev-parse", "--git-dir")
    if git_dir is None:
        return False
    path = (repository / git_dir).resolve()
    return any((path / marker).exists() for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-apply", "rebase-merge"))


def preflight(repository: Path, base_commit: str) -> tuple[dict[str, Any] | None, str | None]:
    if not repository.is_dir() or git_output(repository, "rev-parse", "--is-inside-work-tree") != "true":
        return failure("repository_not_git", "The manifest repository is not a Git worktree."), None
    top_level = git_output(repository, "rev-parse", "--show-toplevel")
    if top_level is None or Path(top_level).resolve() != repository.resolve():
        return failure("repository_not_git", "The manifest repository must name the Git worktree root."), None
    if operation_in_progress(repository):
        return failure("git_operation_in_progress", "The repository has a merge, rebase, cherry-pick, or revert in progress."), None
    if git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout:
        return failure("repository_dirty", "The repository has modified, staged, or untracked state."), None
    resolved_base = git_output(repository, "rev-parse", "--verify", f"{base_commit}^{{commit}}")
    head = git_output(repository, "rev-parse", "HEAD")
    if resolved_base is None or head != resolved_base:
        return failure("base_changed", "The repository HEAD does not match the manifest base commit.", state="base_changed"), None
    upstream = git_output(repository, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream is not None:
        if git(repository, "fetch", "--prune").returncode != 0:
            return failure("repository_fetch_failed", "The repository upstream could not be fetched."), None
        divergence = git_output(repository, "rev-list", "--left-right", "--count", "@{u}...HEAD")
        if divergence is None or divergence != "0\t0":
            return failure("repository_diverged", "The repository is ahead of or behind its upstream."), None
    return None, resolved_base


def create_git_shim(directory: Path) -> Path:
    actual_git = shutil.which("git")
    if actual_git is None:
        raise RuntimeError("git is unavailable")
    directory.mkdir(parents=True, exist_ok=True)
    shim = directory / "git"
    shim.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  add|commit|reset|restore|merge|rebase|cherry-pick|revert|am|apply|stash|switch|checkout|branch|tag|update-index)\n"
        "    echo 'model-routing: worker git mutation blocked' >&2; exit 77;;\n"
        "esac\n"
        f"exec {actual_git} \"$@\"\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return directory


def invoke_writer(command: list[str], request: dict[str, Any], worktree: Path, timeout_seconds: int, git_shim: Path) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PATH"] = f"{git_shim}{os.pathsep}{environment.get('PATH', '')}"
    try:
        completed = subprocess.run(
            command,
            cwd=worktree,
            env=environment,
            input=json.dumps(request, separators=(",", ":")),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"kind": "failure", "category": "worker_timeout"}
    except OSError:
        return {"kind": "failure", "category": "worker_failed"}
    if completed.returncode != 0:
        return {"kind": "failure", "category": "worker_failed"}
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"kind": "failure", "category": "worker_failed"}
    return response if isinstance(response, dict) else {"kind": "failure", "category": "worker_failed"}


def changed_paths(worktree: Path) -> list[str]:
    tracked = git(worktree, "diff", "--name-only", "-z", "HEAD").stdout.split("\0")
    untracked = git(worktree, "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0")
    return sorted({path for path in [*tracked, *untracked] if path})


def owned(path: str, ownership: dict[str, list[str]]) -> bool:
    return path in ownership["files"] or any(path.startswith(f"{prefix}/") or path == prefix for prefix in ownership["directory_prefixes"])


def symlink_safe(worktree: Path, relative_path: str) -> bool:
    root = worktree.resolve()
    candidate = worktree / relative_path
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return False
    current = worktree
    for part in Path(relative_path).parts:
        current = current / part
        if current.is_symlink():
            return False
    return True


def ownership_symlinks_safe(worktree: Path, ownership: dict[str, list[str]]) -> bool:
    candidates = [worktree / path for path in ownership["files"]]
    for prefix in ownership["directory_prefixes"]:
        directory = worktree / prefix
        if directory.exists() and not directory.is_symlink():
            candidates.extend(directory.rglob("*"))
        else:
            candidates.append(directory)
    return all(not candidate.is_symlink() or symlink_safe(worktree, str(candidate.relative_to(worktree))) for candidate in candidates)


def scope_check(worktree: Path, ownership: dict[str, list[str]]) -> tuple[bool, list[str]]:
    paths = changed_paths(worktree)
    return ownership_symlinks_safe(worktree, ownership) and all(owned(path, ownership) and symlink_safe(worktree, path) for path in paths), paths


def worker_touched_git(worktree: Path, base_commit: str) -> bool:
    return git_output(worktree, "rev-parse", "HEAD") != base_commit or git(worktree, "diff", "--cached", "--quiet").returncode != 0


def run_validation(worktree: Path, commands: list[str]) -> tuple[bool, list[dict[str, Any]]]:
    reports: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(command, cwd=worktree, shell=True, capture_output=True, text=True, check=False)
        reports.append({"command": command, "returncode": completed.returncode})
    return all(report["returncode"] == 0 for report in reports), reports


def execute(manifest: dict[str, Any], policy: dict[str, Any], command: list[str]) -> dict[str, Any]:
    role_policy = policy["roles"].get(manifest["role"])
    if role_policy is None or role_policy["contract"]["mode"] != "writer":
        return failure("invalid_role_mode", "The selected role is not configured for isolated writer execution.")
    model_entries = role_policy["models"]
    model_index = 0
    selected = model_metadata(model_entries[model_index])
    timeout_seconds = role_policy["timeout_seconds"]
    preflight_error, base_commit = preflight(Path(manifest["repository"]["path"]), manifest["repository"]["base_commit"])
    if preflight_error is not None:
        return preflight_error
    assert base_commit is not None
    repository = Path(manifest["repository"]["path"]).resolve()
    evidence_root = Path(tempfile.mkdtemp(prefix=f"model-routing-{manifest['task_id']}-"))
    worktree = evidence_root / "worktree"
    branch = f"model-routing/{manifest['task_id']}-{uuid.uuid4().hex[:12]}"
    added = git(repository, "worktree", "add", "-b", branch, str(worktree), base_commit)
    if added.returncode != 0:
        return failure("worktree_failure", "The dedicated Git worktree could not be created.", evidence_locations=[str(evidence_root)])
    shim = create_git_shim(evidence_root / "bin")
    initial_scope, initial_paths = scope_check(worktree, manifest["ownership"])
    if not initial_scope:
        return failure("scope_violation", "Declared ownership contains a symlink boundary.", state="scope_violation", selected_model=selected, timeout_seconds=timeout_seconds, evidence_locations=[str(evidence_root)], changed_paths=initial_paths)
    repair_count = 0
    validations: list[dict[str, Any]] = []
    started = time.monotonic()
    while True:
        selected = model_metadata(model_entries[model_index])
        request = {
            "task_id": manifest["task_id"],
            "role": manifest["role"],
            "model": selected,
            "timeout_seconds": timeout_seconds,
            "repair": repair_count == 1,
            "execution_spec": {
                "acceptance_criteria": manifest["acceptance_criteria"],
                "ownership": manifest["ownership"],
                "repository": {"path": str(worktree), "base_commit": base_commit},
                "validation_commands": manifest["validation_commands"],
            },
        }
        response = invoke_writer(command, request, worktree, timeout_seconds, shim)
        if response.get("kind") == "transport_failure":
            category = response.get("category")
            if category in set(policy["switching"]["transport_failures"]) and model_index + 1 < len(model_entries):
                model_index += 1
                repair_count = 0
                continue
            return failure("provider_exhausted", "All configured provider fallbacks failed.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence_locations=[str(evidence_root)], validation=validations)
        if response.get("kind") != "success":
            return failure(response.get("category", "worker_failed"), "The writer did not return a successful response.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence_locations=[str(evidence_root)], validation=validations)
        if worker_touched_git(worktree, base_commit):
            return failure("worker_git_mutation", "The writer attempted to stage or commit changes.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence_locations=[str(evidence_root)], validation=validations)
        in_scope, paths = scope_check(worktree, manifest["ownership"])
        if not in_scope:
            return failure("scope_violation", "Writer changes escaped exact ownership or a symlink boundary.", state="scope_violation", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence_locations=[str(evidence_root)], changed_paths=paths, validation=validations)
        valid_output = isinstance(response.get("output"), dict) and all(field in response["output"] for field in manifest["output_contract"]["required_fields"])
        checks_passed, validation_attempt = run_validation(worktree, manifest["validation_commands"])
        validations.extend(validation_attempt)
        if valid_output and checks_passed:
            break
        if repair_count == 1:
            return failure("validation_failed", "The same-model repair did not satisfy the declared output contract and validation commands.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence_locations=[str(evidence_root)], changed_paths=paths, validation=validations)
        repair_count = 1
    git(worktree, "add", "--all")
    committed = git(worktree, "commit", "-m", f"feat(controller): complete {manifest['task_id']}")
    if committed.returncode != 0:
        return failure("controller_commit_failed", "The controller could not create the validated Conventional Commit.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence_locations=[str(evidence_root)], changed_paths=paths, validation=validations)
    return {
        "version": 1,
        "task_id": manifest["task_id"],
        "ok": True,
        "state": "candidate_ready",
        "code": "candidate_ready",
        "summary": "Writer candidate committed in an isolated worktree.",
        "selected_model": selected,
        "timeout_seconds": timeout_seconds,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "repair_count": repair_count,
        "evidence": [],
        "evidence_locations": [str(evidence_root)],
        "base_commit": base_commit,
        "candidate_commit": git_output(worktree, "rev-parse", "HEAD"),
        "candidate_branch": branch,
        "changed_paths": paths,
        "validation": validations,
    }


def emit(report: dict[str, Any]) -> int:
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    status = "success" if report["ok"] else "failure"
    print(f"writer_candidate={status} code={report['code']} summary={report['summary']}", file=sys.stderr)
    return 0 if report["ok"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--writer-command", nargs="+", required=True, help="Writer command receiving one JSON request on stdin in the dedicated worktree.")
    args = parser.parse_args()
    try:
        validator = load_validator()
        manifest, _ = load_manifest(args.manifest, validator)
        policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
        return emit(execute(manifest, policy, args.writer_command))
    except ModuleNotFoundError as error:
        return emit(failure("input_unavailable", f"Required controller dependency is unavailable: {error.name}."))
    except validator.DuplicateJsonKey as error:
        return emit(failure("duplicate_json_key", f"Duplicate JSON key: {error}."))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as error:
        return emit(failure("input_unavailable", str(error)))
    except validator.ContractFailure as error:
        return emit(failure(error.code, error.summary))


if __name__ == "__main__":
    raise SystemExit(main())
