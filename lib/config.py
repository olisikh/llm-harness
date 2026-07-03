#!/usr/bin/env python3
"""Configuration loading and harness/skill discovery."""

import os
from pathlib import Path
from typing import Iterator

import yaml


DEFAULT_HARNESS_ROOTS = {
    "agents": "~/.agents",
    "claude": "~/.claude",
    "codex": "~/.codex",
}


class Config:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.harness_dir = self.repo_root / "harness"
        self.paths_file = self.repo_root / "harness-paths.yaml"
        self.sources_file = self.repo_root / "config.yaml"

    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text()) or {}

    def harness_roots(self) -> dict[str, str]:
        roots = dict(DEFAULT_HARNESS_ROOTS)
        data = self._load_yaml(self.paths_file)
        for name, root in (data.get("harness") or {}).items():
            roots[name] = os.path.expanduser(root)
        return roots

    def resolve_harness_root(self, name: str) -> Path:
        roots = self.harness_roots()
        if name not in roots:
            raise SystemExit(f"No install root configured for harness '{name}'")
        return Path(roots[name]).expanduser().resolve()

    def list_harness_names(self) -> list[str]:
        names: set[str] = set()

        if self.harness_dir.exists():
            for entry in self.harness_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    names.add(entry.name)

        data = self._load_yaml(self.paths_file)
        for name in (data.get("harness") or {}).keys():
            names.add(name)

        data = self._load_yaml(self.sources_file)
        for entry in (data.get("sources") or {}).values():
            child_sources = self._normalize_child_sources(entry)
            for source in child_sources:
                harness = source.get("harness")
                if harness:
                    names.add(harness)
            for harness in (entry.get("overrides") or {}).values():
                names.add(harness)

        return sorted(names)

    def _normalize_child_sources(self, entry: dict) -> list[dict]:
        child_sources = entry.get("sources")
        if child_sources is None:
            root = entry.get("root", "")
            harness = entry.get("harness", "")
            if root or harness:
                child_sources = [{"root": root, "harness": harness}]
            else:
                child_sources = []
        return child_sources

    def list_configured_skills(self) -> Iterator[tuple[str, str, Path]]:
        """Yield (harness_name, rel_path, source_abs) for every configured skill."""
        data = self._load_yaml(self.sources_file)
        for source_name, entry in (data.get("sources") or {}).items():
            source_base = self.repo_root / source_name
            if not source_base.exists():
                continue

            child_sources = self._normalize_child_sources(entry)
            excludes = set(entry.get("exclude") or [])
            overrides = entry.get("overrides") or {}

            for source in child_sources:
                root_rel = source.get("root", "")
                default_harness = source.get("harness", "")
                if not root_rel or not default_harness:
                    continue

                source_root = source_base / root_rel
                if not source_root.exists():
                    continue

                for current_root, dirs, files in os.walk(source_root, followlinks=False):
                    dirs.sort()
                    files.sort()
                    if "SKILL.md" in files:
                        rel = os.path.relpath(current_root, source_root)
                        if rel in excludes:
                            dirs.clear()
                            continue
                        harness = overrides.get(rel, default_harness)
                        yield (harness, rel, Path(current_root))
                        dirs.clear()

    def configured_submodule_names(self) -> list[str]:
        data = self._load_yaml(self.sources_file)
        sources = data.get("sources") or {}
        return sorted(
            name for name, entry in sources.items() if entry.get("type") == "submodule"
        )
