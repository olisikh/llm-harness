#!/usr/bin/env python3
"""Manage controller artifact lifecycle and metadata-only telemetry.

Operations:
  --record-telemetry       Record one telemetry entry from a result artifact.
  --cleanup                Remove successful controller worktrees/branches after
                           integration, while retaining failed evidence for 24h.
  --prune-telemetry        Age/size prune the telemetry log.

Safety:
- Only removes directories and Git refs that match the controller prefix
  "model-routing-" and are not currently the active checkout branch or a
  registered unrecognized worktree.
- Does not delete user-created, active, or non-controller worktrees/branches.
- Updates result artifact evidence_locations to reference only retained evidence.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

# Ensure telemetry_store is importable when this script is invoked directly.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import telemetry_store  # noqa: E402

CONTROLLER_PREFIXES = ("model-routing-", "model-routing/")
FAILURE_RETENTION_SECONDS = 24 * 3600


def git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repository), *args], capture_output=True, text=True, check=False)


def git_output(repository: Path, *args: str) -> str | None:
    completed = git(repository, *args)
    return completed.stdout.strip() if completed.returncode == 0 else None


def is_controller_path(path: Path) -> bool:
    return any(part.startswith(CONTROLLER_PREFIXES) for part in path.parts)


def is_active_worktree(repository: Path, worktree_path: Path) -> bool:
    """Return True if worktree_path is the repository's active checkout."""
    top_level = git_output(repository, "rev-parse", "--show-toplevel")
    if top_level is None:
        return False
    return Path(top_level).resolve() == worktree_path.resolve()


def is_registered_worktree(repository: Path, worktree_path: Path) -> bool:
    listed = git(repository, "worktree", "list", "--porcelain").stdout
    for line in listed.splitlines():
        if line.startswith("worktree ") and Path(line.split(" ", 1)[1]).resolve() == worktree_path.resolve():
            return True
    return False


def remove_worktree(repository: Path, worktree_path: Path, *, force: bool = False) -> tuple[bool, str]:
    """Remove a controller-owned worktree directory and deregister it."""
    if not worktree_path.exists():
        return True, "already absent"
    if not is_controller_path(worktree_path):
        return False, "refuse to remove non-controller path"
    if is_active_worktree(repository, worktree_path) and not force:
        return False, "active checkout, not removed"
    if is_registered_worktree(repository, worktree_path):
        git(repository, "worktree", "remove", "--force", str(worktree_path))
        git(repository, "worktree", "prune", "--expire=now")
    if worktree_path.exists():
        shutil.rmtree(worktree_path, ignore_errors=True)
    if worktree_path.exists():
        return False, "partial removal"
    # Ensure stale worktree registration is gone before caller tries to delete the branch.
    git(repository, "worktree", "prune", "--expire=now")
    return True, "removed"


def remove_branch(repository: Path, branch: str, *, active_branch: str | None = None) -> tuple[bool, str]:
    """Remove a controller-owned branch if it is not active."""
    if not branch.startswith(CONTROLLER_PREFIXES):
        return False, "refuse to remove non-controller branch"
    if active_branch is not None and branch == active_branch:
        return False, "active branch, not removed"
    if git_output(repository, "rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}") is None:
        return True, "already absent"
    completed = git(repository, "branch", "-D", branch)
    return completed.returncode == 0, "removed" if completed.returncode == 0 else completed.stderr


