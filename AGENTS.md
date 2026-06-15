# AGENTS.md

These rules bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

Do not assume. Do not hide confusion. Surface tradeoffs.

- State assumptions explicitly.
- If multiple interpretations exist, ask or present options instead of choosing silently.
- Say when a simpler approach exists.
- Stop and clarify when the request or constraints are unclear.

## 2. Simplicity First

Write the minimum code that solves the requested problem.

- Do not add features that were not requested.
- Do not add abstractions for one-off code.
- Do not add configurability or flexibility without a concrete need.
- Do not add defensive code for scenarios that do not plausibly exist here.
- If the solution feels overbuilt, simplify it.

## 3. Surgical Changes

Touch only what is required for the task.

- Do not refactor unrelated code.
- Do not reformat or rewrite adjacent code without a task-driven reason.
- Match the local style of the code you are editing.
- Remove only the imports, variables, or helpers that your own change made unused.
- Mention unrelated issues you notice, but do not fix them unless asked.

Every changed line should trace back to the user's request.

## 4. Goal-Driven Execution

Define success in a way that can be checked.

- Turn vague requests into verifiable outcomes.
- For bug fixes, reproduce the issue and confirm the fix.
- For behavior changes, verify the changed behavior directly.
- For multi-step work, keep a short plan and verify each step.

## 5. Search Before You Say You Don't Know

If you feel tempted to say "I don't know," "my knowledge cutoff," or "I don't have data about that" — search the internet first.

Mandatory search triggers:
- User asks about specific products, models, versions, events, or dates
- You suspect information may be newer than your training data
- Any factual claim you cannot immediately verify from files in the repo

Only state you cannot verify something after searching returns no relevant results.

If you disagree with the user or suspect they are wrong — search before correcting them.

Example:

```text
1. Update the implementation -> verify: relevant tests or direct behavior check
2. Adjust integration points -> verify: changed flow still works
3. Clean up change-specific fallout -> verify: no introduced breakage
```

These guidelines are working if diffs stay small, changes are directly justified, and clarification happens before implementation rather than after mistakes.

## 6. Repository Operating Model

- This repo is canonical `~/.agents` checkout.
- `skills/` is mixed tree:
  - real directories for first-party/local skills stored in this repo
  - tracked symlinks into git submodules for shared upstream skills
- Shared upstream submodules currently are:
  - `obsidian-skills`
  - `mattpocock-skills`

## 7. Shared Skill Layout Rules

- Shared-skill sync is generic, driven by `skills-sync.yaml`:
  - `skillsRoot`: folder inside submodule to scan
  - `skillsDest`: destination root inside this repo
  - `skillsExclude`: optional relative skill paths to skip
- Script symlinks every directory under `skillsRoot` that contains `SKILL.md`, preserving its relative path under `skillsDest`.
- Some local skills intentionally shadow upstream variants. Keep local directories unless task explicitly says to replace them:
  - `skills/handoff`
  - `skills/caveman`
- Do not replace real local skill directories with symlinks by accident.

## 8. Source Of Truth For Shared Skills

- `scripts/update-skills.sh` is source of truth for shared-skill sync.
- Script responsibilities:
  1. update requested submodule checkouts to upstream default-branch tips
  2. read `skills-sync.yaml` and mirror matching skill dirs into `skills/`
- Do not hand-edit managed symlinks if script should own them. Fix script or rerun script instead.
- Prefer editing canonical files inside submodule paths when changing shared upstream skills. Editing through symlink path changes same files, but hides ownership.

## 9. Verify Structure Changes

- After changing submodules, skill-link rules, install/uninstall behavior, or this file, verify with:
  1. `bash -n scripts/update-skills.sh`
  2. `./scripts/update-skills.sh [submodule...]`
  3. `git status --short`
  4. `git diff --cached --submodule=short`
