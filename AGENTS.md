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
