---
name: llm-harness-ops
description: Install, migrate, and verify repo-driven LLM harness homes such as ~/.agents, ~/.claude, ~/.codex, ~/.hermes, and ~/.config/opencode using a harness-first checkout.
category: autonomous-ai-agents
---

# LLM Harness Ops

Use this skill when the user wants to install, migrate, reinstall, or verify a repository-managed harness layout that fans out into tool-specific homes like `~/.agents`, `~/.claude`, `~/.codex`, `~/.hermes`, or `~/.config/opencode`.

This skill is for *home-layout operations*, not source-code changes inside the harness repo.

## Repository Maintenance

Run maintenance from `~/.llm-harness`; do not create, copy, or link an
`update-skills.sh` helper into another harness home.

```sh
cd ~/.llm-harness
./harness.py update-repo        # full repository maintenance
./harness.py update-skills      # refresh configured skill submodules only
```

Use `update-repo` when the checkout itself should be pulled and maintained;
use `update-skills` when only configured submodule sources need updating.

## When to use

- Installing or reinstalling the harness-first `llm-harness` checkout
- Reinstalling symlink-managed harness files after a cleanup
- Verifying what `./harness.py install`/`uninstall` changed in the user home
- Checking whether target paths are managed symlinks or unrelated user-owned files

## Core workflow

1. **Inspect the install model before acting.**
   - Read the repo `README.md` and run `./harness.py --help` first.
   - Confirm canonical checkout path, target home mappings, and whether install is per-skill symlinks or whole-directory links.
   - Look for repo-local `AGENTS.md` instructions that constrain structure changes.

2. **Run `./harness.py uninstall` from `~/.llm-harness` to clear managed symlinks.**
   - Expect it to remove only *managed matching symlinks* and to skip unrelated files/paths.
   - Capture skip messages exactly; they often explain why some target path remained untouched.

3. **Run `./harness.py install` from `~/.llm-harness`.**
   - Creates or refreshes symlinks in target harness homes.

4. **Verify with realpath-level checks, not just installer stdout.**
   - Check the clone destination exists.
   - Check important installed targets resolve to the expected source paths, especially:
     - `~/.agents`
     - `~/.claude/CLAUDE.md`
     - `~/.claude/skills/*` when relevant
     - `~/.codex/skills/*` when relevant
     - `~/.hermes/skills/*` when relevant
   - Prefer verifying representative links and the harness root mapping rather than assuming success from the install log alone.

## What to report back

Keep the report concise and operational:

- what uninstall did
- what it skipped
- whether install completed
- which key symlinks were verified
- any skipped pre-existing paths

If uninstall skipped an existing path because it pointed elsewhere, mention that explicitly so the user knows it was preserved rather than forgotten.

## Verification checklist

- `./harness.py uninstall` exited `0`
- `./harness.py install` exited `0`
- at least one key target under each affected harness resolves to the source tree
- any skipped pre-existing paths are called out in the summary

## Pitfalls

- Do not mirror Hermes package-bundled skills into `~/.llm-harness/harness/hermes/skills`. That tree is only for custom Hermes-only skills; built-in package skills belong in the Hermes installed runtime/package tree: `~/.hermes/skills`. Before copying any Hermes skill into `~/.llm-harness`, compare its category/name against the currently installed Hermes skill tree.
- Do not assume `./harness.py uninstall` removes arbitrary target files; it only removes symlinks that resolve to the expected managed source.
- Do not delete `~/.claude`, `~/.codex`, or similar homes just because a migration touched them; preserve unrelated user files unless explicitly told otherwise.
- Do not rely only on README claims; installer behavior can differ in detail from prose.
- Do not stop after cloning. The job is not done until install has been executed and verified.
- If a repo documents a canonical checkout path but the user asked for a different destination, follow the user’s requested destination and verify the installed symlinks against the actual clone path used.

## References

- `references/agents-to-llm-harness-migration.md` — current migration pattern for the harness-first `llm-harness` repo, including uninstall semantics and verification targets.
