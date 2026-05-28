# OpenClaw Codex OAuth rotation / duplicate-profile notes

Session-derived troubleshooting notes for recurring `openai-codex` auth failures.

## Observed pattern

- User re-authenticated OpenAI Codex successfully, but OpenClaw soon failed again with:
  - `OAuth token refresh failed for openai-codex`
  - `refresh_token_reused`
  - `Your refresh token has already been used to generate a new access token. Please try signing in again.`
- Logs around the re-auth contained:
  - `[reload] config change requires gateway restart (auth.profiles.openai-codex:<email>)`
  - followed by `refresh_token_reused`
- Auth store had multiple Codex profiles, e.g. both:
  - `openai-codex:default`
  - `openai-codex:<email>`
- `lastGood` pointed at the email profile, but stale duplicate profiles remained.

## Likely causes

1. Gateway kept an old refresh token in memory because it was not restarted immediately after re-auth.
2. Multiple OpenClaw/Codex processes raced refresh-token rotation; one process used the new token, another reused the invalidated previous token.
3. Profile selection ambiguity: OpenClaw may sometimes use a stale `default` profile instead of the fresh email-specific profile.
4. If the same OAuth credential/token material is shared between agents or copied between auth stores, refresh-token rotation can break one side; prefer separate credentials/profiles when possible.

## Safe inspection commands

Do not print token values. Inspect only keys, timestamps, profile IDs, and redacted shapes:

```bash
python3 - <<'PY'
import json, pathlib, datetime
files = [
    pathlib.Path.home()/'.openclaw/agents/main/agent/auth-profiles.json',
    pathlib.Path.home()/'.openclaw/agents/main/agent/auth-state.json',
    pathlib.Path.home()/'.hermes/auth.json',
]
for p in files:
    if not p.exists():
        print(p, 'MISSING')
        continue
    st = p.stat()
    print('\n', p)
    print('mtime', datetime.datetime.fromtimestamp(st.st_mtime).isoformat(), 'size', st.st_size)
    data = json.loads(p.read_text())
    def red(o):
        if isinstance(o, dict):
            return {k: ('[REDACTED]' if any(s in k.lower() for s in ['token','secret','key']) else red(v)) for k,v in o.items()}
        if isinstance(o, list):
            return [red(x) for x in o]
        return o
    print(json.dumps(red(data), indent=2)[:5000])
PY

grep -iE 'openai-codex|refresh_token_reused|config change requires gateway restart|OAuth token refresh failed' \
  ~/.openclaw/logs/gateway.log ~/.openclaw/logs/gateway.err.log 2>/dev/null | tail -120
```

## Recommended repair sequence

1. Stop/kick duplicate OpenClaw processes and identify stale login commands:

```bash
ps aux | grep -E 'openclaw|models auth|codex' | grep -v grep
```

2. Re-auth using direct device-code method:

```bash
cd ~/openclaw
node ~/openclaw/dist/index.js models auth login \
  --provider openai-codex \
  --method device-code \
  --set-default
```

3. Immediately restart the gateway after successful authorization:

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

4. If failures recur, remove or disable stale duplicate `openai-codex:default` profile after backing up the auth files, leaving only the intended email-specific profile/default pointer. Avoid editing token values manually.

5. Verify with a small Codex request before switching Codex back to the global default model.

## Hermes interaction note

Hermes and OpenClaw normally use separate auth stores (`~/.hermes/auth.json` vs `~/.openclaw/agents/main/agent/auth-profiles.json`). A `refresh_token_reused` error is not proof that Hermes broke OpenClaw, but if the same OAuth token material was copied/shared, create a fresh separate credential/profile for one side.
