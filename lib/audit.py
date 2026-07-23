"""Persistent verification of configured llm-harness skill installations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lib.config import Config
from lib.sync import sync_harness


STATE_RELATIVE_PATH = Path("state/skill-installation.json")


@dataclass(frozen=True)
class SkillAuditResult:
    new_keys: list[str]
    removed_keys: list[str]
    repaired_keys: list[str]
    invalid_keys: list[str]
    state_changed: bool


def _is_exact_target(source: Path, target: Path) -> bool:
    return target.is_symlink() and target.resolve() == source.resolve()


def _effective_skills(config: Config) -> dict[str, tuple[str, str, Path]]:
    """Return the final configured source for each harness-relative target."""
    desired: dict[str, tuple[str, str, Path]] = {}
    for harness, relative_path, source in config.list_skill_targets():
        desired[f"{harness}:{relative_path}"] = (harness, relative_path, source)
    return desired


def _state_entry(
    config: Config, harness: str, relative_path: str, source: Path, status: str
) -> dict[str, str]:
    return {
        "harness": harness,
        "path": relative_path,
        "source": source.resolve().relative_to(config.repo_root).as_posix(),
        "status": status,
    }


def _read_state(state_path: Path) -> dict[str, dict[str, dict[str, str]]]:
    if not state_path.exists():
        return {"version": 1, "skills": {}}
    data = json.loads(state_path.read_text())
    if data.get("version") != 1 or not isinstance(data.get("skills"), dict):
        raise SystemExit(f"Invalid skill audit state: {state_path}")
    return data


def _write_state(state_path: Path, state: dict[str, object]) -> bool:
    rendered = json.dumps(state, indent=2, sort_keys=True) + "\n"
    if state_path.exists() and state_path.read_text() == rendered:
        return False
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(rendered)
    return True


def audit_skill_installations(config: Config) -> SkillAuditResult:
    """Repair safe managed links, verify final mappings, and persist their state."""
    desired = _effective_skills(config)
    pre_invalid = {
        key
        for key, (harness, relative_path, source) in desired.items()
        if not _is_exact_target(
            source, config.resolve_harness_root(harness) / "skills" / relative_path
        )
    }

    for harness in config.list_harness_names():
        sync_harness(config, harness)

    state_path = config.repo_root / STATE_RELATIVE_PATH
    previous = _read_state(state_path)
    previous_skills = previous["skills"]
    current_skills: dict[str, dict[str, str]] = {}
    invalid_keys: list[str] = []

    for key, (harness, relative_path, source) in sorted(desired.items()):
        target = config.resolve_harness_root(harness) / "skills" / relative_path
        status = "complete" if _is_exact_target(source, target) else "blocked"
        if status != "complete":
            invalid_keys.append(key)
        current_skills[key] = _state_entry(
            config, harness, relative_path, source, status
        )

    state = {"version": 1, "skills": current_skills}
    state_changed = _write_state(state_path, state)
    new_keys = sorted(set(current_skills) - set(previous_skills))
    removed_keys = sorted(set(previous_skills) - set(current_skills))
    repaired_keys = sorted(key for key in pre_invalid if key not in invalid_keys)
    return SkillAuditResult(
        new_keys=new_keys,
        removed_keys=removed_keys,
        repaired_keys=repaired_keys,
        invalid_keys=invalid_keys,
        state_changed=state_changed,
    )


def print_audit_summary(result: SkillAuditResult) -> None:
    print(
        "[audit] "
        f"new={len(result.new_keys)} "
        f"removed={len(result.removed_keys)} "
        f"repaired={len(result.repaired_keys)} "
        f"blocked={len(result.invalid_keys)}"
    )
    for key in result.new_keys:
        print(f"[audit] New: {key}")
    for key in result.removed_keys:
        print(f"[audit] Removed: {key}")
    for key in result.repaired_keys:
        print(f"[audit] Repaired: {key}")
    for key in result.invalid_keys:
        print(f"[audit] BLOCKED: {key}")
