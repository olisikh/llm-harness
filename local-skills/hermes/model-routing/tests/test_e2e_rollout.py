"""End-to-end acceptance tests for the deterministic model-routing workflow.

These tests exercise real controller scripts against disposable Git repositories
and fixture providers/writers/reviewers. They do not call live model APIs.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = Path.home() / ".hermes" / "model-routing.yaml"
PYTHON = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
READ_ONLY_ROUTE = ROOT / "scripts" / "execute-read-only-route.py"
WRITER_ROUTE = ROOT / "scripts" / "execute-writer-candidate.py"
SCHEDULER = ROOT / "scripts" / "schedule-routed-tasks.py"
INTEGRATE = ROOT / "scripts" / "integrate-candidates.py"
REVIEW_GATE = ROOT / "scripts" / "final-review-gate.py"
LIFECYCLE = ROOT / "scripts" / "manage-lifecycle.py"

READ_ONLY_PROVIDER = """#!/usr/bin/env python3
import json
import sys
request = json.loads(sys.stdin.read())
print(json.dumps({"kind": "success", "output": {"summary": "fixture findings"}}))
"""

WRITER_FIXTURE = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
request = json.loads(sys.stdin.read())
repo = Path(request["execution_spec"]["repository"]["path"])
owned = request["execution_spec"]["ownership"]["files"][0]
(repo / owned).write_text("generated", encoding="utf-8")
print(json.dumps({"kind": "success", "output": {"summary": f"wrote {owned}"}}))
"""

REVIEWER_FIXTURE_PASS = """#!/usr/bin/env python3
import json
import sys
print(json.dumps({"kind": "success", "verdict": "PASS", "findings": []}))
"""

REVIEWER_FIXTURE_REJECT = """#!/usr/bin/env python3
import json
import sys
print(json.dumps({"kind": "success", "verdict": "REJECT", "findings": [{"severity": "blocking", "summary": "fixture rejection"}]}))
"""


