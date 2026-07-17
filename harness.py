#!/usr/bin/env python3
"""Unified entrypoint for llm-harness operations."""

import argparse
import subprocess
import sys
from pathlib import Path

from lib.audit import audit_skill_installations, print_audit_summary
from lib.config import Config
from lib.git import update_submodules
from lib.readiness import audit_skill_readiness, print_readiness_summary
from lib.routing import (
    approve_skill,
    discover_unapproved_skills,
    print_candidates,
    seed_routing_index,
)
from lib.sync import sync_harness, uninstall_harness


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def run(*args: str, cwd: Path | None = None, check: bool = True, capture: bool = False):
    kwargs = {"cwd": cwd, "check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(args, **kwargs)


def cmd_install(args: argparse.Namespace) -> int:
    cfg = Config(repo_root())
    names = cfg.list_harness_names()
    if not names:
        print(
            "no harnesses discovered from harness/, harness-paths.yaml, or config.yaml",
            file=sys.stderr,
        )
        return 1

    for name in names:
        sync_harness(cfg, name)

    print("[install] Done.")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    cfg = Config(repo_root())
    names = cfg.list_harness_names()
    if not names:
        print(
            "no harnesses discovered from harness/, harness-paths.yaml, or config.yaml",
            file=sys.stderr,
        )
        return 1

    for name in names:
        uninstall_harness(cfg, name)

    print("[uninstall] Done.")
    return 0


def cmd_update_skills(args: argparse.Namespace) -> int:
    if args.push and not args.commit:
        print("--push only makes sense together with --commit", file=sys.stderr)
        return 1

    update_submodules(
        repo_root(),
        requested=args.submodule,
        commit=args.commit,
        push=args.push,
    )

    print("== refresh harness links ==")
    cfg = Config(repo_root())
    for name in cfg.list_harness_names():
        sync_harness(cfg, name)
    return 0


def cmd_audit_skills(args: argparse.Namespace) -> int:
    result = audit_skill_installations(Config(repo_root()))
    print_audit_summary(result)
    return 1 if result.invalid_keys else 0


def cmd_audit_readiness(args: argparse.Namespace) -> int:
    root = repo_root()
    project = Path(args.project).expanduser().resolve() if args.project else None
    result = audit_skill_readiness(
        root / "state" / "skill-readiness.yaml",
        skill_paths_path=Path("~/.agents/config/skill-paths.json").expanduser(),
        project=project,
    )
    print_readiness_summary(result)
    return 1 if result.blocked else 0


def cmd_routing_candidates(args: argparse.Namespace) -> int:
    print_candidates(discover_unapproved_skills(Config(repo_root())), as_json=args.json)
    return 0


def cmd_seed_routing_index(args: argparse.Namespace) -> int:
    count = seed_routing_index(Config(repo_root()))
    print(f"[routing] seeded={count}")
    return 0


def cmd_approve_skill(args: argparse.Namespace) -> int:
    approve_skill(Config(repo_root()), args.source, args.harness, reason=args.reason)
    print(f"[routing] approved {args.source} -> {args.harness}")
    return 0


def commit_audit_state(root: Path, state_changed: bool) -> None:
    if not state_changed:
        return
    run("git", "add", "state/skill-installation.json", cwd=root)
    run("git", "commit", "-m", "chore: audit skill installations", cwd=root)
    branch = run("git", "branch", "--show-current", cwd=root, capture=True).stdout.strip()
    run("git", "push", "origin", branch, cwd=root)
    print(f"[audit] Committed and pushed state on {branch}")


def cmd_update_repo(args: argparse.Namespace) -> int:
    root = repo_root()

    if not (root / ".git").is_dir():
        print("update-llm-harness: repo missing", file=sys.stderr)
        return 1

    print("== repo ==")
    print(root)

    print("== pull ==")
    run("git", "pull", "--rebase", "--autostash", "origin", "main", cwd=root, check=True)

    print("== update shared skill submodules and refresh harness links ==")
    update_submodules(root, requested=[], commit=True, push=True)

    print("== audit skill installations ==")
    result = audit_skill_installations(Config(root))
    print_audit_summary(result)
    commit_audit_state(root, result.state_changed)

    print("== git status ==")
    run("git", "status", "--short", "--branch", cwd=root, check=False)
    return 1 if result.invalid_keys else 0


DESCRIPTION = """\
Manage the llm-harness repository.

This entrypoint installs, uninstalls, and updates repository-driven LLM harness
homes such as ~/.agents, ~/.claude, ~/.codex, ~/.hermes, and ~/.config/opencode.
Skills and harness files are mirrored through symlinks driven by config.yaml
and the routing index in state/skill-routing-index.json.
"""

EPILOG = """\
Examples:
  Install all configured harnesses and skills:
    ./harness.py install

  Remove every symlink managed by this repo:
    ./harness.py uninstall

  Update all shared skill submodules and refresh links:
    ./harness.py update-skills

  Update only selected submodules and commit/push the pointer changes:
    ./harness.py update-skills --commit --push obsidian-skills mattpocock-skills

  Audit skill installations, repairing safe mismatches:
    ./harness.py audit-skills

  Audit configured runtime prerequisites without changing them:
    ./harness.py audit-readiness

  Audit project-specific engineering prerequisites:
    ./harness.py audit-readiness --project /path/to/project

  List skills awaiting routing approval:
    ./harness.py routing-candidates

  Approve a skill for a target harness:
    ./harness.py approve-skill --source shared/some-skill --harness agents

  One-shot repo maintenance (pull, update, audit, install):
    ./harness.py update-repo
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="harness.py",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        title="commands",
        metavar="COMMAND",
    )

    install_parser = subparsers.add_parser(
        "install",
        help="symlink configured skills and harness files into target homes",
        description="Symlink configured skills and harness files into target homes.",
    )
    install_parser.set_defaults(func=cmd_install)

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="remove all symlinks managed by this repo from target homes",
        description="Remove all symlinks managed by this repo from target homes.",
    )
    uninstall_parser.set_defaults(func=cmd_uninstall)

    update_parser = subparsers.add_parser(
        "update-skills",
        help="update configured submodule sources and refresh managed skill links",
        description="Update configured submodule sources and refresh managed skill links.",
    )
    update_parser.add_argument(
        "--commit",
        action="store_true",
        help="commit submodule pointer updates",
    )
    update_parser.add_argument(
        "--push",
        action="store_true",
        help="push the commit to origin (requires --commit)",
    )
    update_parser.add_argument(
        "submodule",
        nargs="*",
        metavar="SUBMODULE",
        help="specific submodules to update (default: all configured submodules)",
    )
    update_parser.set_defaults(func=cmd_update_skills)

    audit_parser = subparsers.add_parser(
        "audit-skills",
        help="repair safe managed skill links and persist verification state",
        description="Repair safe managed skill links and persist verification state.",
    )
    audit_parser.set_defaults(func=cmd_audit_skills)

    readiness_parser = subparsers.add_parser(
        "audit-readiness",
        help="report declared skill prerequisites without changing runtime state",
        description="Report declared skill prerequisites without changing runtime state.",
    )
    readiness_parser.add_argument(
        "--project",
        metavar="PATH",
        help="also check project-scoped prerequisites in this repository",
    )
    readiness_parser.set_defaults(func=cmd_audit_readiness)

    candidates_parser = subparsers.add_parser(
        "routing-candidates",
        help="list discovered skills withheld pending routing approval",
        description="List discovered skills that are withheld pending routing approval.",
    )
    candidates_parser.add_argument("--json", action="store_true", help="emit JSON output")
    candidates_parser.set_defaults(func=cmd_routing_candidates)

    seed_parser = subparsers.add_parser(
        "seed-routing-index",
        help="baseline current config-derived routes as approved",
        description="Baseline current config-derived routes as approved in the routing index.",
    )
    seed_parser.set_defaults(func=cmd_seed_routing_index)

    approve_parser = subparsers.add_parser(
        "approve-skill",
        help="approve a discovered skill for its config-selected harness",
        description="Approve a discovered skill for its config-selected harness.",
    )
    approve_parser.add_argument(
        "--source",
        required=True,
        metavar="PATH",
        help="repo-relative path to the skill directory",
    )
    approve_parser.add_argument(
        "--harness",
        required=True,
        metavar="NAME",
        help="configured target harness name (e.g. agents, claude, opencode)",
    )
    approve_parser.add_argument(
        "--reason",
        default="",
        metavar="TEXT",
        help="concise routing rationale",
    )
    approve_parser.set_defaults(func=cmd_approve_skill)

    repo_parser = subparsers.add_parser(
        "update-repo",
        help="pull, update submodules, audit, and install (intended for automation)",
        description="Pull latest repo, update submodules, audit skills, and install.",
    )
    repo_parser.set_defaults(func=cmd_update_repo)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
