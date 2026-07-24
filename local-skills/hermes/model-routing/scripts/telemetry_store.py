#!/usr/bin/env python3
"""Metadata-only telemetry store for model-routing runs.

Records one JSON line per run. Stores only role, selected model, duration,
outcome category, repair count, and validation/scope flags. Explicitly
rejects prompts, source content, model outputs, command output, credentials,
and secrets.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path(os.environ.get("MODEL_ROUTING_TELEMETRY_LOG") or (Path.home() / ".hermes" / "state" / "model-routing-telemetry.jsonl"))
DEFAULT_MAX_AGE_DAYS = 30
DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024

# Keys that must never appear in a telemetry record.
_DENIED_KEYS = frozenset({
    "prompt", "input", "output", "source", "code", "diff", "patch",
    "command_output", "stdout", "stderr", "log", "content", "text",
    "secret", "credential", "token", "api_key", "password", "env",
    "authorization", "auth", "key", "private_key", "certificate",
})

# Allowed top-level keys. Extra keys are rejected.
_ALLOWED_KEYS = frozenset({
    "run_id", "recorded_at", "request_kind", "parent_task_id", "task_id",
    "role", "provider", "model", "reasoning_effort", "duration_ms",
    "repair_count", "outcome", "validation_passed", "scope_violation",
})

# Outcome values must be stable, content-free categories.
_ALLOWED_OUTCOMES = frozenset({
    "success", "validation_failure", "scope_violation", "base_changed",
    "review_rejected", "worker_failed", "worker_timeout", "provider_exhausted",
    "transport_failure", "cancelled", "integration_conflict",
    "integration_validation_failed", "repository_diverged", "other",
})


def normalize_outcome(state: str | None) -> str:
    if state in ("candidate_ready", "locally_integrated"):
        return "success"
    if state in _ALLOWED_OUTCOMES:
        return state
    return "other"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _reject_if_bad(record: dict[str, Any]) -> None:
    for key in record:
        if key in _DENIED_KEYS:
            raise ValueError(f"telemetry key not allowed: {key}")
        if key not in _ALLOWED_KEYS:
            raise ValueError(f"telemetry key not allowed: {key}")
    if record.get("outcome") not in _ALLOWED_OUTCOMES:
        raise ValueError(f"telemetry outcome not allowed: {record.get('outcome')}")
    for key in ("duration_ms", "repair_count"):
        value = record.get(key)
        if value is not None and not isinstance(value, int):
            raise ValueError(f"telemetry {key} must be an integer")
    for key in ("validation_passed", "scope_violation"):
        value = record.get(key)
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"telemetry {key} must be a boolean")
    for key in ("task_id", "role", "provider", "model", "run_id"):
        value = record.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 256):
            raise ValueError(f"telemetry {key} must be a short string")


def record(record: dict[str, Any], log_path: Path | None = None) -> Path:
    """Append one validated telemetry record. Returns the log path."""
    target = log_path or DEFAULT_LOG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_if_bad(record)
    if "recorded_at" not in record:
        record["recorded_at"] = _now_iso()
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return target


def _parse_line(line: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            return None
        if "recorded_at" not in parsed:
            return None
        return parsed
    except json.JSONDecodeError:
        return None


def _line_bytes(line: str) -> int:
    return len(line.encode("utf-8")) + 1  # include newline


def prune(
    log_path: Path | None = None,
    *,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
    now: datetime | None = None,
) -> tuple[Path, int, int]:
    """Age-prune then size-prune telemetry. Returns (path, kept, removed)."""
    target = log_path or DEFAULT_LOG_PATH
    if not target.exists():
        return target, 0, 0
    cutoff = (now or datetime.now(timezone.utc)).timestamp() - max_age_days * 24 * 3600
    with target.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()

    survivors: list[tuple[dict[str, Any], str]] = []
    removed = 0
    for line in lines:
        stripped = line.rstrip("\n")
        parsed = _parse_line(stripped)
        if parsed is None:
            removed += 1
            continue
        try:
            timestamp = datetime.fromisoformat(parsed["recorded_at"]).timestamp()
        except ValueError:
            removed += 1
            continue
        if timestamp < cutoff:
            removed += 1
            continue
        survivors.append((parsed, stripped))

    # Size cap: remove oldest first.
    total = sum(_line_bytes(line) for _, line in survivors)
    while survivors and total > max_size_bytes:
        survivors.sort(key=lambda item: item[0]["recorded_at"])
        _, removed_line = survivors.pop(0)
        total -= _line_bytes(removed_line)
        removed += 1

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".jsonl.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        for _, line in survivors:
            handle.write(line + "\n")
    temp.replace(target)
    return target, len(survivors), removed
