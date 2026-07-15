---
name: model-routing
description: Route non-trivial, parallelizable, coding, research, ambiguous, high-risk, or repeatedly failing work across direct tools, execute_code, Hermes delegate_task workers, explicit OpenCode specialists, and final reviewer escalation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [model-routing, delegation, orchestration, cost-control, opencode, ollama]
    related_skills: [opencode, subagent-driven-development, hermes-agent-devops]
---

# Model Routing

Apply a **routing ladder**: choose the cheapest route that can satisfy the acceptance criteria, validate its output, and climb only when evidence requires stronger judgment.

## Routing loop

1. **Frame the task.** State the objective, acceptance criteria, scope, privacy constraints, required evidence, and rollback mechanism for high-impact actions.
2. **Choose the lowest capable route.** Load `references/routing-policy.md` when exact provider/model selection matters, then prefer direct tools, deterministic execution, cheap workers, specialists, and finally a reviewer.
3. **Pass a complete brief.** Include every fact a fresh process needs; delegated agents do not inherit the parent conversation.
4. **Execute within a cap.** Limit concurrency, iterations, retries, and context.
5. **Validate independently.** Treat summaries and self-reported success as claims until tool output, files, tests, or sources verify them.
6. **Escalate on evidence.** Preserve the compact handoff and state exactly why the previous route failed.

Completion criterion: every result is either validated against the acceptance criteria or explicitly marked partial/failed with an escalation decision.

## Route selection

| Route | Use when | Default mechanism |
|---|---|---|
| Direct | One clear answer or a few dependent tool calls | Main agent with normal tools |
| Deterministic | Mechanical processing, tests, builds, lint, schema checks, data reduction | `execute_code`, `terminal`, or file tools |
| Cheap worker | Independent bounded extraction, classification, summary, discovery, comparison, first-pass research | `delegate_task` pinned globally to `openai-codex/gpt-5.6-luna` |
| Specialist | Coding or research needs sustained judgment, broad context, or model choice | Main `openai-codex/gpt-5.6-terra` or explicit `opencode run --model ...` |
| Reviewer | Architecture, security, conflicting evidence, repeated failure, failed validation, or high-impact action | Isolated `openai-codex/gpt-5.6-sol` |

Do not delegate a task that direct tools can finish more cheaply and reliably. Do not use a model to run a deterministic check.

Apply this decision tree:

```text
One clear answer or a few dependent tool calls?
  -> main agent uses direct tools
Mechanical transformation, test, build, lint, or schema check?
  -> execute_code or deterministic tools
Two or more independent bounded extraction/research tasks?
  -> Luna delegate_task batch
Coding/research judgment or per-task model choice?
  -> terra synthesis or explicit OpenCode specialist
Architecture, security, conflict, repeated failure, or high impact?
  -> isolated sol reviewer
```

## Native Hermes delegation

Use `delegate_task` only for bounded work with explicit output and acceptance criteria. Luna is limited to the cheap-worker suitability list in `references/routing-policy.md`; route architecture, security, destructive/high-impact work, tool-heavy implementation, and final acceptance to a specialist or reviewer.

- Batch only independent tasks.
- Cap routine batches at two children.
- Keep orchestration flat: the main agent orchestrates; children remain leaves.
- Restrict each child to the smallest necessary toolsets.
- Pass absolute paths, source URLs, exact questions, constraints, output format, and validation expectations.
- Require findings, evidence, files changed, unresolved questions, and validation status in the result.
- Verify external side effects and shared-file writes in the parent session.

Native `delegate_task` does not expose per-call model/provider selection. `delegation.provider`, `delegation.model`, and `delegation.reasoning_effort` apply globally to children, which inherit the parent fallback chain. Use an explicit OpenCode or one-shot Hermes process when a task needs another model.

Bounded delegation example:

```python
delegate_task(tasks=[
    {
        "goal": "Extract every configured provider/model pair",
        "context": "Read /absolute/path/config.yaml. Return pairs plus line evidence. Do not edit files.",
        "role": "leaf",
    },
    {
        "goal": "Map repository test and validation commands",
        "context": "Inspect /absolute/path/repo docs and manifests. Return exact commands plus source paths. Do not edit files.",
        "role": "leaf",
    },
])
```

Deterministic execution example:

```python
execute_code(code="""
import json
from pathlib import Path
payload = json.loads(Path('/absolute/path/result.json').read_text())
required = {'findings', 'validation', 'unresolved'}
missing = sorted(required - payload.keys())
print({'valid': not missing, 'missing': missing})
""")
```

One-shot Hermes example:

