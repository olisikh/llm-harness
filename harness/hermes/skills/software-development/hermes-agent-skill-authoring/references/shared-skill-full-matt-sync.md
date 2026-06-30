# Full Matt skill sync in `~/llm-harness`

Use this when Oleksii wants `~/llm-harness` to stop excluding any Matt Pocock skills and to mirror the full `mattpocock-skills/skills` tree into the intended harness trees.

## Trigger

The user says some Matt skill should be symlinked but is missing, or says to stop ignoring/excluding Matt skills and sync the whole folder.

## Diagnosis pattern

1. Check `~/llm-harness/skills-config.yaml` for a `mattpocock-skills` entry with `exclude` values or overrides.
2. Check `~/llm-harness/AGENTS.md` for local-shadow rules that intentionally keep first-party local copies.
3. Compare repo policy to the actual tree before blaming `scripts/update-skills.sh`.

If `exclude` or local-shadow policy still mention Matt overlaps, a missing symlink is usually a config/policy mismatch, not a broken sync script.

## Update pattern

When the user wants full Matt sync:

1. Remove any Matt-specific exclusion block from the `mattpocock-skills` entry in `skills-config.yaml`.
2. Update `AGENTS.md` so repo policy matches the new intent: sync the full Matt tree and remove local overlapping copies instead of excluding upstream skills.
3. Rerun `bash -n scripts/update-skills.sh`.
4. Rerun `./scripts/update-skills.sh mattpocock-skills`.
5. Verify with `git status --short` and inspect the relevant symlink paths.

## Practical note

If `~/llm-harness` has local unstaged edits and the user asked to pull first, prefer `git pull --rebase --autostash` after a plain pull fails because of dirty worktree state.

## Expected verification outcomes

- `skills-config.yaml` no longer excludes the desired Matt skills.
- `AGENTS.md` no longer instructs the agent to preserve conflicting local Matt shadow copies.
- resulting `harness/.../skills/...` symlinks are owned by `scripts/update-skills.sh`, not by ad hoc manual edits.
- If there are no actual remaining overlapping local skills, the sync may report `No submodule pointer or symlink changes detected`; that is still a successful policy cleanup.
