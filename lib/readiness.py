"""Read-only readiness checks for configured skill prerequisites."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from lib.agent_paths import artifact_directory


@dataclass(frozen=True)
class SkillReadinessResult:
    ready: list[str]
    blocked: dict[str, list[str]]
    optional_missing: dict[str, list[str]]
    not_checked: list[str]


def _expand_path(value: str, home: Path) -> Path:
    if value == "~":
        return home
    if value.startswith("~/"):
        return home / value[2:]
    return Path(value).expanduser()


def _requirement_status(
    requirement: dict,
    *,
    skill_paths_path: Path,
    home: Path,
    environ: Mapping[str, str],
    project: Path | None,
) -> tuple[bool | None, str]:
    kind = requirement.get("type")
    if kind == "artifact_directory":
        name = requirement.get("name")
        try:
            path = artifact_directory(name, config_path=skill_paths_path, home=home)
        except ValueError:
            return False, f"artifact_directory:{name}"
        return path.is_dir(), f"artifact_directory:{name}"
    if kind == "path":
        path = _expand_path(requirement["path"], home)
        expected = requirement.get("kind", "any")
        if expected == "directory":
            return path.is_dir(), f"directory:{path}"
        if expected == "file":
            return path.is_file(), f"file:{path}"
        return path.exists(), f"path:{path}"
    if kind == "command":
        name = requirement["name"]
        return shutil.which(name) is not None, f"command:{name}"
    if kind == "environment":
        name = requirement["name"]
        return bool(environ.get(name)), f"environment:{name}"
    if kind == "project_file":
        if project is None:
            return None, f"project_file:{requirement['path']}"
        path = project / requirement["path"]
        return path.is_file(), f"project_file:{requirement['path']}"
    raise ValueError(f"Unsupported readiness requirement type: {kind}")


def audit_skill_readiness(
    manifest_path: Path,
    *,
    skill_paths_path: Path,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    project: Path | None = None,
) -> SkillReadinessResult:
    """Evaluate declared prerequisites without making changes."""
    home = home or Path.home()
    environ = environ or os.environ
    data = yaml.safe_load(manifest_path.read_text()) or {}
    if data.get("version") != 1 or not isinstance(data.get("skills"), dict):
        raise ValueError(f"Invalid skill readiness manifest: {manifest_path}")

    ready: list[str] = []
    blocked: dict[str, list[str]] = {}
    optional_missing: dict[str, list[str]] = {}
    not_checked: list[str] = []

    for skill, entry in sorted(data["skills"].items()):
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid readiness entry for {skill}")
        missing: list[str] = []
        optional: list[str] = []
        skipped = False
        for requirement in entry.get("requirements") or []:
            status, label = _requirement_status(
                requirement,
                skill_paths_path=skill_paths_path,
                home=home,
                environ=environ,
                project=project,
            )
            if status is None:
                skipped = True
            elif not status:
                (optional if requirement.get("optional", False) else missing).append(label)
        if missing:
            blocked[skill] = missing
        elif skipped:
            not_checked.append(skill)
        elif not optional:
            ready.append(skill)
        if optional:
            optional_missing[skill] = optional

    return SkillReadinessResult(
        ready=ready,
        blocked=blocked,
        optional_missing=optional_missing,
        not_checked=not_checked,
    )


def print_readiness_summary(result: SkillReadinessResult) -> None:
    print(
        "[readiness] "
        f"ready={len(result.ready)} "
        f"blocked={len(result.blocked)} "
        f"optional_missing={len(result.optional_missing)} "
        f"not_checked={len(result.not_checked)}"
    )
    for skill in result.ready:
        print(f"[readiness] READY: {skill}")
    for skill, requirements in result.blocked.items():
        print(f"[readiness] BLOCKED: {skill} ({', '.join(requirements)})")
    for skill, requirements in result.optional_missing.items():
        print(f"[readiness] OPTIONAL: {skill} ({', '.join(requirements)})")
    for skill in result.not_checked:
        print(f"[readiness] PROJECT REQUIRED: {skill}")
