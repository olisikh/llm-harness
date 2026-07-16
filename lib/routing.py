"""Skill routing index: discovery, approval, and install gating."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lib.config import Config


INDEX_RELATIVE_PATH = Path("state/skill-routing-index.json")


@dataclass(frozen=True)
class RoutingCandidate:
    source: str
    harness: str
    path: str


def _index_path(config: Config) -> Path:
    return config.repo_root / INDEX_RELATIVE_PATH


def _write_index(config: Config, skills: dict[str, dict[str, str]]) -> None:
    path = _index_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps({"version": 1, "skills": skills}, indent=2, sort_keys=True) + "\n"
    path.write_text(rendered)


def _raw_skills(config: Config) -> dict[str, RoutingCandidate]:
    return {
        source: RoutingCandidate(source=source, harness=harness, path=path)
        for source, harness, path, _ in config.list_discovered_skills()
    }


def discover_unapproved_skills(config: Config) -> list[RoutingCandidate]:
    """Return skills absent from the index or no longer matching config routing."""
    index = config.routing_index() or {"skills": {}}
    approved = index["skills"]
    candidates = []
    for source, candidate in _raw_skills(config).items():
        record = approved.get(source)
        if (
            not isinstance(record, dict)
            or record.get("harness") != candidate.harness
            or record.get("path") != candidate.path
        ):
            candidates.append(candidate)
    return sorted(candidates, key=lambda candidate: candidate.source)


def seed_routing_index(config: Config) -> int:
    """Record the current config-derived routing as the initial approved baseline."""
    skills = {
        source: {"harness": candidate.harness, "path": candidate.path}
        for source, candidate in _raw_skills(config).items()
    }
    _write_index(config, skills)
    return len(skills)


def approve_skill(config: Config, source: str, harness: str, reason: str = "") -> None:
    """Approve a discovered skill only for the harness currently selected by config."""
    candidate = _raw_skills(config).get(source)
    if candidate is None:
        raise SystemExit(f"Unknown discovered skill: {source}")
    if candidate.harness != harness:
        raise SystemExit(
            f"Config routes {source} to {candidate.harness}; update config.yaml before approving {harness}"
        )

    index = config.routing_index() or {"version": 1, "skills": {}}
    skills = dict(index["skills"])
    record = {"harness": candidate.harness, "path": candidate.path}
    if reason:
        record["reason"] = reason
    skills[source] = record
    _write_index(config, skills)


def print_candidates(candidates: list[RoutingCandidate], as_json: bool = False) -> None:
    if as_json:
        print(
            json.dumps(
                [
                    {"source": candidate.source, "harness": candidate.harness, "path": candidate.path}
                    for candidate in candidates
                ],
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(f"[routing] unapproved={len(candidates)}")
    for candidate in candidates:
        print(
            f"[routing] {candidate.source} -> {candidate.harness}/skills/{candidate.path}"
        )
