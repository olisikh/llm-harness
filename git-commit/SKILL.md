---
name: git-commit
description: Stage and commit the current changes with a well-crafted commit message. Use when the user asks to commit, save changes, or create a commit. Analyzes the diff and writes a concise, meaningful message.
disable-model-invocation: true
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git diff *) Bash(git status *)
---

## Current state

!`git status --short`

## Staged and unstaged diff

!`git diff HEAD`

## Recent commits (for style reference)

!`git log --oneline -10`

## Instructions

1. Review the diff and recent commit style above.
2. Stage relevant changed files (prefer specific paths over `git add .`; never stage `.env` or secrets).
3. Write a commit message that:
   - Has a concise subject line (≤72 chars) in imperative mood
   - Focuses on WHY, not what (the diff shows what)
   - Matches the tone and style of recent commits
   - Ends with: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
4. Create the commit using a HEREDOC to preserve formatting.
5. Report the commit hash and subject on success.

If $ARGUMENTS is provided, treat it as guidance for the commit message or scope.
