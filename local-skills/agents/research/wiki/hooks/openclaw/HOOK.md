---
name: wiki-session
description: "Capture redacted OpenClaw session context into the ~/.llm-wiki/hub/.sessions/ queue for later review and possible topic-wiki promotion."
metadata: {"openclaw":{"emoji":"📚","events":["command:new","command:reset"],"async":true}}
---

# Wiki Session Hook

At the end of an OpenClaw session, this hook writes a redacted digest to
`~/.llm-wiki/hub/.sessions/digests/` and appends a feedback-candidate event to
`~/.llm-wiki/hub/.sessions/feedback/` if the session contained corrections,
preferences, approvals, or important decisions.

The hook is intentionally conservative: it captures metadata and redacted
highlights, not full transcripts. Topic-wiki promotion remains explicit and
user-directed.

## Enable

```bash
openclaw hooks enable wiki-session
```

## Safety

- Only writes to `~/.llm-wiki/hub/.sessions/`
- Redacts API keys, tokens, and long opaque blobs before writing
- Hook failures are swallowed; set `WIKI_SESSION_HOOK_DEBUG=1` to log failures
