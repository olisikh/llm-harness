---
name: model-routing
description: Hermes-only deterministic routing policy. Use for non-trivial, parallelizable, coding, research, ambiguous, high-risk, or repeatedly failing work. Read ~/.hermes/model-routing.yaml and run the controller from ~/.llm-harness/local-skills/hermes/model-routing/scripts before selecting a route, model, fallback, or escalation path.
version: 2.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [model-routing, delegation, orchestration, cost-control, opencode]
    related_skills: [hermes-agent-devops, harness-managed-skills]
---

# Hermes Model Routing

This skill is **Hermes-only**. It relies on Hermes `delegate_task`, Hermes provider names, `~/.hermes/config.yaml` for native runtime values, and the deterministic controller in `~/.llm-harness/local-skills/hermes/model-routing/`.

## Source of truth

The semantic policy file is:

```text
~/.hermes/model-routing.yaml
```

It declaratively defines:

- ordered model chains for every role;
- role contracts (`read_only` or `writer`);
- cheap-worker allowed tasks;
- switching rules (transport failures, retries, same-model repairs, escalation);
- hard concurrency limits;
- isolation mode (`git_worktree`);
- review requirements.

It does **not** duplicate `model.*`, `delegation.*`, or `fallback_providers` from `config.yaml`. Those remain native runtime values in `~/.hermes/config.yaml`.

### Read-only validation

Validate the policy without touching `config.yaml`:

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/scripts/validate-model-routing.py
```

Expected output:

```text
routing_policy=valid
version=1
```

The old `sync-model-routing-config.py --check/--print/--apply` projection script is gone; `config.yaml` is edited directly for native runtime values and is never rewritten by the routing machinery.

## Routing loop

1. Frame the task: objective, acceptance criteria, scope, privacy constraints, required evidence, and rollback for high-impact work.
2. Read `model-routing.yaml` and choose the lowest capable route.
3. Build a strict version-1 controller task manifest (or batch). The controller validates it, schedules it, runs it, and produces a result artifact.
4. Validate independently with tools, tests, source evidence, or file inspection.
5. Escalate to the next role only when the YAML switching conditions are met.

Never delegate a task that direct or deterministic tools can perform more cheaply and reliably.

## Route selection

```text
One clear answer or a few dependent tool calls?
  -> Direct tools in the parent.

Mechanical processing, tests, builds, lint, schema checks, or reduction?
  -> execute_code, terminal, or file tools.

Two or more independent bounded tasks from roles.cheap_worker.allowed_tasks?
  -> Controller read-only route (cheap_worker) or native delegate_task batch.

Coding implementation owner?
  -> Controller writer route (coder).

Read-only architecture, design, or diagnosis oracle?
  -> Controller read-only route (coding_expert) or explicit Sol process.

Read-only evidence and findings?
  -> Controller read-only route (researcher).

Architecture, security-sensitive work, conflicting results, repeated failures,
failed validation, or high-impact action?
  -> final_reviewer once per routed request, only after routed writers complete.
