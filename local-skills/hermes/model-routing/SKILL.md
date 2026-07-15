---
name: model-routing
description: Hermes-only routing policy. Use for non-trivial, parallelizable, coding, research, ambiguous, high-risk, or repeatedly failing work. Read ~/.hermes/model-routing.yaml before selecting a route, model, fallback, or escalation path.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [model-routing, delegation, orchestration, cost-control, opencode]
    related_skills: [hermes-agent-devops, harness-managed-skills]
---

# Hermes Model Routing

This skill is **Hermes-only**. It relies on Hermes `delegate_task`, Hermes provider names, `~/.hermes/config.yaml`, and the Hermes runtime policy file.

## Source of truth

Read this file before non-trivial routing decisions:

```text
~/.hermes/model-routing.yaml
```

It declaratively defines:

- ordered model chains for every role;
- the runtime projection for Hermes-native parent/delegation/fallback settings;
- cheap-worker suitability;
- escalation and switch conditions;
- cost caps, privacy, and handoff requirements.

Do **not** hard-code or silently substitute role models from this skill. Use the YAML policy. Recheck its runtime projection against `~/.hermes/config.yaml` with:

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/scripts/sync-model-routing-config.py --check
```

After an approved policy edit, inspect the projection with `--print`, then run `--apply`; it updates only routing-owned fields in `config.yaml`. Never directly change unrelated config fields.

## Routing loop

1. Frame the task: objective, acceptance criteria, scope, privacy constraints, required evidence, and rollback for high-impact work.
2. Read `model-routing.yaml` and choose the lowest capable route.
3. Pass a full brief to every fresh child or specialist process.
4. Enforce YAML concurrency, iteration, retry, and wall-clock caps.
5. Validate independently with tools, tests, source evidence, or file inspection.
6. Escalate with a compact handoff when the YAML conditions are met.

Never delegate a task that direct or deterministic tools can perform more cheaply and reliably.

## Route selection

```text
One clear answer or a few dependent tool calls?
  -> Direct tools in the parent.

Mechanical processing, tests, builds, lint, schema checks, or reduction?
  -> execute_code, terminal, or file tools.

Two or more independent bounded tasks allowed by roles.cheap_worker.allowed_tasks?
  -> Native delegate_task batch using the runtime projection.

Coding or research requiring sustained judgment or per-task model choice?
  -> The configured coding_specialist or research_specialist role.

Architecture, security-sensitive work, conflicting results, repeated failures,
failed validation, or high-impact action?
  -> final_reviewer, only when its invoke_only_for condition matches.
```

## Native Hermes delegation

`delegate_task` has no per-call model/provider override. It uses the global `delegation` projection from `config.yaml`, which is derived from `model-routing.yaml`.

- Use native children only for tasks allowed by `roles.cheap_worker.allowed_tasks`.
- Batch only independent bounded tasks.
- Keep children as leaves and enforce the YAML depth/concurrency caps.
- Pass absolute paths, URLs, constraints, expected output, and validation criteria.
- Require findings, evidence, files changed, unresolved questions, and validation status.
- Verify child claims and all external side effects in the parent.

For a per-task specialist model, run the selected YAML role through an explicit OpenCode process or a one-shot Hermes process. Keep the handoff compact and evidence-based.

## Switching and escalation

Follow `switching` in `model-routing.yaml`.

- Transport failures use the Hermes runtime fallback chain after the configured API retry cap; do not add unbounded retries.
- Structured output: validate locally, make only the configured same-model repair attempt, simplify the schema/deterministic work if needed, then escalate.
- Tool failures: switch models only when model behavior caused the failure. Otherwise fix the environment, files, credentials, permissions, compilers, or services directly.
- Poor/uncertain work: issue one focused repair, then climb cheap worker -> specialist -> reviewer as specified by the policy.

Every provider/model switch is cold. The receiving route has no conversation, tool history, or provider prompt cache unless you include it in the handoff.

## Cost and privacy

Read the policy's `cost_controls` and `privacy_and_verification` sections rather than relying on memory.

- Treat every provider listed as hosted as remote; do not send secrets or unnecessary private material.
- Run at most the configured number of specialists/reviewers concurrently.

## Handoff contract

Load `references/routing-policy.md` for the required machine-readable handoff shape and behavioral verification checklist. Preserve exact commands, sources, evidence, files changed, unresolved questions, validation status, and rollback mechanism.

## Gateway safety

Routing configuration applies to new sessions. Validate statically and through isolated one-shot CLI runs; do not restart the active gateway from a gateway-owned session. If a detached recovery gateway is active, do not modify launchd or start another gateway. Treat service repair as a separate planned maintenance task.
