---
name: llm-harness-ops
description: Install, migrate, and verify repo-driven LLM harness homes such as ~/.agents, ~/.claude, ~/.codex, ~/.hermes, and ~/.config/opencode using a harness-first checkout.
category: autonomous-ai-agents
---

# LLM Harness Ops

Use this skill when the user wants to install, migrate, reinstall, or verify a repository-managed harness layout that fans out into tool-specific homes like `~/.agents`, `~/.claude`, `~/.codex`, `~/.hermes`, or `~/.config/opencode`.

This skill is for *home-layout operations*, not source-code changes inside the harness repo.

## When to use

- Moving from a standalone `~/.agents` repo to a harness-first repo such as `llm-harness`
- Reinstalling symlink-managed harness files after a cleanup or migration
- Verifying what an installer/uninstaller actually changed in the user home
- Checking whether target paths are managed symlinks or unrelated user-owned files
- Cleaning up legacy skill-path indirection such as `~/.skills`

## Core workflow

1. **Inspect the install model before acting.**
   - Read the repo `README.md`, `install.sh`, and `uninstall.sh` first.
   - Confirm canonical checkout path, target home mappings, and whether install is per-skill symlinks or whole-directory links.
   - Look for repo-local `AGENTS.md` instructions that constrain structure changes.

2. **Run the old uninstall from the old canonical repo/root before deleting it.**
   - Do this when replacing an existing managed checkout such as `~/.agents`.
   - Expect uninstall scripts to remove only *managed matching symlinks* and to skip unrelated files/paths.
   - Capture skip messages exactly; they often explain why some target path remained untouched.

3. **Remove only the retired source tree the user asked to replace.**
   - After uninstall completes, remove the old checkout path if explicitly requested.
   - Do not manually delete target harness-home contents unless the user asked for broader cleanup.

4. **Clone the new repo into the requested location and run its installer from repo root.**
   - Use the exact remote and destination the user named.
   - Run `install.sh` from the cloned repo root so relative paths resolve correctly.

5. **Verify with realpath-level checks, not just installer stdout.**
   - Check the clone destination exists.
   - Check important installed targets resolve to the expected source paths, especially:
     - `~/.agents`
     - `~/.claude/CLAUDE.md`
     - `~/.claude/skills/*` when relevant
     - `~/.codex/skills/*` when relevant
     - `~/.hermes/skills/*` when relevant
   - Also inspect whether `~/.claude/skills` is a real directory or a legacy symlink chain through `~/.skills`.
   - Prefer verifying representative links and the harness root mapping rather than assuming success from the install log alone.

6. **Clean up legacy `~/.skills` indirection if present and not wanted.**
   - A common pre-harness state is:
     - `~/.skills -> ~/.agents/skills`
     - `~/.claude/skills -> ~/.skills`
   - If the user wants `~/.skills` gone, remove `~/.claude/skills` first when it points to `~/.skills`, then remove `~/.skills`, rerun `install.sh`, and verify `~/.claude/skills` becomes a normal directory managed directly by the harness installer.
   - After this cleanup, check whether Claude-only skills leaked into `~/.agents/skills` during the legacy setup and remove those stale entries if they resolve into `harness/claude/skills`.

## What to report back

Keep the report concise and operational:

- what uninstall did
- what it skipped
- what path was removed
- where the new repo was cloned
- whether install completed
- which key symlinks were verified
- whether any legacy `~/.skills` path was removed
- whether stale Claude-only entries had to be pruned from `~/.agents/skills`

If uninstall skipped an existing path because it pointed elsewhere, mention that explicitly so the user knows it was preserved rather than forgotten.

## Verification checklist

- `uninstall.sh` exited `0`
- requested old checkout path is gone or replaced as expected
- clone destination exists and is a repo
- `install.sh` exited `0`
- at least one key target under each affected harness resolves to the new source tree
- any skipped pre-existing paths are called out in the summary
- if `~/.skills` existed before, it is either intentionally retained or confirmed absent afterward
- if `~/.claude/skills` previously pointed through `~/.skills`, it ends as a normal directory with the expected harness-specific entries

## Pitfalls

- Do not mirror Hermes package-bundled skills into `~/llm-harness/harness/hermes/skills`. That tree is only for custom Hermes-only skills; built-in package skills belong in the Hermes install/source tree (for Oleksii, typically `~/hermes-agent/skills`). Before copying any Hermes skill into `llm-harness`, compare its category/name against the built-in Hermes skill tree.
- Do not assume `uninstall.sh` removes arbitrary target files; many harness uninstallers only remove symlinks that resolve to the expected managed source.
- Do not delete `~/.claude`, `~/.codex`, or similar homes just because a migration touched them; preserve unrelated user files unless explicitly told otherwise.
- Do not rely only on README claims; installer behavior can differ in detail from prose.
- Do not stop after cloning. The job is not done until install has been executed and verified.
- If a repo documents a canonical checkout path but the user asked for a different destination, follow the user’s requested destination and verify the installed symlinks against the actual clone path used.
- Legacy `~/.skills` indirection can make a successful install look correct while silently mixing Claude-only skills into portable `~/.agents/skills`; inspect and clean that chain when separation matters.
- Current harness installers may not remove Claude-only stale symlinks that were previously created through the legacy `~/.skills` path; after cleanup, explicitly prune any `~/.agents/skills/*` entries that resolve into `harness/claude/skills`.

## References

- `references/agents-to-llm-harness-migration.md` — concrete migration pattern from a standalone `~/.agents` checkout to a harness-first `llm-harness` repo, including uninstall skip semantics, legacy `~/.skills` cleanup, and verification targets.
