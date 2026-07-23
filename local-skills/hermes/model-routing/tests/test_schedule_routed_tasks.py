"""Public CLI acceptance tests for dependency-aware routed task scheduling."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULER = ROOT / "scripts" / "schedule-routed-tasks.py"
POLICY = {
    "limits": {"max_parallel_workers": 2, "max_expensive_workers": 1},
    "roles": {
        "cheap_worker": {"timeout_seconds": 300},
        "coder": {"timeout_seconds": 1200},
        "coding_expert": {"timeout_seconds": 600},
        "researcher": {"timeout_seconds": 900},
        "final_reviewer": {"timeout_seconds": 600},
    },
}

EXECUTOR_FIXTURE = """#!/usr/bin/env python3
import fcntl
import json
import sys
import time
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text())
request = json.loads(sys.stdin.read())
task_id = request["task"]["task_id"]
log = Path(plan["log"])
lock = log.with_suffix(".lock")
def record(event):
    with lock.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        entries = json.loads(log.read_text()) if log.exists() else []
        if event["event"] == "start":
            active = {item["task_id"]: item for item in entries if item["event"] == "start"}
            for item in entries:
                if item["event"] == "finish":
                    active.pop(item["task_id"], None)
            event["active_total"] = len(active) + 1
            event["active_expensive"] = sum(item["role"] == "coder" for item in active.values()) + (event["role"] == "coder")
        entries.append(event)
        log.write_text(json.dumps(entries))
        fcntl.flock(handle, fcntl.LOCK_UN)
record({"event": "start", "task_id": task_id, "role": request["task"]["role"]})
step = plan["steps"].get(task_id, {})
time.sleep(step.get("sleep", 0))
record({"event": "finish", "task_id": task_id})
if step.get("kind") == "cancelled":
    print(json.dumps({"version": 1, "task_id": task_id, "kind": "cancelled", "summary": "executor cancelled"}))
elif step.get("kind") == "failed":
    print(json.dumps({"version": 1, "task_id": task_id, "ok": False, "state": "validation_failure", "code": "worker_failed", "summary": "planned failure"}))
else:
    print(json.dumps({"version": 1, "task_id": task_id, "ok": True, "state": "candidate_ready", "code": "candidate_ready", "summary": "completed"}))
