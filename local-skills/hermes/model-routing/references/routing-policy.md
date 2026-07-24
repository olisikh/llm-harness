# Hermes Routing Procedure Reference

The declarative policy lives in `~/.hermes/model-routing.yaml`. This file describes the execution contract used with that policy and the deterministic controller in `~/.llm-harness/local-skills/hermes/model-routing/`. It does not duplicate role models or provider fallback order.

## Compact handoff contract

```yaml
task:
  objective: "<one sentence>"
  acceptance_criteria:
    - "<verifiable condition>"

scope:
  working_directory: "<absolute path or null>"
  relevant_files: []
  constraints: []

findings:
  - claim: "<finding>"
    evidence: "<tool output, source URL, file:line, or command>"

tool_results:
  - command_or_tool: "<exact invocation>"
    result: "<concise result>"
    status: passed # passed | failed | partial

changes:
  files_modified: []
  external_side_effects: []

rollback:
  prepared: false
  mechanism: "<commit, backup, snapshot, dry-run, or not_required>"

validation:
  status: not_run # passed | failed | partial | not_run
  checks: []

unresolved: []

previous_route:
  provider: null
  model: null
  failure_reason: null
  context_continuity: unknown # warm | cold | unknown

next_action: "<specific request for receiving model>"
```

Represent empty list fields as `[]` and unknown scalar fields as `null`. Do not omit machine-readable keys. Store large raw outputs in files and reference their paths.

## Validating the routing policy

```bash
~/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/scripts/validate-model-routing.py
```

Expected output:

```text
routing_policy=valid
version=1
```

This command is read-only. It never writes `config.yaml`. If it reports an error, edit `~/.hermes/model-routing.yaml` and rerun.

## Running a routed task

1. Build a version-1 task manifest.
2. Validate it:

   ```bash
   ~/.hermes/hermes-agent/venv/bin/python \
     ~/.llm-harness/local-skills/hermes/model-routing/scripts/validate-controller-manifest.py \
     --kind task --input manifest.json
   ```

3. Execute through the appropriate controller script (for example `execute-read-only-route.py` or `execute-writer-candidate.py`), or build a batch and use `schedule-routed-tasks.py`.

4. Inspect the emitted JSON result artifact. Failure states include a stable `code` and `summary`.

## Behavioral verification checklist

- `validate-model-routing.py` reports `routing_policy=valid`.
- The installed `model-routing` skill resolves to the canonical `~/.llm-harness/local-skills/hermes/model-routing` source and is visible in `~/.hermes/skills/model-routing`.
- A direct synthetic request does not delegate.
- A two-part bounded request produces two cheap read-only children with parent validation.
- Writer candidates are created in isolated Git worktrees; overlapping scopes are rejected before launch.
- Deterministic JSON/schema/test work uses tools, not an LLM claim.
- Final review (`final_reviewer`) runs once per routed request that includes a writer.
- Native delegation guard blocks terminal/mutation attempts in audit mode (Task 11 may enable blocking).
- Repositories are clean and synchronized after documentation updates.

## Future local model enablement

Do not add a local Ollama route until all declared prerequisites are complete: explicit approval, installation, and a benchmark appropriate to the actual hardware. Add the selected model and the benchmark result to the policy in the same commit.
