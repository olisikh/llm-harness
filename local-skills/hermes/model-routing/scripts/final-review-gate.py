#!/usr/bin/env python3
"""Final Sol review gate for staged integration results.

Reads a task manifest batch and an integration report. If the request used no
routed writer, it bypasses review. Otherwise it invokes a fixed final reviewer
(Sol/high, 10m timeout, no fallback) with the full integrated diff, validation
evidence, role rationales, and unresolved issues. PASS lets integration
continue; REJECT returns a strict review_rejected artifact.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-controller-manifest.py"

FINAL_REVIEWER_ROLE = "final_reviewer"
FINAL_REVIEWER_TIMEOUT_SECONDS = 600


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("controller_contract", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("The controller contract validator is unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_output(repository: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(repository), *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def failure(
    code: str,
    summary: str,
    *,
    state: str = "validation_failure",
    evidence_locations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "task_id": "final-review",
        "ok": False,
        "state": state,
        "code": code,
        "summary": summary,
        "evidence": [],
        "evidence_locations": evidence_locations or [],
    }


def load_documents(batch_path: Path, integration_path: Path, validator: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = json.loads(batch_path.read_text(encoding="utf-8"), object_pairs_hook=validator.unique_object)
    integration = json.loads(integration_path.read_text(encoding="utf-8"), object_pairs_hook=validator.unique_object)
    if not isinstance(tasks, list) or not tasks:
        raise validator.ContractFailure("schema_violation", "A review batch must be a non-empty JSON array.")
    if not isinstance(integration, dict):
        raise validator.ContractFailure("schema_violation", "An integration report must be a JSON object.")
    task_schema = json.loads((ROOT / "schemas" / "controller-task.v1.schema.json").read_text(encoding="utf-8"))
    result_schema = json.loads((ROOT / "schemas" / "controller-result.v1.schema.json").read_text(encoding="utf-8"))
    task_ids: set[str] = set()
    for task in tasks:
        validator.validate_document(task, "task", task_schema)
        if task["task_id"] in task_ids:
            raise validator.ContractFailure("duplicate_task_id", "Review batch task IDs must be unique.")
        task_ids.add(task["task_id"])
    validator.validate_document(integration, "result", result_schema)
    return tasks, integration


def review_required(tasks: list[dict[str, Any]]) -> bool:
    return any(task["mode"] == "write" for task in tasks)


def build_review_payload(
    tasks: list[dict[str, Any]],
    integration: dict[str, Any],
    repository: Path,
    base_commit: str,
    integration_commit: str,
    unresolved_issues: list[str],
) -> dict[str, Any]:
    diff_process = subprocess.run(
        ["git", "-C", str(repository), "diff", f"{base_commit}..{integration_commit}"],
        capture_output=True,
        text=True,
        check=False,
    )
    diff = diff_process.stdout if diff_process.returncode == 0 else ""
    return {
        "task_ids": [task["task_id"] for task in tasks],
        "role_rationales": {task["task_id"]: task["role_rationale"] for task in tasks},
        "base_commit": base_commit,
        "integration_commit": integration_commit,
        "validation": integration.get("validation", []),
        "unresolved_issues": unresolved_issues,
        "diff": diff,
        "timeout_seconds": FINAL_REVIEWER_TIMEOUT_SECONDS,
    }


def invoke_reviewer(command: list[str], payload: dict[str, Any]) -> dict[str, Any]:
    timeout = int(os.environ.get("MODEL_ROUTING_REVIEW_TIMEOUT_SECONDS", str(FINAL_REVIEWER_TIMEOUT_SECONDS)))
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload, separators=(",", ":")),
            capture_output=True,
            text=True,
            timeout=timeout,
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


def valid_verdict(response: dict[str, Any]) -> tuple[bool, str, list[dict[str, Any]]]:
    if not isinstance(response.get("verdict"), str) or response["verdict"] not in ("PASS", "REJECT"):
        return False, "malformed_verdict", []
    findings = response.get("findings")
    if not isinstance(findings, list):
        return False, "malformed_verdict", []
    for finding in findings:
        if not isinstance(finding, dict) or "severity" not in finding or "summary" not in finding:
            return False, "malformed_verdict", []
        if finding["severity"] not in ("blocking", "warning", "info"):
            return False, "malformed_verdict", []
    return True, response["verdict"], findings


def gate(
    tasks: list[dict[str, Any]],
    integration: dict[str, Any],
    command: list[str] | None,
    unresolved_issues: list[str],
    policy_path: Path | None,
) -> dict[str, Any]:
    if integration.get("ok") is not True or integration.get("state") != "locally_integrated" or not isinstance(integration.get("integration_commit"), str):
        return failure("integration_not_ready", "Final review requires a successful locally_integrated report with an integration_commit.")
    repository = Path(tasks[0]["repository"]["path"]).resolve()
    base_commit = integration["base_commit"]
    integration_commit = integration["integration_commit"]
    if not review_required(tasks):
        return {
            "version": 1,
            "task_id": "final-review",
            "ok": True,
            "state": "locally_integrated",
            "code": "locally_integrated",
            "summary": "No routed writer was used; final review bypassed.",
            "evidence": [],
            "evidence_locations": [],
        }
    if command is None:
        return failure("reviewer_command_missing", "A final reviewer command is required when routed writers were used.")
    if policy_path is not None:
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        role_policy = policy.get("roles", {}).get(FINAL_REVIEWER_ROLE)
        if role_policy is None or role_policy.get("contract", {}).get("mode") != "read_only":
            return failure("invalid_reviewer_role", "The policy does not define final_reviewer as a read-only role.")
        first_model = (role_policy.get("models") or [None])[0]
        if first_model is None or first_model.get("model") != "gpt-5.6-sol" or first_model.get("reasoning_effort") != "high":
            return failure("invalid_reviewer_role", "The final reviewer model is not fixed to Sol/high.")
    payload = build_review_payload(tasks, integration, repository, base_commit, integration_commit, unresolved_issues)
    started = time.monotonic()
    response = invoke_reviewer(command, payload)
    duration_ms = round((time.monotonic() - started) * 1000)
    if response.get("kind") == "transport_failure":
        return failure(
            "reviewer_transport_failure",
            "The final reviewer could not be reached; the gate is not bypassed.",
            evidence_locations=[],
        )
    if response.get("kind") != "success":
        return failure("reviewer_failure", "The final reviewer returned a failure response.")
    valid, verdict, findings = valid_verdict(response)
    if not valid:
        return failure("malformed_verdict", "The final reviewer returned a verdict that does not match the strict schema.")
    if verdict == "PASS" and not [finding for finding in findings if finding.get("severity") == "blocking"]:
        return {
            "version": 1,
            "task_id": "final-review",
            "ok": True,
            "state": "locally_integrated",
            "code": "locally_integrated",
            "summary": "Final review PASS; integration approved.",
            "evidence": [],
            "evidence_locations": [],
        }
    return failure("review_rejected", "Final review REJECT; integration stopped before updating the active branch.", state="review_rejected")


def emit(report: dict[str, Any]) -> int:
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    status = "success" if report["ok"] else "failure"
    print(f"final_review={status} code={report['code']} summary={report['summary']}", file=sys.stderr)
    return 0 if report["ok"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, type=Path, help="JSON array of task manifests")
    parser.add_argument("--integration-report", required=True, type=Path, help="Integration report JSON artifact")
    parser.add_argument("--reviewer-command", nargs=argparse.REMAINDER, help="Reviewer command receiving one JSON request on stdin")
    parser.add_argument("--unresolved-issue", action="append", default=[], help="Unresolved issue text for reviewer context")
    parser.add_argument("--policy", type=Path, help="Routing policy YAML (required to verify reviewer role configuration)")
    args = parser.parse_args()
    validator = load_validator()
    try:
        tasks, integration = load_documents(args.batch, args.integration_report, validator)
        return emit(gate(tasks, integration, args.reviewer_command if review_required(tasks) else None, args.unresolved_issue or [], args.policy))
    except validator.DuplicateJsonKey as error:
        return emit(failure("duplicate_json_key", f"Duplicate JSON key: {error}."))
    except validator.ContractFailure as error:
        return emit(failure(error.code, error.summary))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as error:
        return emit(failure("input_unavailable", str(error)))


if __name__ == "__main__":
    raise SystemExit(main())