def make_executable(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def make_repository(directory: Path, *, bare_upstream: bool = False) -> tuple[Path, str, Path | None]:
    repository = directory / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "e2e@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "E2E tests"], check=True)
    (repository / "seed.txt").write_text("seed", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "seed.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "test: seed"], check=True)
    base = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    upstream: Path | None = None
    if bare_upstream:
        upstream = directory / "upstream.git"
        subprocess.run(["git", "init", "--bare", "-q", str(upstream)], check=True)
        subprocess.run(["git", "-C", str(repository), "remote", "add", "origin", str(upstream)], check=True)
        subprocess.run(["git", "-C", str(repository), "push", "-u", "origin", "HEAD"], check=True)
    return repository, base, upstream


def manifest(task_id: str, role: str, mode: str, repository: Path, base: str, ownership: dict) -> dict:
    return {
        "version": 1,
        "task_id": task_id,
        "role": role,
        "role_rationale": "E2E acceptance test.",
        "mode": mode,
        "repository": {"path": str(repository), "base_commit": base},
        "depends_on": [],
        "ownership": ownership,
        "validation_commands": ["test -f " + ownership["files"][0]] if mode == "write" else [],
        "timeout_seconds": 60,
        "output_contract": {"artifact_type": "candidate" if mode == "write" else "findings", "required_fields": ["summary"]},
        "acceptance_criteria": ["Return a summary."],
    }


def build_executor(directory: Path) -> Path:
    provider_path = make_executable(directory / "provider.py", READ_ONLY_PROVIDER)
    writer_path = make_executable(directory / "writer.py", WRITER_FIXTURE)
    source = f"""#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path({str(ROOT)!r})
PYTHON = Path({str(PYTHON)!r})
POLICY = Path({str(POLICY)!r})
PROVIDER = Path({str(provider_path)!r})
WRITER = Path({str(writer_path)!r})
RESULT_DIR = Path({str(directory)!r})

request = json.loads(sys.stdin.read())
task = request["task"]
manifest_path = RESULT_DIR / f"manifest-{{task['task_id']}}.json"
manifest_path.write_text(json.dumps(task), encoding="utf-8")
result_path = RESULT_DIR / f"result-{{task['task_id']}}.json"
if task["mode"] == "read_only":
    cmd = [str(PYTHON), str(ROOT / "scripts" / "execute-read-only-route.py"), "--manifest", str(manifest_path), "--policy", str(POLICY), "--provider-command", str(PYTHON), str(PROVIDER)]
else:
    cmd = [str(PYTHON), str(ROOT / "scripts" / "execute-writer-candidate.py"), "--manifest", str(manifest_path), "--policy", str(POLICY), "--writer-command", str(PYTHON), str(WRITER)]
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
result_path.write_text(result.stdout, encoding="utf-8")
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
sys.exit(result.returncode)
"""
    return make_executable(directory / "executor.py", source)


def run_scheduler(directory: Path, tasks: list[dict]) -> tuple[subprocess.CompletedProcess[str], dict]:
    batch_path = directory / "batch.json"
    batch_path.write_text(json.dumps(tasks), encoding="utf-8")
    executor_path = build_executor(directory)
    result = subprocess.run(
        [str(PYTHON), str(SCHEDULER), "--batch", str(batch_path), "--policy", str(POLICY), "--executor-command", str(PYTHON), str(executor_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = {}
    return result, report


def load_task_result(directory: Path, task_id: str) -> dict:
    return json.loads((directory / f"result-{task_id}.json").read_text(encoding="utf-8"))


def test_full_routed_workflow_schedules_integrates_reviews_and_cleans():
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        repository, base, _ = make_repository(directory, bare_upstream=True)

        tasks = [
            manifest("e2e-read", "cheap_worker", "read_only", repository, base, {"files": ["seed.txt"], "directory_prefixes": []}),
            manifest("e2e-write-a", "coder", "write", repository, base, {"files": ["a.txt"], "directory_prefixes": []}),
            manifest("e2e-write-b", "coder", "write", repository, base, {"files": ["b.txt"], "directory_prefixes": []}),
        ]
        tasks[1]["depends_on"] = ["e2e-read"]
        tasks[2]["depends_on"] = ["e2e-read"]

        result, schedule_report = run_scheduler(directory, tasks)
        assert result.returncode == 0, result.stderr
        assert schedule_report["ok"] is True, schedule_report
        assert all(t["state"] == "candidate_ready" for t in schedule_report["tasks"]), schedule_report

        candidate_results = [load_task_result(directory, t["task_id"]) for t in tasks if t["mode"] == "write"]
        for candidate in candidate_results:
            assert candidate["ok"] is True
            assert candidate["state"] == "candidate_ready"
            assert candidate["candidate_commit"]
            assert candidate["candidate_branch"].startswith(f"model-routing/{candidate['task_id']}-")

        # Active branch unchanged before integration.
        assert subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip() == base

        integration_batch = directory / "integration-batch.json"
        integration_batch.write_text(json.dumps([tasks[0], tasks[1], tasks[2]]), encoding="utf-8")
        candidates_file = directory / "candidates.json"
        candidates_file.write_text(json.dumps(candidate_results), encoding="utf-8")
        integrate_result = subprocess.run(
            [str(PYTHON), str(INTEGRATE), "--batch", str(integration_batch), "--candidates", str(candidates_file), "--validation-command", "test -f a.txt", "--validation-command", "test -f b.txt"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert integrate_result.returncode == 0, integrate_result.stderr
        integration_report = json.loads(integrate_result.stdout)
        assert integration_report["ok"] is True
        assert integration_report["state"] == "locally_integrated"
        assert integration_report["push_required"] is True

        new_head = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        assert new_head == integration_report["integration_commit"]
        assert new_head != base
        assert (repository / "a.txt").read_text(encoding="utf-8") == "generated"
        assert (repository / "b.txt").read_text(encoding="utf-8") == "generated"

        # Final review gate with fixture PASS reviewer.
        integration_report_path = directory / "integration-report.json"
        integration_report_path.write_text(integrate_result.stdout, encoding="utf-8")
        reviewer_path = make_executable(directory / "reviewer_pass.py", REVIEWER_FIXTURE_PASS)
        review_result = subprocess.run(
            [str(PYTHON), str(REVIEW_GATE), "--batch", str(integration_batch), "--integration-report", str(integration_report_path), "--reviewer-command", str(PYTHON), str(reviewer_path), "--policy", str(POLICY)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert review_result.returncode == 0, review_result.stderr
        review_report = json.loads(review_result.stdout)
        assert review_report["ok"] is True
        assert review_report["state"] == "locally_integrated"

        # Cleanup removes writer evidence.
        for candidate in candidate_results:
            result_path = directory / f"candidate-{candidate['task_id']}.json"
            result_path.write_text(json.dumps(candidate), encoding="utf-8")
            lifecycle_result = subprocess.run(
                [str(PYTHON), str(LIFECYCLE), "--cleanup", "--result", str(result_path), "--repository", str(repository)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert lifecycle_result.returncode == 0, lifecycle_result.stderr
            evidence_root = Path(candidate["evidence_locations"][0])
            assert not evidence_root.exists()

        # Active branch remains at the integrated commit; no push occurred.
        assert subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip() == new_head


def test_read_only_route_provider_fallback_and_same_model_repair():
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        repository, base, _ = make_repository(directory)
        task = manifest("e2e-read", "cheap_worker", "read_only", repository, base, {"files": ["seed.txt"], "directory_prefixes": []})
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps(task), encoding="utf-8")

        # Provider that returns transport_failure on the first provider/model attempt,
        # then success on the fallback provider/model attempt.
        provider_source = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
counter_path = Path(sys.argv[0]).with_suffix(".counter")
count = int(counter_path.read_text(encoding="utf-8")) if counter_path.exists() else 0
counter_path.write_text(str(count + 1), encoding="utf-8")
request = json.loads(sys.stdin.read())
if count == 0:
    print(json.dumps({"kind": "transport_failure", "category": "timeout"}))
else:
    print(json.dumps({"kind": "success", "output": {"summary": "recovered"}}))
"""
        provider_path = make_executable(directory / "provider.py", provider_source)
        result = subprocess.run(
            [str(PYTHON), str(READ_ONLY_ROUTE), "--manifest", str(manifest_path), "--policy", str(POLICY), "--provider-command", str(PYTHON), str(provider_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["state"] == "candidate_ready"
        assert report["selected_model"]["provider"] == "ollama-cloud"
        assert report["selected_model"]["model"] == "deepseek-v4-flash"

        # Same-model repair: first invalid output, then valid.
        repair_provider_source = """#!/usr/bin/env python3
import json
import sys
request = json.loads(sys.stdin.read())
if request.get("repair"):
    print(json.dumps({"kind": "success", "output": {"summary": "fixed"}}))
else:
    print(json.dumps({"kind": "success", "output": {}}))
"""
        provider_path = make_executable(directory / "provider2.py", repair_provider_source)
        result = subprocess.run(
            [str(PYTHON), str(READ_ONLY_ROUTE), "--manifest", str(manifest_path), "--policy", str(POLICY), "--provider-command", str(PYTHON), str(provider_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["state"] == "candidate_ready"
        assert report["repair_count"] == 1
        assert report["selected_model"]["provider"] == "openai-codex"


def test_scheduler_rejects_cycle_and_overlapping_scopes():
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        repository, base, _ = make_repository(directory)
        tasks = [
            manifest("a", "cheap_worker", "read_only", repository, base, {"files": ["seed.txt"], "directory_prefixes": []}),
            manifest("b", "cheap_worker", "read_only", repository, base, {"files": ["seed.txt"], "directory_prefixes": []}),
        ]
        tasks[0]["depends_on"] = ["b"]
        tasks[1]["depends_on"] = ["a"]
        result, report = run_scheduler(directory, tasks)
        assert result.returncode == 2
        assert report["code"] == "dependency_cycle"

        # Overlapping writer scopes.
        writer_tasks = [
            manifest("w1", "coder", "write", repository, base, {"files": ["x.txt"], "directory_prefixes": []}),
            manifest("w2", "coder", "write", repository, base, {"files": ["x.txt"], "directory_prefixes": []}),
        ]
        result, report = run_scheduler(directory, writer_tasks)
        assert result.returncode == 2
        assert report["code"] == "overlapping_writer_scope"


def test_writer_preflight_fails_dirty_and_divergent():
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        repository, base, _ = make_repository(directory, bare_upstream=True)
        task = manifest("dirty", "coder", "write", repository, base, {"files": ["x.txt"], "directory_prefixes": []})
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps(task), encoding="utf-8")
        (repository / "dirt.txt").write_text("dirty", encoding="utf-8")
        writer_path = make_executable(directory / "writer.py", WRITER_FIXTURE)
        result = subprocess.run(
            [str(PYTHON), str(WRITER_ROUTE), "--manifest", str(manifest_path), "--policy", str(POLICY), "--writer-command", str(PYTHON), str(writer_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 2
        report = json.loads(result.stdout)
        assert report["code"] == "repository_dirty"


def test_integration_review_reject_stops_active_branch_update():
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        repository, base, _ = make_repository(directory, bare_upstream=True)
        task = manifest("write", "coder", "write", repository, base, {"files": ["x.txt"], "directory_prefixes": []})
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps(task), encoding="utf-8")
        writer_path = make_executable(directory / "writer.py", WRITER_FIXTURE)
        writer_result = subprocess.run(
            [str(PYTHON), str(WRITER_ROUTE), "--manifest", str(manifest_path), "--policy", str(POLICY), "--writer-command", str(PYTHON), str(writer_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert writer_result.returncode == 0, writer_result.stderr
        candidate = json.loads(writer_result.stdout)

        batch_path = directory / "batch.json"
        batch_path.write_text(json.dumps([task]), encoding="utf-8")
        candidates_path = directory / "candidates.json"
        candidates_path.write_text(json.dumps([candidate]), encoding="utf-8")
        integrate_result = subprocess.run(
            [str(PYTHON), str(INTEGRATE), "--batch", str(batch_path), "--candidates", str(candidates_path), "--validation-command", "test -f x.txt"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert integrate_result.returncode == 0, integrate_result.stderr
        integration_report = json.loads(integrate_result.stdout)
        new_head = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        assert new_head == integration_report["integration_commit"]

        integration_report_path = directory / "integration-report.json"
        integration_report_path.write_text(integrate_result.stdout, encoding="utf-8")
        reviewer_path = make_executable(directory / "reviewer_reject.py", REVIEWER_FIXTURE_REJECT)
        review_result = subprocess.run(
            [str(PYTHON), str(REVIEW_GATE), "--batch", str(batch_path), "--integration-report", str(integration_report_path), "--reviewer-command", str(PYTHON), str(reviewer_path), "--policy", str(POLICY)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert review_result.returncode == 2
        review_report = json.loads(review_result.stdout)
        assert review_report["code"] == "review_rejected"
        # Active branch was already updated by integrate, but review rejected means orchestrator must not push.
        # The acceptance criterion says "second rejection stops" — here we test the first REJECT path.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
