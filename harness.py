#!/usr/bin/env python3
"""Unified entrypoint for llm-harness operations."""

import argparse
import subprocess
import sys
from pathlib import Path

from lib.config import Config
from lib.git import update_submodules
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
    return 0


def cmd_update_repo(args: argparse.Namespace) -> int:
    root = repo_root()

    if not (root / ".git").is_dir():
        print("update-llm-harness: repo missing", file=sys.stderr)
        return 1

    print("== repo ==")
    print(root)

    print("== pull ==")
    run("git", "pull", "--rebase", "--autostash", "origin", "main", cwd=root, check=True)

    print("== update shared skill submodules ==")
    update_submodules(root, requested=[], commit=True, push=True)

    print("== install harness links ==")
    cfg = Config(root)
    for name in cfg.list_harness_names():
        sync_harness(cfg, name)

    print("== git status ==")
    run("git", "status", "--short", "--branch", cwd=root, check=False)
    return 0


DESCRIPTION = """\
Manage the llm-harness repository.

This single entrypoint installs, uninstalls, and updates the repository-driven
LLM harness homes (e.g. ~/.agents, ~/.claude, ~/.codex, ~/.hermes, ~/.config/opencode).

Subcommands:
  install         Symlink configured skills and harness files into target homes.
  uninstall       Remove all symlinks managed by this repo from target homes.
  update-skills   Update pinned commits for configured git submodule skill sources.
  update-repo     Pull latest repo, update submodules (--commit --push), then install.

Examples:
  ./harness.py install
  ./harness.py uninstall
  ./harness.py update-skills
  ./harness.py update-skills obsidian-skills mattpocock-skills
  ./harness.py update-skills --commit --push
  ./harness.py update-repo
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="harness.py",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser(
        "install",
        help="symlink configured skills and harness files into target homes",
    )
    install_parser.set_defaults(func=cmd_install)

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="remove managed symlinks from target homes",
    )
    uninstall_parser.set_defaults(func=cmd_uninstall)

    update_parser = subparsers.add_parser(
        "update-skills",
        help="update pinned commits for configured submodule skill sources",
    )
    update_parser.add_argument(
        "--commit",
        action="store_true",
        help="commit submodule pointer updates",
    )
    update_parser.add_argument(
        "--push",
        action="store_true",
        help="push the commit to origin (implies --commit)",
    )
    update_parser.add_argument(
        "submodule",
        nargs="*",
        help="specific submodules to update (default: all configured submodules)",
    )
    update_parser.set_defaults(func=cmd_update_skills)

    repo_parser = subparsers.add_parser(
        "update-repo",
        help="pull, update submodules, and install (intended for automation)",
    )
    repo_parser.set_defaults(func=cmd_update_repo)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
