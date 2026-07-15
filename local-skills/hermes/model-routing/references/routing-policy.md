# Hermes Routing Procedure Reference

The declarative policy lives in `~/.hermes/model-routing.yaml`. This file describes only the execution contract used with that policy; it does not duplicate role models or provider fallback order.

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

## Editing the routing policy

1. Edit `~/.hermes/model-routing.yaml`.
2. Run the deterministic checker:

   ```bash
   ~/.hermes/hermes-agent/venv/bin/python \
     ~/.hermes/scripts/sync-model-routing-config.py --check
   ```

3. If it reports drift, preview the exact owned projection:

   ```bash
   ~/.hermes/hermes-agent/venv/bin/python \
     ~/.hermes/scripts/sync-model-routing-config.py --print
   ```

4. After reviewing it, project only routing-owned fields:

   ```bash
   ~/.hermes/hermes-agent/venv/bin/python \
     ~/.hermes/scripts/sync-model-routing-config.py --apply
   ```

5. Re-run `--check` and `hermes config check`.
6. Test through isolated one-shot commands, not an active gateway restart.
7. Commit the policy, projection, and validation evidence together in the Hermes-state repository.

## Behavioral verification checklist

- The checker reports `model-routing policy and config.yaml are synchronized`.
- `hermes fallback list` matches `runtime_projection.fallback_providers`.
- The installed `model-routing` skill resolves to the canonical `local-skills/hermes` source and is visible in `~/.hermes/skills`, not `~/.agents/skills`.
- A direct synthetic request does not delegate.
- A two-part bounded request produces two native children and parent validation.
- An explicit specialist command uses the role selected from the YAML policy.
- Deterministic JSON/schema/test work uses tools, not an LLM claim.
- Reviewer use matches `roles.final_reviewer.invoke_only_for`.
- No local model is selected when `privacy_and_verification.local_ollama.status` is `disabled`.
- Repositories are clean and synchronized after documentation updates.

## Future local model enablement

Do not change `local_ollama.status` from `disabled` until all declared prerequisites are complete: explicit approval, installation, and a benchmark appropriate to the actual hardware. Add the selected model and the benchmark result to the policy in the same commit.
