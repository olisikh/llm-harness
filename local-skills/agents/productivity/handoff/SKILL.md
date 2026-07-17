---
name: handoff
description: Compact the current conversation into a durable redacted handoff document under ~/.agents/handoffs for another agent to resume. Use only when explicitly invoked as /handoff or when the user explicitly asks for a handoff.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

# Durable Handoff

Write a compact Markdown handoff so a fresh agent can continue the work.

## Output location

Resolve and create the configured handoff directory before writing:

```bash
python3 ~/.llm-harness/scripts/skill-path.py artifact handoffs --create
```

Read `~/.agents/config/skill-paths.json` if the resolver reports an error. Do not write handoffs into a repository, the skill source, or a temporary directory.

Name the file `YYYY-MM-DD-HHMMSS-<slug>.md`, using a short slug based on the next session's purpose. Report the absolute path after writing it.

## Content

Include:

- objective and current state;
- decisions already made and their rationale;
- exact files, commands, URLs, issues, and commits worth reopening;
- completed work, remaining work, risks, and the next concrete action;
- a **Suggested skills** section.

Reference existing specs, plans, ADRs, issues, commits, and diffs by path or URL instead of copying them. Redact API keys, passwords, tokens, personal identifiers, and sensitive user data.

Use the supplied argument only to focus the next session; it does not change the storage location.

## Functional evaluation

Before completing, verify the path and file exist:

```bash
HANDOFF_DIR="$(python3 ~/.llm-harness/scripts/skill-path.py artifact handoffs --create)"
test -d "$HANDOFF_DIR"
test -f "$HANDOFF_PATH"
```
