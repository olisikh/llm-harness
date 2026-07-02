---
name: fix-issue
description: Fix a GitHub issue by number. Use when the user says "fix issue #N", "work on issue N", or "resolve ticket N". Reads the issue, implements the fix, writes tests, and creates a commit.
disable-model-invocation: true
argument-hint: [issue-number]
allowed-tools: Bash(gh issue view *) Bash(gh issue list *)
---

## Issue details

!`gh issue view $ARGUMENTS --json title,body,labels,comments 2>/dev/null || echo "Could not fetch issue — make sure gh is authenticated and issue number is correct"`

## Instructions

1. Read the issue title, body, and comments above.
2. Understand what needs to change and why.
3. Find the relevant code (use Grep/Glob/Read as needed).
4. Implement the fix — minimal, focused on the issue.
5. Write or update tests that cover the fix.
6. Verify nothing is broken.
7. Use /git-commit to commit, referencing the issue number in the message (e.g. "Fix #$ARGUMENTS: ...").

If the issue number is missing or invalid, ask the user to provide it.
