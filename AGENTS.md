# AGENTS.md

These rules bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

Do not assume. Do not hide confusion. Surface tradeoffs.

- State assumptions explicitly.
- If multiple interpretations exist, ask or present options instead of choosing silently.
- Say when simpler approach exists.
- Stop and clarify when request or constraints are unclear.

## 2. Simplicity First

Write minimum code that solves requested problem.

- Do not add features that were not requested.
- Do not add abstractions for one-off code.
- Do not add configurability without concrete need.
- If solution feels overbuilt, simplify it.

## 3. Surgical Changes

Touch only what task requires.

- Do not refactor unrelated code.
- Do not reformat adjacent code without task-driven reason.
- Match local style.
- Mention unrelated issues you notice, but do not fix unless asked.

Every changed line should trace back to request.

## 4. Goal-Driven Execution

Define success in a way that can be checked.

- Turn vague requests into verifiable outcomes.
- For bug fixes, reproduce issue and confirm fix.
- For behavior changes, verify changed behavior directly.
- For multi-step work, keep short plan and verify each step.

## 5. Search Before You Say You Don't Know

If tempted to say you cannot verify something from memory, search first.

Mandatory search triggers:
- specific products, models, versions, events, dates
- anything likely newer than training data
- factual claims not verifiable from repo files

Only state you cannot verify after searching returns no useful result.

## 6. Repository Model

- Canonical checkout path is `~/.llm-harness`.
- Repo is harness-first.
- `harness/<name>/` mirrors target harness home.
- `harness/agents/` is portable/default harness and mirrors `~/.agents/`.
- `skills/` under each harness contains direct child skill directories intended for that harness.

Current conventions:
- `harness/agents` -> `~/.agents`
- `harness/claude` -> `~/.claude`
- `harness/codex` -> `~/.codex`
- `harness/opencode` -> `~/.config/opencode` via `harness-paths.yaml`

## 7. Shared Skill Sync Rules

- Shared upstream submodules currently are:
  - `obsidian-skills`
  - `mattpocock-skills`
- `scripts/update-skills.sh` is source of truth for shared skill sync.
- Shared submodule skills default to portable `harness/agents/skills`.
- Harness-specific exceptions use explicit overrides in `skills-config.yaml`.
- Local first-party skills may intentionally shadow upstream names. Do not replace real local directories with symlinks by accident.

## 8. Installer Rules

- `install.sh` auto-discovers harness directories.
- `skills/` install uses per-skill symlinks.
- Non-skill top-level harness entries install as 1:1 symlinks into harness home.
- Existing non-matching target paths are warnings, not overwrite candidates.
- Stale managed symlinks should be removed.
- Unrelated user files must be left alone.

## 9. Verify Structure Changes

After changing shared-sync or install behavior, verify with:

1. `bash -n install.sh`
2. `bash -n uninstall.sh`
3. `bash -n scripts/update-skills.sh`
4. `./scripts/update-skills.sh [submodule...]`
5. `git status --short`