```bash
~/.local/bin/hermes \
  --provider openai-codex \
  -m gpt-5.6-sol \
  -z '<compact reviewer handoff>'
```

## Specialist selection

Use the main terra agent for synthesis that benefits from the live conversation and tools. Use OpenCode for isolated coding/research work requiring per-task model choice.

- `opencode-go/kimi-k2.7-code`: coding, debugging, implementation, code-centric agent work.
- `opencode-go/qwen3.7-max`: difficult reasoning, research synthesis, design comparison.
- `opencode-go/deepseek-v4-pro`: alternative deep reasoning or independent specialist review.
- `opencode-go/deepseek-v4-flash`: fast, lower-cost bounded hosted fallback.

Example:

```bash
opencode run \
  --model opencode-go/kimi-k2.7-code \
  --variant high \
  '<compact task brief with acceptance criteria and validation commands>'
```

Keep specialist processes scoped to one repository/worktree. For long bounded runs, use `terminal(background=true, notify_on_complete=true)`; use `process` for interactive sessions.

## Reviewer escalation

Invoke sol only for:

- architecture or cross-system design;
- security-sensitive work;
- destructive, public, financial, or otherwise high-impact actions;
- materially conflicting specialist conclusions;
- repeated malformed or uncertain results;
- failed tests, compilation, lint, schema validation, or rollout verification after attempted repair;
- a final decision whose cost of error materially exceeds reviewer cost.

Give the reviewer the compact handoff, not the full conversation. Ask it to check framing, evidence, validation, risk, and rollback. Keep `xhigh` for exceptional risk rather than routine review.

## Failure and provider switching

### Transport failure

Respect the provider retry cap in `agent.api_max_retries` (currently three); do not add an unbounded agent-level retry loop. Then use the configured fallback for rate limits, quota exhaustion, timeouts, authentication/provider errors, 5xx overload, connection failure, or unavailable models. This is also the main-orchestrator failure path. Stop after the configured fallback fails and escalate rather than bouncing providers.

Every cross-provider switch starts cold: the new process has no provider prompt cache and an explicit OpenCode/one-shot Hermes process does not inherit the live conversation or tool history. Build a compact handoff before switching. Prefer same-provider repair when it is likely to work, but never preserve cache at the expense of correctness.

### Malformed structured output

1. Validate locally.
2. Retry the same model once with the exact schema and validation error.
3. If the schema itself is ambiguous or too complex, simplify it, split the work into smaller deterministic chunks, or replace the LLM step with a parser.
4. Switch route/model if the repaired output is still invalid.
5. Escalate cheap worker -> specialist -> reviewer -> human when two distinct models fail at one rung.

### Failed tool calls

Switch models only when model behavior caused the failure: invented tool, malformed arguments after correction, repeated failure to invoke a required tool, or a success claim without execution. Fix the task/environment instead when the tool reports a deterministic file, permission, credential, service, compiler, test, or network failure.

### Poor or uncertain result

Give one focused repair request. Escalate if the result remains unsupported, contradictory, vague, or unvalidated. Prefer one specialist over repeated cheap-worker retries.

## Cost controls

- Use the smallest capable model.
- Do not delegate simple work.
- Use at most two cheap workers concurrently.
- Run one specialist or reviewer at a time.
- Keep native delegation depth at one.
- Cap cheap workers at a maximum of 15 iterations; raise the cap only for a justified specialist run.
- Allow one same-model repair before switching.
- Set an explicit wall-clock budget for every specialist/reviewer process; default to 600 seconds and raise it before launch only with a stated reason.
- Preserve a stable provider/model within each role to retain prompt caching.
- Keep sol out of default, routine, and cheap-worker paths.
- Keep handoffs compact; reference large outputs by file path.

## Ollama policy

Treat all hosted routes (`openai-codex`, `opencode-go`, `opencode-zen`, and Ollama Cloud) as remote providers: exclude secrets and minimize proprietary data unless the task explicitly permits sending it. Use Ollama Cloud for bounded hosted fallback, summaries, extraction, classification, code explanation, and tightly tested implementation. Validate JSON and code independently.

Use local Ollama only after a model is installed and benchmarked. Restrict it to private/offline summaries, simple schemas, repository triage from supplied excerpts, and isolated code transformations with deterministic acceptance criteria. Local output must not be the sole basis for architecture, security, high-impact action, or tool-dependent workflows.

When no local model is installed, leave the local route disabled rather than silently substituting another provider.

## Handoffs and detailed model map

Load `references/routing-policy.md` when constructing a handoff, checking the exact model/fallback map, reviewing privacy tradeoffs, or running the behavioral verification scenarios.