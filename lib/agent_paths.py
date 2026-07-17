"""Resolve non-secret, user-owned skill paths from ~/.agents configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SKILL_PATHS = Path("~/.agents/config/skill-paths.json")


def _expand(value: str, home: Path) -> Path:
    if value == "~":
        return home
    if value.startswith("~/"):
        return home / value[2:]
    return Path(value).expanduser()


def _load(config_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(config_path.read_text())
    except FileNotFoundError as exc:
        raise ValueError(f"Skill paths configuration is missing: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Skill paths configuration is invalid JSON: {config_path}") from exc
    if data.get("version") != 1:
        raise ValueError(f"Unsupported skill paths configuration: {config_path}")
    return data


def configured_path(
    name: str,
    *,
    config_path: Path | None = None,
    home: Path | None = None,
) -> Path:
    """Return a configured named path without creating it."""
    home = home or Path.home()
    config_path = config_path or DEFAULT_SKILL_PATHS.expanduser()
    value = (_load(config_path).get("paths") or {}).get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing paths.{name} in {config_path}")
    return _expand(value, home)


def artifact_directory(
    name: str,
    *,
    config_path: Path | None = None,
    home: Path | None = None,
    create: bool = False,
) -> Path:
    """Return a configured artifact directory and optionally create it."""
    home = home or Path.home()
    config_path = config_path or DEFAULT_SKILL_PATHS.expanduser()
    value = (_load(config_path).get("artifacts") or {}).get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing artifacts.{name} in {config_path}")
    result = _expand(value, home)
    if create:
        result.mkdir(parents=True, exist_ok=True)
    return result
