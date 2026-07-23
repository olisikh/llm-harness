#!/usr/bin/env python3
"""Validate a Hermes semantic model-routing policy without side effects."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


class PolicyError(Exception):
    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message


def render_path(parts: list[str | int]) -> str:
    if not parts:
        return "<root>"
    result = ""
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        elif result:
            result += f".{part}"
        else:
            result = part
    return result


def assert_unique_yaml_keys(node: Node, parts: list[str | int] | None = None) -> None:
    parts = [] if parts is None else parts
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                raise PolicyError("invalid_yaml_key", render_path(parts), "mapping keys must be scalar")
            key = str(key_node.value)
            child_parts = [*parts, key]
            if key in seen:
                raise PolicyError("duplicate_yaml_key", render_path(child_parts), "duplicate mapping key")
            seen.add(key)
            assert_unique_yaml_keys(value_node, child_parts)
    elif isinstance(node, SequenceNode):
        for index, item in enumerate(node.value):
            assert_unique_yaml_keys(item, [*parts, index])


def load_yaml(path: Path) -> Any:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PolicyError("missing_file", "<root>", f"missing {path}") from exc
    try:
        document = yaml.compose(source)
        if document is None:
            raise PolicyError("invalid_yaml", "<root>", "document must not be empty")
        assert_unique_yaml_keys(document)
        return yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise PolicyError("invalid_yaml", "<root>", str(exc).splitlines()[0]) from exc


def validate_schema(policy: Any, schema: Any) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(policy),
        key=lambda error: (list(error.absolute_path), list(error.absolute_schema_path), error.message),
    )
    if errors:
        error = errors[0]
        raise PolicyError("schema", render_path(list(error.absolute_path)), error.message)


def validate_semantics(policy: dict[str, Any]) -> None:
    roles = policy["roles"]
    for role, definition in roles.items():
        seen: set[tuple[str, str]] = set()
        for index, model in enumerate(definition["models"]):
            identity = (model["provider"], model["model"])
            if identity in seen:
                raise PolicyError(
                    "duplicate_model",
                    f"roles.{role}.models[{index}]",
                    "duplicate provider/model entry",
                )
            seen.add(identity)

    if roles["coder"]["contract"]["mode"] != "writer":
        raise PolicyError("role_contract", "roles.coder.contract.mode", "coder must be a writer")
    for role in ("cheap_worker", "coding_expert", "researcher", "final_reviewer"):
        if roles[role]["contract"]["mode"] != "read_only":
            raise PolicyError("role_contract", f"roles.{role}.contract.mode", f"{role} must be read_only")
    if "allowed_tasks" not in roles["cheap_worker"]:
        raise PolicyError("role_contract", "roles.cheap_worker.allowed_tasks", "cheap_worker requires allowed_tasks")
    for role in ("coder", "coding_expert", "researcher", "final_reviewer"):
        if "allowed_tasks" in roles[role]:
            raise PolicyError("role_contract", f"roles.{role}.allowed_tasks", "only cheap_worker may declare allowed_tasks")
    if policy["limits"]["max_expensive_workers"] > policy["limits"]["max_parallel_workers"]:
        raise PolicyError("limits", "limits.max_expensive_workers", "must not exceed max_parallel_workers")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--policy", type=Path, default=Path.home() / ".hermes" / "model-routing.yaml")
    parser.add_argument("--schema", type=Path, default=root / "schemas" / "routing-policy.v1.schema.json")
    args = parser.parse_args()

    try:
        schema = load_yaml(args.schema)
        policy = load_yaml(args.policy)
        validate_schema(policy, schema)
        validate_semantics(policy)
    except PolicyError as exc:
        print(f"ERROR [{exc.code}] {exc.path}: {exc.message}", file=sys.stderr)
        return 2

    print("routing_policy=valid")
    print("version=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
