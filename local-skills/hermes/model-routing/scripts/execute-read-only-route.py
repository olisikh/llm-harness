#!/usr/bin/env python3
"""Execute one validated read-only controller route through a provider command."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-controller-manifest.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("controller_contract", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("The controller contract validator is unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def model_metadata(entry: dict[str, Any]) -> dict[str, str]:
    metadata = {"provider": entry["provider"], "model": entry["model"]}
    if "reasoning_effort" in entry:
        metadata["reasoning_effort"] = entry["reasoning_effort"]
    return metadata


def load_manifest(manifest_path: Path, validator: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    document = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=validator.unique_object)
    schema = json.loads((ROOT / "schemas" / "controller-task.v1.schema.json").read_text(encoding="utf-8"))
    report = validator.validate_document(document, "task", schema)
    if document["mode"] != "read_only":
        raise validator.ContractFailure("invalid_role_mode", "Read-only routes require a read_only manifest mode.", "mode")
    return document, report


def invoke(command: list[str], request: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(request, separators=(",", ":")),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"kind": "transport_failure", "category": "timeout"}
    except OSError:
        return {"kind": "transport_failure", "category": "provider_error"}
    if completed.returncode != 0:
        return {"kind": "transport_failure", "category": "provider_error"}
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"kind": "failure", "category": "provider_protocol_failure"}
    return response if isinstance(response, dict) else {"kind": "failure", "category": "provider_protocol_failure"}


def valid_output(output: Any, required_fields: list[str]) -> bool:
    return isinstance(output, dict) and all(field in output for field in required_fields)


def failure(code: str, summary: str, *, selected_model: dict[str, str], timeout_seconds: int, repair_count: int, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": 1,
        "task_id": "controller-error",
        "ok": False,
        "state": "validation_failure",
        "code": code,
        "summary": summary,
        "selected_model": selected_model,
        "timeout_seconds": timeout_seconds,
        "repair_count": repair_count,
        "evidence": evidence,
        "evidence_locations": [],
    }


def execute(manifest: dict[str, Any], policy: dict[str, Any], command: list[str]) -> dict[str, Any]:
    role = manifest["role"]
    role_policy = policy["roles"].get(role)
    if role_policy is None or role_policy["contract"]["mode"] != "read_only":
        return failure("invalid_role_mode", "The selected role is not configured for read-only controller execution.", selected_model={}, timeout_seconds=0, repair_count=0, evidence=[])
    selected = model_metadata(role_policy["models"][0])
    timeout_seconds = role_policy["timeout_seconds"]
    transport_failures = set(policy["switching"]["transport_failures"])
    required_fields = manifest["output_contract"]["required_fields"]
    evidence: list[dict[str, Any]] = []
    repair_count = 0
    started = time.monotonic()

    for index, entry in enumerate(role_policy["models"]):
        selected = model_metadata(entry)
        while True:
            request = {
                "task_id": manifest["task_id"],
                "role": role,
                "model": selected,
                "timeout_seconds": timeout_seconds,
                "repair": repair_count == 1,
                "execution_spec": {
                    "acceptance_criteria": manifest["acceptance_criteria"],
                    "output_contract": manifest["output_contract"],
                    "repository": manifest["repository"],
                },
            }
            response = invoke(command, request, timeout_seconds)
            if response.get("kind") == "success" and valid_output(response.get("output"), required_fields):
                return {
                    "version": 1,
                    "task_id": manifest["task_id"],
                    "ok": True,
                    "state": "candidate_ready",
                    "code": "candidate_ready",
                    "summary": "Read-only route completed successfully.",
                    "selected_model": selected,
                    "timeout_seconds": timeout_seconds,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "repair_count": repair_count,
                    "evidence": evidence,
                    "evidence_locations": [],
                }
            if response.get("kind") == "success":
                if repair_count == 0:
                    repair_count = 1
                    continue
                return failure("output_validation_failed", "The same-model output repair did not satisfy the declared output contract.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence=evidence)

            category = response.get("category", "provider_protocol_failure")
            if response.get("kind") == "transport_failure" and category in transport_failures and index + 1 < len(role_policy["models"]):
                evidence.append({"attempt": index + 1, "category": category, "provider": selected["provider"], "model": selected["model"]})
                repair_count = 0
                break
            return failure("non_switchable_failure", "The route failed without an eligible provider/transport fallback.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence=evidence)

    return failure("provider_exhausted", "All configured provider fallbacks failed.", selected_model=selected, timeout_seconds=timeout_seconds, repair_count=repair_count, evidence=evidence)


def emit(report: dict[str, Any]) -> int:
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    status = "success" if report["ok"] else "failure"
    print(f"route={status} code={report['code']} summary={report['summary']}", file=sys.stderr)
    return 0 if report["ok"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--provider-command", nargs="+", required=True, help="Read-only provider command receiving one JSON request on stdin.")
    args = parser.parse_args()
    validator = load_validator()
    try:
        manifest, _ = load_manifest(args.manifest, validator)
        policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
        return emit(execute(manifest, policy, args.provider_command))
    except validator.DuplicateJsonKey as error:
        return emit(failure("duplicate_json_key", f"Duplicate JSON key: {error}.", selected_model={}, timeout_seconds=0, repair_count=0, evidence=[]))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as error:
        return emit(failure("input_unavailable", str(error), selected_model={}, timeout_seconds=0, repair_count=0, evidence=[]))
    except validator.ContractFailure as error:
        return emit(failure(error.code, error.summary, selected_model={}, timeout_seconds=0, repair_count=0, evidence=[]))


if __name__ == "__main__":
    raise SystemExit(main())
