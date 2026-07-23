#!/usr/bin/env python3
"""Validate strict controller task manifests and result artifacts without side effects."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_NAMES = {
    "task": "controller-task.v1.schema.json",
    "result": "controller-result.v1.schema.json",
}
ROLE_MODES = {
    "cheap_worker": "read_only",
    "coder": "write",
    "coding_expert": "read_only",
    "researcher": "read_only",
    "final_reviewer": "read_only",
}
GLOB_CHARACTERS = frozenset("*?[")


class ContractFailure(Exception):
    def __init__(self, code: str, summary: str, path: str = "<root>") -> None:
        self.code = code
        self.summary = summary
        self.path = path
        super().__init__(summary)


class DuplicateJsonKey(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(key)
        result[key] = value
    return result


def path_text(parts: Any) -> str:
    output = ""
    for part in parts:
        output += f"[{part}]" if isinstance(part, int) else (f".{part}" if output else str(part))
    return output or "<root>"


def schema_error_code(error: Any) -> str:
    path = list(error.absolute_path)
    if error.validator == "additionalProperties":
        return "unknown_field"
    if path == ["task_id"]:
        return "malformed_task_id"
    if path == ["code"]:
        return "invalid_result_code"
    return "schema_violation"


def normalize_ownership_path(value: str, path: str) -> str:
    if any(character in value for character in GLOB_CHARACTERS):
        raise ContractFailure("unrestricted_glob", "Ownership paths cannot contain glob syntax.", path)
    if value.startswith("/") or "\\" in value:
        raise ContractFailure("path_traversal", "Ownership paths must remain repository-relative.", path)
    parts = [part for part in value.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        raise ContractFailure("path_traversal", "Ownership paths cannot traverse outside their repository.", path)
    return "/".join(parts)


def normalize_ownership(ownership: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "files": [normalize_ownership_path(item, f"ownership.files[{index}]") for index, item in enumerate(ownership["files"])],
        "directory_prefixes": [
            normalize_ownership_path(item, f"ownership.directory_prefixes[{index}]")
            for index, item in enumerate(ownership["directory_prefixes"])
        ],
    }


def validate_document(document: Any, kind: str, schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ContractFailure("schema_violation", "The contract document must be a JSON object.")
    if document.get("version") != 1:
        raise ContractFailure("unsupported_schema_version", "Only contract schema version 1 is supported.", "version")

    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: (path_text(error.absolute_path), error.message))
    if errors:
        error = errors[0]
        raise ContractFailure(schema_error_code(error), error.message, path_text(error.absolute_path))

    report: dict[str, Any] = {"ok": True, "kind": kind, "code": "ok", "summary": f"{kind} contract is valid."}
    if kind == "result":
        report["task_id"] = document["task_id"]
        report["state"] = document["state"]
        return report

    dependencies = document["depends_on"]
    if len(dependencies) != len(set(dependencies)):
        raise ContractFailure("duplicate_dependency", "Dependencies must be unique.", "depends_on")
    if document["task_id"] in dependencies:
        raise ContractFailure("self_dependency", "A task cannot depend on itself.", "depends_on")
    if ROLE_MODES[document["role"]] != document["mode"]:
        raise ContractFailure("invalid_role_mode", "The selected role cannot use the requested execution mode.", "mode")
    if document["mode"] == "write" and not document["validation_commands"]:
        raise ContractFailure("writer_validation_missing", "Writer tasks require at least one validation command.", "validation_commands")

    report["task_id"] = document["task_id"]
    report["normalized_ownership"] = normalize_ownership(document["ownership"])
    return report


def emit(report: dict[str, Any], *, valid: bool) -> int:
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    if valid:
        print(f"manifest=valid kind={report['kind']} code=ok summary={report['summary']}", file=sys.stderr)
        return 0
    print(f"manifest=invalid kind={report['kind']} code={report['code']} path={report['path']} summary={report['summary']}", file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(SCHEMA_NAMES), default="task")
    parser.add_argument("--input", type=Path, required=True, help="JSON task manifest or result artifact")
    args = parser.parse_args()
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / SCHEMA_NAMES[args.kind]
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        report = validate_document(document, args.kind, schema)
        return emit(report, valid=True)
    except DuplicateJsonKey as error:
        return emit({"ok": False, "kind": args.kind, "code": "duplicate_json_key", "path": "<root>", "summary": f"Duplicate JSON key: {error}."}, valid=False)
    except json.JSONDecodeError as error:
        return emit({"ok": False, "kind": args.kind, "code": "invalid_json", "path": "<root>", "summary": error.msg}, valid=False)
    except OSError as error:
        return emit({"ok": False, "kind": args.kind, "code": "input_unavailable", "path": "<root>", "summary": str(error)}, valid=False)
    except ContractFailure as error:
        return emit({"ok": False, "kind": args.kind, "code": error.code, "path": error.path, "summary": error.summary}, valid=False)


if __name__ == "__main__":
    raise SystemExit(main())
