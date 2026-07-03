---
name: harness-managed-skills
description: Use when creating, migrating, or maintaining centrally managed skills in Oleksii's llm-harness repo and installing them into runtime homes like ~/.agents, ~/.claude, and ~/.hermes.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, llm-harness, hermes, claude, agents, symlinks, install]
    related_skills: [llm-harness-ops, hermes-agent-skill-authoring]
---

# Harness-Managed Skills

## Overview

Use this skill for work where the user wants skills maintained centrally in `~/.llm-harness` while runtime harness homes consume installed symlinks.

On Oleksii's setup, physical source files in `~/.llm-harness` are the source of truth. Installed runtime trees such as `~/.agents/skills` and `~/.hermes/skills` are deployment targets, not preferred edit locations.

See `references/hermes-central-skill-install.md` for the concrete Hermes-specific layout and verification recipe.

## When to Use

- Creating a new durable skill for Oleksii
- Moving a skill out of an installed runtime tree into the central repo
- Updating instructions that still say skills should be authored directly in `~/.agents/skills` or `~/.hermes/skills`
- Verifying that installed runtime skill paths are symlinks into `~/.llm-harness`
- Adding Hermes-specific skills that need category folders preserved under `~/.hermes/skills`

Do not use this for one-off temporary personal notes that should remain local-only.

## Core Rules

1. Treat `~/.llm-harness` as canonical.
2. Put first-party source skills under `~/.llm-harness/local-skills/skills/...`.
   - default target harness: `agents`
   - for `claude`, `codex`, `hermes`, or `opencode`, keep the source under `local-skills/skills/...` and route it with `config.yaml` overrides
   - use `harness/<name>/` only for non-skill harness-specific files such as `CLAUDE.md`
3. Prefer editing repo source, not installed runtime copies.
4. After creating, moving, or editing skills, run `cd ~/.llm-harness && ./harness.py install` so harness homes refresh.
5. Verify symlink targets with realpath-level checks, not just installer stdout.

## Hermes-Specific Layout Rule

Hermes skills may need nested category paths in the installed runtime tree, for example:

- source: `~/.llm-harness/local-skills/skills/autonomous-ai-agents/hermes-agent/...`
- install target: `~/.hermes/skills/autonomous-ai-agents/hermes-agent`

The installer must preserve nested category paths by linking every directory containing `SKILL.md`, not only direct children of `skills/`.

## Workflow

1. Identify which harness should receive the installed skill.
2. Create or update the physical source under `~/.llm-harness/local-skills/skills/...`.
3. If the skill belongs somewhere other than the default `agents` harness, add or update the `local-skills` override in `~/.llm-harness/config.yaml`.
4. If instructions or references still point to old canonical paths, patch them in the same session.
5. Re-run `cd ~/.llm-harness && ./harness.py install`.
6. Verify installed runtime paths resolve back into `~/.llm-harness`.
7. Commit in `~/.llm-harness` once verified.
8. If the user explicitly wants the repo publication/sync step, push as a separate repo action rather than treating it as part of skill authoring itself.
   - Use a repo workflow such as `git-commit` for the commit step and a separate push/sync action only when requested.

## Common Pitfalls

1. **Editing installed runtime copies directly.** This creates drift and breaks the central-repo model.
2. **Assuming skill trees are flat.** Hermes may require nested category paths like `autonomous-ai-agents/<skill>`.
3. **Forgetting to run `./harness.py install` after repo edits.** The repo can be correct while runtime homes are stale.
4. **Keeping two editable copies.** Runtime paths should be symlinked compatibility/install views, not a second source of truth.
5. **Updating the sync cron job without refreshing install links.** The automated update path should both sync repo state and reinstall links.
6. **Fixing only the repo script when Hermes cron still fails.** Hermes `cronjob` script entries are resolved from `~/.hermes/scripts/`; if the durable implementation moved into `~/.llm-harness/scripts/...`, keep a wrapper in `~/.hermes/scripts/` that `exec`s the repo script and manually run the job once after changing it.

## Verification Checklist

- [ ] Skill source lives under `~/.llm-harness/local-skills/skills/...`
- [ ] Any non-default target harness routing is declared in `~/.llm-harness/config.yaml`
- [ ] Installed runtime path exists where expected
- [ ] Installed runtime path is a symlink or managed install target resolving into `~/.llm-harness`
- [ ] `cd ~/.llm-harness && ./harness.py install` has been run after changes
- [ ] Any updated instructions now describe `~/.llm-harness` as canonical
- [ ] Changes are ready to commit in the `~/.llm-harness` repo
