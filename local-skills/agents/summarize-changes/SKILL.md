---
name: summarize-changes
description: Summarizes uncommitted changes and flags anything risky. Use when the user asks what changed, wants a diff summary, wants to review their work before committing, or asks about recent edits.
allowed-tools: Bash(git diff *) Bash(git status *)
---

## Uncommitted changes

!`git diff HEAD`

## Modified files

!`git status --short`

## Instructions

Summarize the changes above in 2–4 bullet points. Then list any risks you notice such as:
- Missing error handling
- Hardcoded values or secrets
- Tests that need updating
- Breaking API changes
- Large refactors that could hide bugs

If the diff is empty, say there are nothing uncommitted.

Keep the summary short and actionable. $ARGUMENTS
