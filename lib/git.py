#!/usr/bin/env python3
"""Git submodule update logic."""

import subprocess
from pathlib import Path

from lib.config import Config


def run(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    kwargs = {"cwd": cwd, "check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(args, **kwargs)


def declared_submodules(repo_root: Path) -> list[str]:
    result = run(
        "git",
        "config",
        "-f",
        str(repo_root / ".gitmodules"),
        "--get-regexp",
        r"^submodule\..*\.path$",
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    submodules = []
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) == 2:
            submodules.append(parts[1])
    return submodules


def has_local_changes(path: Path) -> bool:
    result = run("git", "-C", str(path), "status", "--short", capture=True, check=False)
    return bool(result.stdout.strip())


def remote_head_ref(path: Path) -> str | None:
    result = run(
        "git", "-C", str(path), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD",
        capture=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    for branch in ("main", "master"):
        if (
            run(
                "git",
                "-C",
                str(path),
                "rev-parse",
                "--verify",
                "--quiet",
                f"origin/{branch}",
                check=False,
            ).returncode
            == 0
        ):
            return f"refs/remotes/origin/{branch}"
    return None


def update_submodules(
    repo_root: Path,
    requested: list[str],
    commit: bool = False,
    push: bool = False,
) -> None:
    config = Config(repo_root)
    configured = set(config.configured_submodule_names())
    declared = set(declared_submodules(repo_root))

    if not requested:
        requested = sorted(configured)

    for path in requested:
        if path not in configured:
            raise SystemExit(
                f"submodule '{path}' is not configured as a submodule source in {config.sources_file}"
            )
        if path not in declared:
            raise SystemExit(f"submodule '{path}' is not declared in {repo_root / '.gitmodules'}")

    branch_result = run("git", "branch", "--show-current", capture=True, check=False)
    current_branch = branch_result.stdout.strip()
    if not current_branch:
        raise SystemExit("parent repo is not on a branch")

    print("[update-skills] Initializing submodules")
    run("git", "submodule", "update", "--init", "--recursive", "--", *requested, cwd=repo_root)

    updated_any = False
    for path in requested:
        submodule_path = repo_root / path

        if has_local_changes(submodule_path):
            print(f"[update-skills] Skipping {path} because it has local changes")
            continue

        run("git", "-C", str(submodule_path), "fetch", "--prune", "origin")

        head_ref = remote_head_ref(submodule_path)
        if not head_ref:
            print(f"[update-skills] Skipping {path} because origin HEAD is unavailable")
            continue

        target_commit = run(
            "git", "-C", str(submodule_path), "rev-parse", head_ref, capture=True
        ).stdout.strip()
        current_commit = run(
            "git", "-C", str(submodule_path), "rev-parse", "HEAD", capture=True
        ).stdout.strip()

        if current_commit == target_commit:
            print(f"[update-skills] {path} is already up to date")
            continue

        run("git", "-C", str(submodule_path), "checkout", "--detach", target_commit)
        run("git", "add", path, cwd=repo_root)
        updated_any = True
        short = run(
            "git", "-C", str(submodule_path), "rev-parse", "--short", "HEAD", capture=True
        ).stdout.strip()
        print(f"[update-skills] Updated {path} to {short}")

    if not updated_any:
        print("[update-skills] No submodule pointer changes detected")
        return

    print("[update-skills] Staged submodule updates:")
    run("git", "diff", "--cached", "--submodule=short", cwd=repo_root)

    if not commit:
        print("[update-skills] Done. Review and commit when ready.")
        return

    run("git", "commit", "-m", "chore: update shared skill submodules", cwd=repo_root)
    print(f"[update-skills] Committed on {current_branch}")

    if push:
        run("git", "push", "origin", current_branch, cwd=repo_root)
        print(f"[update-skills] Pushed {current_branch}")
