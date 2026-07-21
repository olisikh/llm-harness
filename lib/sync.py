#!/usr/bin/env python3
"""Install and uninstall synchronization logic."""

import os
import sys
from pathlib import Path
from typing import Callable

from lib.config import Config


def log(msg: str) -> None:
    print(f"[install] {msg}")


def warn(msg: str) -> None:
    print(f"[install] WARNING: {msg}", file=sys.stderr)


def resolve_path(path: Path | str) -> Path:
    return Path(path).resolve()


def sync_target(
    source_abs: Path,
    target_abs: Path,
    log_fn: Callable[[str], None],
    managed_root: Path | None = None,
) -> bool:
    expected = resolve_path(source_abs)

    if target_abs.is_symlink():
        resolved = resolve_path(target_abs)
        if resolved == expected:
            log_fn(f"Link already exists at {target_abs}")
            return True
        if managed_root is not None:
            try:
                resolved.relative_to(resolve_path(managed_root))
            except ValueError:
                pass
            else:
                target_abs.unlink()
                target_abs.symlink_to(source_abs)
                log_fn(f"Repaired {target_abs} -> {source_abs}")
                return True
        warn(f"Skipping existing symlink at {target_abs} (points elsewhere)")
        return False

    if target_abs.exists():
        warn(f"Skipping existing path at {target_abs}")
        return False

    target_abs.parent.mkdir(parents=True, exist_ok=True)
    target_abs.symlink_to(source_abs)
    log_fn(f"Linked {target_abs} -> {source_abs}")
    return True


def remove_stale_symlink(target_abs: Path, source_root_abs: Path) -> bool:
    if not target_abs.is_symlink():
        return False

    source_root_resolved = resolve_path(source_root_abs)
    resolved = resolve_path(target_abs)

    if resolved == source_root_resolved or str(resolved).startswith(
        str(source_root_resolved) + os.sep
    ):
        target_abs.unlink()
        print(f"[install] Removed stale {target_abs}")
        return True

    return False


def prune_empty_parent_dirs(path: Path, stop_dir: Path) -> None:
    current = path.parent
    stop = stop_dir.resolve()
    while str(current).startswith(str(stop) + os.sep):
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def list_managed_symlinks(target_skills_dir: Path, repo_root: Path) -> list[Path]:
    managed: list[Path] = []
    if not target_skills_dir.exists():
        return managed

    repo_root_resolved = repo_root.resolve()
    for current_root, dirs, files in os.walk(target_skills_dir, followlinks=False):
        dirs.sort()
        files.sort()
        for name in dirs + files:
            path = Path(current_root) / name
            if not path.is_symlink():
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            try:
                resolved.relative_to(repo_root_resolved)
            except ValueError:
                continue
            managed.append(path)
    return managed


def sync_harness(config: Config, harness_name: str) -> None:
    source_dir = config.harness_dir / harness_name
    target_root = config.resolve_harness_root(harness_name)

    if not target_root.exists():
        log(f"Skipping [{harness_name}]: {target_root} does not exist")
        return

    log(f"[{harness_name}] -> {target_root}")

    target_skills_dir = target_root / "skills"
    target_skills_dir.mkdir(parents=True, exist_ok=True)

    desired_sources: dict[Path, Path] = {}

    for harness, rel, source in config.list_configured_skills():
        if harness != harness_name:
            continue
        target = target_skills_dir / rel
        if target in desired_sources:
            warn(f"Source collision at {target}; later config wins")
        desired_sources[target] = source

    for target, source in desired_sources.items():
        sync_target(source, target, log, managed_root=config.repo_root)

    desired_target_set = set(desired_sources)
    for existing in list_managed_symlinks(target_skills_dir, config.repo_root):
        if existing in desired_target_set:
            continue
        existing.unlink()
        log(f"Removed stale {existing}")
        prune_empty_parent_dirs(existing, target_skills_dir)

    if source_dir.exists():
        for source_entry in source_dir.iterdir():
            base_name = source_entry.name
            if base_name in (".gitkeep", "skills"):
                continue
            sync_target(source_entry, target_root / base_name, log)

        for existing in target_root.iterdir():
            base_name = existing.name
            if base_name == "skills":
                continue
            source_entry = source_dir / base_name
            if source_entry.exists() or source_entry.is_symlink():
                continue
            remove_stale_symlink(existing, source_dir)


def uninstall_harness(config: Config, harness_name: str) -> None:
    source_dir = config.harness_dir / harness_name
    target_root = config.resolve_harness_root(harness_name)

    if not target_root.exists():
        print(f"[uninstall] Skipping [{harness_name}]: {target_root} does not exist")
        return

    print(f"[uninstall] [{harness_name}]")

    target_skills_dir = target_root / "skills"
    if target_skills_dir.exists():
        for existing in list_managed_symlinks(target_skills_dir, config.repo_root):
            existing.unlink()
            print(f"[uninstall] Removed {existing}")
            prune_empty_parent_dirs(existing, target_skills_dir)

    if source_dir.exists():
        for source_entry in source_dir.iterdir():
            base_name = source_entry.name
            if base_name in (".gitkeep", "skills"):
                continue
            target = target_root / base_name
            if not target.is_symlink():
                if target.exists():
                    print(f"[uninstall] WARNING: Skipping non-symlink at {target}", file=sys.stderr)
                continue
            if resolve_path(target) != resolve_path(source_entry):
                print(
                    f"[uninstall] WARNING: Skipping symlink at {target} (points elsewhere)",
                    file=sys.stderr,
                )
                continue
            target.unlink()
            print(f"[uninstall] Removed {target}")
            prune_empty_parent_dirs(target, target_root)