def load_result_artifact(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_result_artifact(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def should_retain_evidence(report: dict[str, Any], now: float) -> bool:
    """Failed evidence is retained for 24h."""
    if report.get("ok") is True:
        return False
    # Best-effort timestamp from file mtime if available; otherwise assume now.
    return True


def telemetry_from_result(report: dict[str, Any], *, parent_task_id: str | None = None) -> dict[str, Any]:
    """Extract content-free metadata from a controller result artifact."""
    selected = report.get("selected_model") or {}
    outcome = telemetry_store.normalize_outcome(report.get("state"))
    validation_passed = None
    validation = report.get("validation")
    if isinstance(validation, list):
        validation_passed = all(isinstance(item, dict) and item.get("returncode") == 0 for item in validation)
    changed_paths = report.get("changed_paths") or []
    scope_violation = report.get("state") == "scope_violation" or report.get("code") == "scope_violation"
    return {
        "run_id": report.get("task_id", "unknown"),
        "parent_task_id": parent_task_id,
        "task_id": report.get("task_id", "unknown"),
        "role": report.get("role", "unknown"),
        "provider": selected.get("provider"),
        "model": selected.get("model"),
        "reasoning_effort": selected.get("reasoning_effort"),
        "duration_ms": report.get("duration_ms"),
        "repair_count": report.get("repair_count"),
        "outcome": outcome,
        "validation_passed": validation_passed,
        "scope_violation": scope_violation,
    }


def cleanup(report: dict[str, Any], repository: Path, *, now: float | None = None) -> dict[str, Any]:
    """Clean up a result artifact's evidence_locations. Returns cleanup report."""
    now = now or time.time()
    active_branch = git_output(repository, "symbolic-ref", "--quiet", "--short", "HEAD")
    retained: list[str] = []
    removed: list[str] = []
    skipped: list[str] = []

    for location in report.get("evidence_locations", []):
        path = Path(location).resolve()
        if not path.exists():
            continue
        if not is_controller_path(path):
            retained.append(location)
            continue
        if should_retain_evidence(report, now):
            # Keep failed evidence for 24h.
            try:
                age_seconds = now - path.stat().st_mtime
            except OSError:
                age_seconds = 0
            if age_seconds < FAILURE_RETENTION_SECONDS:
                retained.append(location)
                continue
        ok, reason = remove_worktree(repository, path)
        if ok:
            removed.append(location)
        else:
            skipped.append(f"{location}: {reason}")

    # Also remove associated candidate/integration branches.
    for key in ("candidate_branch", "integration_branch"):
        branch = report.get(key)
        if isinstance(branch, str):
            ok, reason = remove_branch(repository, branch, active_branch=active_branch)
            if ok:
                removed.append(f"refs/heads/{branch}")
            else:
                skipped.append(f"refs/heads/{branch}: {reason}")

    # Update evidence_locations to retained paths only.
    report["evidence_locations"] = retained
    return {"retained": retained, "removed": removed, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, help="Path to controller result artifact JSON")
    parser.add_argument("--repository", type=Path, help="Repository that owns worktrees/branches")
    parser.add_argument("--record-telemetry", action="store_true", help="Record metadata from --result")
    parser.add_argument("--cleanup", action="store_true", help="Clean up controller worktrees/branches for --result")
    parser.add_argument("--prune-telemetry", action="store_true", help="Prune aged/oversized telemetry")
    parser.add_argument("--parent-task-id", help="Optional parent task grouping for telemetry")
    args = parser.parse_args()

    if args.record_telemetry:
        if args.result is None:
            print("telemetry=error missing --result", file=sys.stderr)
            return 2
        report = load_result_artifact(args.result)
        record = telemetry_from_result(report, parent_task_id=args.parent_task_id)
        telemetry_store.record(record)
        print("telemetry=recorded", file=sys.stderr)
        print(json.dumps({"telemetry": "recorded", "record": record}, sort_keys=True, separators=(",", ":")))
        return 0

    if args.cleanup:
        if args.result is None or args.repository is None:
            print("cleanup=error missing --result and --repository", file=sys.stderr)
            return 2
        report = load_result_artifact(args.result)
        summary = cleanup(report, args.repository)
        save_result_artifact(args.result, report)
        print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
        print(f"cleanup=ok removed={len(summary['removed'])} retained={len(summary['retained'])} skipped={len(summary['skipped'])}", file=sys.stderr)
        return 0

    if args.prune_telemetry:
        _, kept, removed = telemetry_store.prune()
        print(json.dumps({"kept": kept, "removed": removed}, sort_keys=True, separators=(",", ":")))
        print(f"telemetry_pruned kept={kept} removed={removed}", file=sys.stderr)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
