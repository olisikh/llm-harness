# OpenClaw Telegram non-response: healthy gateway, bad lane auth, or Codex startup abort

This note captures a common failure mode seen on the source-installed OpenClaw setup:

- Gateway process is `running`
- health endpoint returns `ok`
- Telegram ingress/egress may still appear normal
- but user messages stop getting useful replies

## What to look for

Check recent logs for these phrases:

- `unauthorized conn`
- `token_mismatch`
- `provider auth state pre-warmed`
- `Codex agent harness failed; not falling back to embedded PI backend`
- `codex app-server startup aborted`
- `model_fallback_decision`
- `candidate_failed`

## Interpretation

- `unauthorized conn` / `token_mismatch` usually means the gateway/auth layer and the active lane disagree on credentials or session state.
- A healthy launch + health check does *not* prove the model lane is usable.
- `codex app-server startup aborted` can trigger a fallback to another model/provider, so the bot may briefly respond differently or not at all depending on fallback availability.

## Triage order

1. Verify the gateway process is alive.
2. Confirm the health endpoint is okay.
3. Inspect the log tail around the failed user turn.
4. Separate gateway health from lane/auth health.
5. If fallback was attempted, check whether the fallback provider itself was available.

## Useful log query

```bash
grep -iE 'unauthorized conn|token_mismatch|codex app-server startup aborted|model_fallback_decision|candidate_failed' \
  ~/.openclaw/logs/gateway.log ~/.openclaw/logs/gateway.err.log 2>/dev/null | tail -120
```

## Session note

In this session, the gateway restarted cleanly and health was `ok`, but logs still showed lane/auth-related failures around the unresponsive turn. The important lesson is to avoid treating a healthy gateway as proof that Telegram replies are functioning end-to-end.
