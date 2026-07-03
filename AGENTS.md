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
- `harness/<name>/` mirrors target harness home for non-skill harness-specific files.
- `harness/agents/` is portable/default harness and mirrors `~/.agents/`.
- Skill sources live in configured upstream submodules and in `local-skills/`; `harness.py install` links each directory that contains `SKILL.md`, preserving nested category paths.

Current conventions:
- `harness/agents` -> `~/.agents`
- `harness/claude` -> `~/.claude`
- `harness/codex` -> `~/.codex`
- `harness/hermes` -> `~/.hermes` via `harness-paths.yaml` for custom Hermes-only skills
- `harness/opencode` -> `~/.config/opencode` via `harness-paths.yaml`

## 7. Skill Source Sync Rules

- Skill sources are declared in `config.yaml` under `sources:` with `type: submodule` or `type: local`.
- Shared upstream submodules currently are:
  - `obsidian-skills`
  - `mattpocock-skills`
  - `llm-wiki`
- `./harness.py update-skills` is source of truth for shared skill submodule pointer updates; it only touches sources with `type: submodule`.
- All configured skill sources install directly to target harness homes according to `config.yaml`.
- Harness-specific exceptions use explicit overrides in `config.yaml`.
- Later sources in `config.yaml` win on target-path collision.

## 8. Installer Rules

- `harness.py install` auto-discovers harness directories.
- Skill sources are read from `config.yaml` and linked with per-skill symlinks, preserving nested category paths.
- Non-skill top-level harness entries from `harness/<name>/` install as 1:1 symlinks into harness home.
- Existing non-matching target paths are warnings, not overwrite candidates.
- Stale managed symlinks should be removed.
- Unrelated user files must be left alone.

## 9. Verify Structure Changes

After changing shared-sync or install behavior, verify with:

1. `python3 -m py_compile harness.py lib/*.py`
2. `./harness.py update-skills [submodule...]`
3. `./harness.py install`
4. `./harness.py uninstall`
5. `git status --short`

## 10. Operational Guide

For step-by-step recipes on adding skills, registering shared sources, moving skills between harnesses, and troubleshooting, see [docs/llm-harness-ops.md](docs/llm-harness-ops.md). Treat that document as the canonical operational reference for this repo.
