# Routing Policy Reference

## Verified model map

Provider/model identifiers were confirmed against each configured provider's catalog on 2026-07-15. The `openai-codex` models are a separate Hermes provider, `opencode-go` and `opencode-zen` are separate OpenCode endpoints, and `ollama-cloud` has its own remote catalog. Recheck the relevant live catalog and credentials before replacing an identifier.

| Role | Primary | Secondary | Tertiary |
|---|---|---|---|
| Main orchestrator | `openai-codex/gpt-5.6-terra` high | `opencode-go/kimi-k2.7-code` | `opencode-go/deepseek-v4-flash` |
| Cheap native worker | `openai-codex/gpt-5.6-luna` low | global Hermes transport fallback | abort native delegation and launch explicit `opencode-go/deepseek-v4-flash` process |
| Coding specialist | `openai-codex/gpt-5.6-terra` medium/high | `opencode-go/kimi-k2.7-code` | `opencode-go/qwen3.7-max` |
| Research/reasoning specialist | `openai-codex/gpt-5.6-terra` medium/high | `opencode-go/qwen3.7-max` | `opencode-go/deepseek-v4-pro` |
| Final reviewer | `openai-codex/gpt-5.6-sol` high/xhigh | strongest appropriate OpenCode hosted reasoning model | `opencode-go/qwen3.7-max` or `opencode-go/deepseek-v4-pro` |

Preferred shared transport fallback order:

1. `opencode-go/kimi-k2.7-code`
2. `opencode-go/deepseek-v4-flash`
3. `ollama-cloud/kimi-k2.7-code`
4. `opencode-zen/mimo-v2.5-free`
5. `opencode-zen/deepseek-v4-flash-free`

The chain is global, so it is a resilience mechanism rather than a complete semantic role router. The parent applies role-specific semantic escalation.

## Compact handoff contract

```yaml
task:
  objective: "<one sentence>"
  acceptance_criteria:
    - "<verifiable condition>"

scope:
  working_directory: "<absolute path or none>"
  relevant_files:
    - "<path>"
  constraints:
    - "<constraint>"

findings:
  - claim: "<finding>"
    evidence: "<tool output, source URL, file:line, or command>"

tool_results:
  - command_or_tool: "<exact invocation>"
    result: "<concise result>"
    status: passed | failed | partial

changes:
  files_modified:
    - path: "<path>"
      summary: "<what changed>"
  external_side_effects: []

rollback:
  prepared: true | false | not_required
  mechanism: "<commit, backup, snapshot, dry-run, or none>"

validation:
  status: passed | failed | partial | not_run
  checks:
    - "<test/compile/lint/schema command and result>"

unresolved:
  - "<question, conflict, or risk>"

previous_route:
  provider: "<provider>"
  model: "<model>"
  failure_reason: "<rate limit, malformed output, uncertainty, etc.>"
  context_continuity: warm | cold | unknown

next_action: "<specific request for receiving model>"
```

Represent empty list fields as `[]` and unknown scalar fields as `null`; do not omit schema keys from machine-readable handoffs. Preserve exact commands and paths. Store large raw outputs in files and reference them.

## Cheap-worker suitability

Suitable:

- extract named fields from supplied text;
- classify items against explicit labels;
- summarize a bounded source;
- map files, modules, tests, or documentation links;
- compare a small set against explicit criteria;
- collect first-pass research sources and quotations;
- produce a compliance matrix without deciding policy.

Escalate instead:

- architecture or public API design;
- broad implementation or refactoring;
- security, credentials, permissions, or destructive operations;
- decisions requiring conflicting-source resolution;
- tasks without crisp acceptance criteria;
- tool-heavy work where malformed calls are costly;
- final acceptance of code or external side effects.

## Ollama Cloud versus local Ollama

| Factor | Ollama Cloud | Local Ollama |
|---|---|---|
| Tool use | Allow bounded workflows; verify every side effect | Avoid dependable multi-step tool requirements |
| JSON | Validate and allow one repair | Keep schemas simple and validate locally |
| Context | Larger model-dependent briefs are practical | Keep context narrow for local memory/KV limits |
| Latency | Network and provider dependent | Predictable but potentially slow on larger quantizations |
| Privacy | Data leaves the machine | Best for private/offline data |
| Verification | Mandatory for code and structured output | Mandatory; never sole high-impact authority |
| Availability | Models can be retired; recheck catalog | Stable after install but consumes local RAM/CPU |

Environment snapshot on 2026-07-15: Apple M2 Pro, 16 GB RAM, no local Ollama models installed. Probe live hardware and `ollama list` before making a future local-model decision; the local route remains disabled until a separate selection and benchmark is approved.

## OpenCode credential precedence pitfall

If `opencode-go` returns `Invalid API key` while a direct endpoint probe succeeds, run `opencode auth list`. A stale credential in `~/.local/share/opencode/auth.json` can override the valid `OPENCODE_API_KEY` environment credential. Remove only the stale provider entry with `opencode auth logout opencode-go`, then run a one-line smoke test before the real specialist task.

## Behavioral verification scenarios

### Direct path

Prompt a simple fact lookup or one-file inspection. Pass when the main agent uses the direct tool and does not call `delegate_task` or OpenCode.

### Cheap parallel path

Provide two independent bounded extraction tasks. Pass when the parent batches two native children, each receives complete context, and the parent validates both results.

### Specialist path

Run a one-shot OpenCode task with an explicit `opencode-go` model and machine-readable output. Pass when the process exits successfully, reports the intended model route, and the parent validates the output.

### Deterministic path

Request JSON/schema validation, tests, compilation, or lint. Pass when tools perform the check directly rather than an LLM worker claiming it passed.

### Reviewer path

Supply a synthetic high-impact decision with conflicting specialist findings. Pass when the parent constructs a compact evidence handoff and invokes sol only after the escalation condition exists.

### Failure path

Feed malformed structured output to local validation. Pass when the same route gets one repair attempt, then the task switches/escalates according to policy rather than looping.

## Verification checklist

- Main provider/model and reasoning match the target config.
- Native delegation provider/model, reasoning, concurrency, depth, and iterations match the target config.
- Global fallback order is visible through `hermes fallback list`.
- The installed skill resolves to the canonical llm-harness source.
- Direct, cheap-worker, specialist, deterministic, and reviewer scenarios produce the expected routes.
- Every delegated result has evidence and validation status.
- Sol is absent from default and routine paths.
- Local Ollama is absent while no local model exists.
- Modified repositories are clean and synchronized after documentation and commits.
