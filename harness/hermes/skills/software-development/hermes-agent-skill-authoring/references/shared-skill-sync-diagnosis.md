# Shared skill sync diagnosis in `~/llm-harness`

Use this when a shared skill from a submodule seems missing, duplicated, or linked in the wrong place.

## Fast diagnosis

1. Pull `~/llm-harness` first.
   - If the repo has local edits, a plain `git pull --ff-only` may fail.
   - Prefer `git pull --rebase --autostash` so the inspection starts from current repo state without discarding local work.

2. Check the policy files before blaming the sync script.
   - Read `skills-config.yaml` for `sources`, `harness`, `exclude`, and `overrides`.
   - Read `AGENTS.md` for intentional local-shadow rules such as keeping a real local skill directory instead of replacing it with a symlink.

3. Interpret the shape correctly.
   - A skill absent from `harness/<dest>/skills/...` is not automatically a bug; it may be intentionally excluded.
   - A manually added symlink can coexist with an exclusion rule, creating a policy/content mismatch even when `scripts/update-skills.sh` itself is working as designed.

4. Verify the sync script separately.
   - Run `bash -n scripts/update-skills.sh`.
   - Run `./scripts/update-skills.sh <submodule>` in a clean clone or otherwise controlled state.
   - If the script obeys `exclude` and `overrides`, the problem is usually repo intent drift, not sync failure.

## Example pattern: upstream skill excluded but manually linked later

Observed pattern:
- `skills-config.yaml` excluded or rerouted a skill from `mattpocock-skills`
- `AGENTS.md` documented an intentional local shadow
- a later commit manually added a symlink anyway

Diagnosis:
- this is not evidence that the linker script is broken
- it is evidence that repo contents changed without updating sync policy

## Recommended fix shapes

Choose one explicit policy and make config match it:

1. **Managed upstream symlink**
   - remove the exclusion or override that blocked the desired path
   - let `scripts/update-skills.sh` own the link

2. **Intentional local shadow**
   - restore the local skill directory
   - keep the exclusion rule
   - remove the manually added symlink

Avoid leaving both the exclusion rule and a hand-created symlink in place; that makes future sync results look flaky when they are actually inconsistent-by-policy.