```

## Roles

| Role | Mode | Ordered primary models | Timeout | Allowed tasks (cheap_worker only) |
|---|---|---|---|---|
| cheap_worker | read_only | Luna/low; DeepSeek V4 Flash | 5 m | extraction, classification, bounded_summary, file_or_repository_discovery, simple_comparison, first_pass_research |
| coder | writer | Terra/high; Kimi K2.7 Code | 20 m | — |
| coding_expert | read_only | Sol/high | 10 m | — |
| researcher | read_only | Terra/high; Qwen 3.5 397B/high; DeepSeek V4 Pro/high | 15 m | — |
| final_reviewer | read_only | Sol/high | 10 m | — |

Models advance only for provider or transport failure. One same-model repair is allowed for malformed structured output; deterministic or tool failures do not switch models.

## Native Hermes delegation

`delegate_task` has no per-call model/provider override. It uses the global `delegation` projection from `config.yaml`.

- Use native children only for tasks allowed by `roles.cheap_worker.allowed_tasks`.
- Batch only independent bounded tasks.
- Keep children as leaves and enforce depth/concurrency caps.
- Pass absolute paths, URLs, constraints, expected output, and validation criteria.
- Require findings, evidence, files changed, unresolved questions, and validation status.
- Verify child claims and all external side effects in the parent.

Native children must carry a valid read-only contract. The profile guard (`~/.hermes/plugins/model-routing-guard/guard.py`) blocks terminal, arbitrary code execution, file mutation, interactive browser tools, messaging, memory, cron, task management, and external side-effect MCP namespaces. In Task 10 it remains in audit-only mode; Task 11 may enable blocking mode after E2E acceptance passes.

For a per-task specialist model that does not match the configured native spec, run an explicit OpenCode or one-shot Hermes process. Keep the handoff compact and evidence-based.

## Controller workflow

The deterministic controller lives at:

```text
~/.llm-harness/local-skills/hermes/model-routing/scripts/
```

Key scripts:

- `validate-model-routing.py` — semantic policy validation.
- `validate-controller-manifest.py` — strict task/result contract validation.
- `execute-read-only-route.py` — run one read-only routed task.
- `execute-writer-candidate.py` — produce one isolated writer candidate commit.
- `schedule-routed-tasks.py` — execute a DAG within worker/expensive caps.
- `integrate-candidates.py` — combine candidates in a dedicated worktree.
- `final-review-gate.py` — gate routed writer results with Sol.
- `manage-lifecycle.py` — cleanup and telemetry.
- `telemetry_store.py` — metadata-only telemetry store.

### Task manifest contract

Every routed task uses a version-1 JSON manifest validated by JSON Schema. It carries:

- `task_id`, `role`, `role_rationale`;
- `mode` matching the role contract (`read_only` or `write`);
- exact `repository.path` and `base_commit`;
- `depends_on` dependency edges;
- exact `ownership.files` and `directory_prefixes`;
- `validation_commands`;
- `timeout_seconds`;
- `output_contract` with `artifact_type` and `required_fields`;
- `acceptance_criteria`.

The controller rejects malformed manifests, dependency cycles, overlapping writer scopes, traversal/symlink escapes, unvalidated writers, and mutation assigned to read-only roles.

### Writer isolation

Every delegated writer gets a unique `model-routing/{task_id}-...` branch and Git worktree. Delegated mutation is unavailable outside Git repositories. The worker cannot stage or commit. The controller validates actual changed paths, runs declared checks, and creates the Conventional Commit. Results become candidate commits; integration requires an explicit orchestrator command.

### Scheduling and limits

Task manifests form a dependency DAG. Cycles are rejected; only ready tasks run.

- Maximum routed workers: 2.
- Maximum expensive workers: 1.
- Expensive roles: coder, coding_expert, researcher, final_reviewer.
- Dependency failure marks downstream work `blocked` without invoking a model.
- Cancellation or timeout stops the entire process group and leaves no newly runnable dependent task behind.

### Staged integration

The controller serially cherry-picks writer candidate commits into a separate integration worktree and runs declared combined validation. The active branch remains untouched. If any routed writer was used, Sol reviews the complete integrated result once. One rejection permits one targeted repair, full revalidation, and one re-review; a second rejection stops automation.

After review PASS, the controller fetches and rechecks upstream, then fast-forwards only the local active branch. It never pushes.

## Switching and escalation

Follow `switching` in `model-routing.yaml`.

- Transport failures (rate limit, timeout, provider error, unavailable model, auth failure, connection error) use the Hermes runtime fallback chain after the configured API retry cap; do not add unbounded retries.
- Structured output: validate locally, make only the configured same-model repair attempt, simplify the schema/deterministic work if needed, then escalate.
- Tool failures: switch models only when model behavior caused the failure. Otherwise fix the environment, files, credentials, permissions, compilers, or services directly.
- Poor/uncertain work: issue one focused repair, then climb cheap_worker → coding_expert/researcher → final_reviewer as specified by the policy.

Every provider/model switch is cold. The receiving route has no conversation, tool history, or provider prompt cache unless you include it in the handoff.

## Cost and privacy

- Treat every hosted provider as remote; do not send secrets or unnecessary private material.
- Run at most the configured number of specialists/reviewers concurrently.
- Telemetry records only metadata (`run_id`, `task_id`, `role`, `provider`, `model`, `reasoning_effort`, `duration_ms`, `repair_count`, `outcome`, `validation_passed`, `scope_violation`). No prompts, outputs, source content, or secrets are logged.
- Telemetry retention: 30 days and 10 MB.

## Handoff contract

Load `references/routing-policy.md` for the required machine-readable handoff shape and behavioral verification checklist. Preserve exact commands, sources, evidence, files changed, unresolved questions, validation status, and rollback mechanism.

## Gateway safety

Routing configuration applies to new sessions. Validate statically and through isolated one-shot CLI runs; do not restart the active gateway from a gateway-owned session. If a detached recovery gateway is active, do not modify launchd or start another gateway. Treat service repair as a separate planned maintenance task.