"""


def task(task_id: str, *, role: str = "cheap_worker", depends_on: list[str] | None = None, scope: str | None = None, timeout: int = 3) -> dict:
    return {
        "version": 1,
        "task_id": task_id,
        "role": role,
        "role_rationale": "The scheduler test requires this bounded role.",
        "mode": "write" if role == "coder" else "read_only",
        "repository": {"path": "/unused", "base_commit": "0123456789abcdef"},
        "depends_on": depends_on or [],
        "ownership": {"files": [scope or f"reports/{task_id}.md"], "directory_prefixes": []},
        "validation_commands": ["true"] if role == "coder" else [],
        "timeout_seconds": timeout,
        "output_contract": {"artifact_type": "candidate" if role == "coder" else "findings", "required_fields": ["summary"]},
        "acceptance_criteria": ["Return a deterministic result."],
    }


class RoutedTaskSchedulerTests(unittest.TestCase):
    def run_scheduler(self, tasks: list[dict], steps: dict[str, dict] | None = None, policy_data: dict | None = None) -> tuple[subprocess.CompletedProcess[str], dict, list[dict]]:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            batch = directory / "batch.json"
            plan = directory / "plan.json"
            policy = directory / "policy.json"
            executor = directory / "executor.py"
            log = directory / "events.json"
            batch.write_text(json.dumps(tasks), encoding="utf-8")
            plan.write_text(json.dumps({"steps": steps or {}, "log": str(log)}), encoding="utf-8")
            policy.write_text(json.dumps(policy_data or POLICY), encoding="utf-8")
            executor.write_text(EXECUTOR_FIXTURE, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCHEDULER), "--batch", str(batch), "--policy", str(policy), "--executor-command", sys.executable, str(executor), str(plan)],
                capture_output=True,
                text=True,
                check=False,
            )
            events = json.loads(log.read_text()) if log.exists() else []
        if not result.stdout:
            raise AssertionError(f"scheduler emitted no JSON: {result.stderr}")
        return result, json.loads(result.stdout), events

    def states(self, report: dict) -> dict[str, str]:
        return {entry["task_id"]: entry["state"] for entry in report["tasks"]}

    def test_linear_chain_runs_in_dependency_order_and_emits_sorted_task_results(self):
        result, report, events = self.run_scheduler([task("third", depends_on=["second"]), task("first"), task("second", depends_on=["first"])])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([entry["task_id"] for entry in report["tasks"]], ["first", "second", "third"])
        self.assertEqual(self.states(report), {"first": "candidate_ready", "second": "candidate_ready", "third": "candidate_ready"})
        self.assertEqual([event["task_id"] for event in events if event["event"] == "start"], ["first", "second", "third"])

    def test_rejects_missing_duplicate_self_and_cycle_dependencies_before_executor_launch(self):
        cases = [
            [task("one", depends_on=["missing"])],
            [task("one"), task("one")],
            [task("one", depends_on=["one"])],
            [task("one", depends_on=["two"]), task("two", depends_on=["one"])],
        ]
        expected = ["missing_dependency", "duplicate_task_id", "self_dependency", "dependency_cycle"]
        for batch, code in zip(cases, expected, strict=True):
            with self.subTest(code=code):
                result, report, events = self.run_scheduler(batch)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(report["code"], code)
                self.assertEqual(events, [])

    def test_rejects_overlapping_writer_scopes_before_executor_launch(self):
        first = task("writer-a", role="coder")
        first["ownership"] = {"files": [], "directory_prefixes": ["docs"]}
        second = task("writer-b", role="coder", scope="docs/guide.md")
        result, report, events = self.run_scheduler([first, second])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["code"], "overlapping_writer_scope")
        self.assertEqual(events, [])

    def test_rejects_policy_limits_and_timeouts_above_the_approved_caps_before_executor_launch(self):
        excessive_limits = deepcopy(POLICY)
        excessive_limits["limits"]["max_parallel_workers"] = 3
        result, report, events = self.run_scheduler([task("one")], policy_data=excessive_limits)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["code"], "policy_limits_invalid")
        self.assertEqual(events, [])
        excessive_timeout = deepcopy(POLICY)
        excessive_timeout["roles"]["coder"]["timeout_seconds"] = 1201
        result, report, events = self.run_scheduler([task("writer", role="coder")], policy_data=excessive_timeout)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["code"], "manifest_timeout_exceeds_role_limit")
        self.assertEqual(events, [])

    def test_two_cheap_workers_run_together_but_never_more_than_two_workers(self):
        result, report, events = self.run_scheduler([task("alpha"), task("bravo"), task("charlie")], {"alpha": {"sleep": 0.15}, "bravo": {"sleep": 0.15}, "charlie": {"sleep": 0.15}})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.states(report), {"alpha": "candidate_ready", "bravo": "candidate_ready", "charlie": "candidate_ready"})
        starts = [event["task_id"] for event in events if event["event"] == "start"]
        self.assertEqual(set(starts[:2]), {"alpha", "bravo"})
        self.assertEqual(starts[2], "charlie")
        self.assertEqual(max(event["active_total"] for event in events if event["event"] == "start"), 2)

    def test_cheap_and_expensive_run_together_while_two_expensive_roles_serialize(self):
        result, report, events = self.run_scheduler(
            [task("cheap"), task("coder-a", role="coder"), task("coder-b", role="coder")],
            {"cheap": {"sleep": 0.15}, "coder-a": {"sleep": 0.15}, "coder-b": {"sleep": 0.15}},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([event["task_id"] for event in events if event["event"] == "start"][:2], ["cheap", "coder-a"])
        self.assertEqual(max(event["active_total"] for event in events if event["event"] == "start"), 2)
        self.assertEqual(max(event["active_expensive"] for event in events if event["event"] == "start"), 1)
        finish_coder_a = next(index for index, event in enumerate(events) if event["event"] == "finish" and event["task_id"] == "coder-a")
        start_coder_b = next(index for index, event in enumerate(events) if event["event"] == "start" and event["task_id"] == "coder-b")
        self.assertGreater(start_coder_b, finish_coder_a)

    def test_diamond_and_failed_or_cancelled_upstream_leave_dependents_blocked(self):
        diamond = [task("root"), task("left", depends_on=["root"]), task("right", depends_on=["root"]), task("leaf", depends_on=["left", "right"])]
        result, report, _ = self.run_scheduler(diamond)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.states(report), {"leaf": "candidate_ready", "left": "candidate_ready", "right": "candidate_ready", "root": "candidate_ready"})
        result, report, events = self.run_scheduler([task("upstream"), task("downstream", depends_on=["upstream"])], {"upstream": {"kind": "failed"}})
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.states(report), {"downstream": "blocked", "upstream": "failed"})
        self.assertEqual([event["task_id"] for event in events if event["event"] == "start"], ["upstream"])
        result, report, events = self.run_scheduler([task("cancel"), task("after-cancel", depends_on=["cancel"])], {"cancel": {"kind": "cancelled"}})
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.states(report), {"after-cancel": "blocked", "cancel": "cancelled"})
        self.assertEqual([event["task_id"] for event in events if event["event"] == "start"], ["cancel"])

    def test_timeout_prevents_dependent_launch(self):
        result, report, events = self.run_scheduler([task("slow", timeout=1), task("after-slow", depends_on=["slow"])], {"slow": {"sleep": 2}})
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.states(report), {"after-slow": "blocked", "slow": "timed_out"})
        self.assertEqual([event["task_id"] for event in events if event["event"] == "start"], ["slow"])


if __name__ == "__main__":
    unittest.main()
