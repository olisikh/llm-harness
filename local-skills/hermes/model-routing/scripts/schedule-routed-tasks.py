#!/usr/bin/env python3
"""Schedule validated routed task manifests within policy concurrency limits."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-controller-manifest.py"
EXPENSIVE_ROLES = frozenset({"coder", "coding_expert", "researcher", "final_reviewer"})
ROLE_TIMEOUTS = {"cheap_worker": 300, "coder": 1200, "coding_expert": 600, "researcher": 900, "final_reviewer": 600}
SUCCESS_STATE = "candidate_ready"
TERMINAL_STATES = frozenset({SUCCESS_STATE, "failed", "blocked", "cancelled", "timed_out"})


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("controller_contract", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("The controller contract validator is unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report_failure(code: str, summary: str) -> dict[str, Any]:
    return {"version": 1, "ok": False, "state": "validation_failure", "code": code, "summary": summary, "tasks": []}


def entry(task_id: str, state: str, code: str, summary: str) -> dict[str, str]:
    return {"task_id": task_id, "state": state, "code": code, "summary": summary}


def load_batch(path: Path, validator: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, list[str]]]]:
    documents = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=validator.unique_object)
    if not isinstance(documents, list):
        raise validator.ContractFailure("schema_violation", "A scheduling batch must be a JSON array.")
    task_ids = [document.get("task_id") for document in documents if isinstance(document, dict)]
    if len(task_ids) != len(documents) or len(task_ids) != len(set(task_ids)):
        raise validator.ContractFailure("duplicate_task_id", "Batch task IDs must be present and unique.")
    schema = json.loads((ROOT / "schemas" / "controller-task.v1.schema.json").read_text(encoding="utf-8"))
    ownership: dict[str, dict[str, list[str]]] = {}
    for document in documents:
        validation = validator.validate_document(document, "task", schema)
        ownership[document["task_id"]] = validation["normalized_ownership"]
    return documents, ownership


def validate_dependencies(tasks: list[dict[str, Any]]) -> None:
    by_id = {task["task_id"]: task for task in tasks}
    for task in tasks:
        for dependency in task["depends_on"]:
            if dependency not in by_id:
                raise ValueError("missing_dependency")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError("dependency_cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id]["depends_on"]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(by_id):
        visit(task_id)


def scope_covers(scope: tuple[str, bool], path: str) -> bool:
    value, is_directory = scope
    return path == value or (is_directory and path.startswith(f"{value}/"))


def scopes_overlap(left: dict[str, list[str]], right: dict[str, list[str]]) -> bool:
    left_scopes = [(path, False) for path in left["files"]] + [(path, True) for path in left["directory_prefixes"]]
    right_scopes = [(path, False) for path in right["files"]] + [(path, True) for path in right["directory_prefixes"]]
    return any(scope_covers(first, second[0]) or scope_covers(second, first[0]) for first in left_scopes for second in right_scopes)


def validate_writer_ownership(tasks: list[dict[str, Any]], ownership: dict[str, dict[str, list[str]]]) -> None:
    writers = [task for task in tasks if task["mode"] == "write"]
    for index, first in enumerate(writers):
        for second in writers[index + 1 :]:
            if repository_identity(first["repository"]["path"]) == repository_identity(second["repository"]["path"]) and scopes_overlap(ownership[first["task_id"]], ownership[second["task_id"]]):
                raise ValueError("overlapping_writer_scope")


def repository_identity(path: str) -> Path:
    resolved = Path(path).resolve(strict=False)
    common = subprocess.run(["git", "-C", str(resolved), "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=False)
    if common.returncode == 0:
        return (resolved / common.stdout.strip()).resolve(strict=False)
    return resolved


def validate_policy(policy: dict[str, Any], tasks: list[dict[str, Any]]) -> None:
    limits = policy.get("limits")
    if not isinstance(limits, dict) or limits.get("max_parallel_workers") not in range(1, 3) or limits.get("max_expensive_workers") not in range(1, 2):
        raise ValueError("policy_limits_invalid")
    roles = policy.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("policy_roles_invalid")
    for task in tasks:
        role = roles.get(task["role"])
        if not isinstance(role, dict) or role.get("timeout_seconds") != ROLE_TIMEOUTS[task["role"]] or role["timeout_seconds"] < task["timeout_seconds"]:
            raise ValueError("manifest_timeout_exceeds_role_limit")


def drain(stream: Any, destination: list[str]) -> None:
    destination.append(stream.read())


def start_executor(command: list[str], task: dict[str, Any]) -> tuple[subprocess.Popen[str], list[str], list[str], list[threading.Thread]]:
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    assert process.stdout is not None and process.stderr is not None
    stdout: list[str] = []
    stderr: list[str] = []
    readers = [threading.Thread(target=drain, args=(process.stdout, stdout)), threading.Thread(target=drain, args=(process.stderr, stderr))]
    for reader in readers:
        reader.start()
    assert process.stdin is not None
    process.stdin.write(json.dumps({"task": task}, separators=(",", ":")))
    process.stdin.close()
    return process, stdout, stderr, readers


def stop_executor(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def read_executor_result(process: subprocess.Popen[str], task_id: str, validator: Any, stdout: list[str], readers: list[threading.Thread]) -> tuple[str, str, str]:
    for reader in readers:
        reader.join()
    output = "".join(stdout)
    if process.returncode != 0:
        return "failed", "executor_failed", "The executor exited unsuccessfully."
    try:
        result = json.loads(output, object_pairs_hook=validator.unique_object)
    except (json.JSONDecodeError, validator.DuplicateJsonKey):
        return "failed", "executor_protocol_failure", "The executor did not return one valid JSON object."
    if isinstance(result, dict) and result.get("kind") == "cancelled":
        if result.get("version") != 1 or result.get("task_id") != task_id:
            return "failed", "cancellation_contract_invalid", "The cancellation result did not identify the launched task."
        return "cancelled", "executor_cancelled", str(result.get("summary", "The executor was cancelled."))
    try:
        schema = json.loads((ROOT / "schemas" / "controller-result.v1.schema.json").read_text(encoding="utf-8"))
        validator.validate_document(result, "result", schema)
    except (validator.ContractFailure, TypeError):
        return "failed", "result_contract_invalid", "The executor returned an invalid controller result artifact."
    if result.get("task_id") != task_id:
        return "failed", "result_task_mismatch", "The executor result task ID does not match the launched task."
    if result.get("ok") is True and result.get("state") == SUCCESS_STATE:
        return SUCCESS_STATE, SUCCESS_STATE, str(result["summary"])
    return "failed", str(result.get("code", "executor_failed")), str(result.get("summary", "The executor returned a non-success result."))


def can_launch(task: dict[str, Any], running: dict[str, tuple[subprocess.Popen[str], float, dict[str, Any]]], policy: dict[str, Any]) -> bool:
    limits = policy["limits"]
    if len(running) >= limits["max_parallel_workers"]:
        return False
    if task["role"] not in EXPENSIVE_ROLES:
        return True
    expensive_running = sum(1 for _, _, active_task, _, _ in running.values() if active_task["role"] in EXPENSIVE_ROLES)
    return expensive_running < limits["max_expensive_workers"]


def schedule(tasks: list[dict[str, Any]], policy: dict[str, Any], command: list[str], validator: Any) -> dict[str, Any]:
    by_id = {task["task_id"]: task for task in tasks}
    results: dict[str, dict[str, str]] = {task_id: entry(task_id, "pending", "pending", "Awaiting dependencies.") for task_id in by_id}
    running: dict[str, tuple[subprocess.Popen[str], float, dict[str, Any], list[str], list[threading.Thread]]] = {}
    cancelled = False
    try:
        while True:
            for task_id in sorted(by_id):
                if results[task_id]["state"] == "pending" and any(results[dependency]["state"] in TERMINAL_STATES - {SUCCESS_STATE} for dependency in by_id[task_id]["depends_on"]):
                    results[task_id] = entry(task_id, "blocked", "dependency_not_successful", "A required dependency did not complete successfully.")

            launched = False
            for task_id in sorted(by_id):
                task = by_id[task_id]
                if results[task_id]["state"] != "pending" or not all(results[dependency]["state"] == SUCCESS_STATE for dependency in task["depends_on"]):
                    continue
                if not can_launch(task, running, policy):
                    continue
                try:
                    process, stdout, _, readers = start_executor(command, task)
                except OSError:
                    results[task_id] = entry(task_id, "failed", "executor_launch_failed", "The executor could not be launched.")
                    continue
                running[task_id] = (process, time.monotonic(), task, stdout, readers)
                results[task_id] = entry(task_id, "running", "running", "Executor launched.")
                launched = True

            if not running:
                if not any(item["state"] == "pending" for item in results.values()):
                    break
                if not launched:
                    for task_id, current in results.items():
                        if current["state"] == "pending":
                            results[task_id] = entry(task_id, "blocked", "scheduler_stalled", "The task could not become runnable.")
                    break

            time.sleep(0.01)
            for task_id, (process, started, task, stdout, readers) in list(running.items()):
                if process.poll() is None and time.monotonic() - started <= task["timeout_seconds"]:
                    continue
                del running[task_id]
                if process.poll() is None:
                    stop_executor(process)
                    for reader in readers:
                        reader.join()
                    results[task_id] = entry(task_id, "timed_out", "task_timeout", "The task exceeded its declared timeout.")
                    continue
                state, code, summary = read_executor_result(process, task_id, validator, stdout, readers)
                results[task_id] = entry(task_id, state, code, summary)
    except KeyboardInterrupt:
        cancelled = True
        for task_id, (process, _, _, _, readers) in running.items():
            stop_executor(process)
            for reader in readers:
                reader.join()
            results[task_id] = entry(task_id, "cancelled", "scheduler_cancelled", "The scheduler was cancelled.")
        for task_id, current in results.items():
            if current["state"] == "pending":
                results[task_id] = entry(task_id, "blocked", "scheduler_cancelled", "The scheduler was cancelled before this task could launch.")

    ordered = [results[task_id] for task_id in sorted(results)]
    ok = not cancelled and all(item["state"] == SUCCESS_STATE for item in ordered)
    return {
        "version": 1,
        "ok": ok,
        "state": "completed" if ok else "completed_with_failures",
        "code": "scheduled" if ok else "task_failures",
        "summary": "All routed tasks completed successfully." if ok else "One or more routed tasks did not complete successfully.",
        "tasks": ordered,
    }


def emit(report: dict[str, Any]) -> int:
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    status = "success" if report["ok"] else "failure"
    print(f"schedule={status} code={report['code']} summary={report['summary']}", file=sys.stderr)
    return 0 if report["ok"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, type=Path, help="JSON array of controller task manifests")
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--executor-command", nargs="+", required=True, help="Executor command receiving one task JSON request on stdin")
    args = parser.parse_args()
    validator = load_validator()
    try:
        tasks, ownership = load_batch(args.batch, validator)
        validate_dependencies(tasks)
        validate_writer_ownership(tasks, ownership)
        policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
        validate_policy(policy, tasks)
        return emit(schedule(tasks, policy, args.executor_command, validator))
    except validator.DuplicateJsonKey as error:
        return emit(report_failure("duplicate_json_key", f"Duplicate JSON key: {error}."))
    except validator.ContractFailure as error:
        return emit(report_failure(error.code, error.summary))
    except ValueError as error:
        return emit(report_failure(str(error), str(error).replace("_", " ").capitalize() + "."))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as error:
        return emit(report_failure("input_unavailable", str(error)))


if __name__ == "__main__":
    raise SystemExit(main())
