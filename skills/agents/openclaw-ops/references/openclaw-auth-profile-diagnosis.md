# OpenClaw Auth Profile Diagnosis: Stale API Key Profiles

## Problem

Provider `opencode-go/kimi-k2.6` returns `HTTP 401: Invalid API key` despite:
- A valid API key being set in `OPENCODE_API_KEY` env var (shell)
- The `opencode` (Zen) provider working fine with the same env var
- The key working from outside OpenClaw (e.g. Hermes direct connection)

## Root Cause

The `opencode-go:default` auth profile in `auth-profiles.json` had a **stale hardcoded API key** (`sk-ATFd...bU6q`) that was no longer valid. OpenClaw's auth resolution prioritizes stored profiles over env vars, so the stale key was used instead of the valid one from the environment.

## Env Var Map (Oleksii's Setup)

Three distinct API keys exist for OpenCode:

| Env Var | Set in | Used by Plugin | Value |
|---------|--------|---------------|-------|
| `OPENCODE_API_KEY` | Shell profile (`.zshrc`) | Both `opencode` and `opencode-go` (primary envVar) | `sk-m6uQY...` — valid |
| `OPENCODE_ZEN_API_KEY` | Service env file | Both (secondary envVar fallback) | `sk-***` — valid for Zen endpoint |
| `OPENCODE_GO_API_KEY` | Service env file | **Neither** — not in plugin's `envVars` list | `sk-***` — ignored by plugin |

The gateway process (LaunchAgent) gets its env from `~/.openclaw/service-env/ai.openclaw.gateway.env`:
```
export OPENCLAW_SERVICE_MANAGED_ENV_KEYS='OPENCODE_GO_API_KEY,OPENCODE_ZEN_API_KEY'
export OPENCODE_GO_API_KEY='***'
export OPENCODE_ZEN_API_KEY='***'
```

Note: `OPENCODE_API_KEY` is **not** in the service env file. The gateway resolves `opencode-go` auth via `OPENCODE_ZEN_API_KEY` (the fallback env var the plugin declares). However, `models.json` regenerates on restart with `apiKey: OPENCODE_API_KEY` (plugin's primary envVar), so if `OPENCODE_API_KEY` isn't in the service env, the SecretRef becomes dangling.

## Plugin envVar Declaration

From `extensions/opencode-go/index.ts` (line 32):
```typescript
envVars: ["OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY"],
```

`OPENCODE_GO_API_KEY` is NOT declared. Even though the service env sets it, the plugin never reads it. To use `OPENCODE_GO_API_KEY`, either:
- Add it to the plugin's `envVars` array (source change)
- Update the `models.json` SecretRef to reference it (config change)
- Copy its value into one of the declared env vars

## Shared Profile IDs

From `extensions/opencode-go/index.ts` (line 15):
```typescript
const OPENCODE_SHARED_PROFILE_IDS = ["opencode:default", "opencode-go:default"] as const;
```

Both `opencode` and `opencode-go` share the same profile IDs. Either profile can be used by both providers. The fix removed the stale `opencode-go:default` entry; the `opencode:default` entry never existed.

## Key Consolidation Pattern

When the user wants a single OpenClaw key shared between Zen and Go providers:

1. Both plugins declare `envVars: ["OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY"]`
2. `models.json` references `OPENCODE_API_KEY` (plugin's primary `envVar`) — regenerates on restart
3. Best practice: set **both** vars in the service env to the same shared key value
4. Remove `OPENCODE_GO_API_KEY` — neither plugin reads it
5. Update `OPENCLAW_SERVICE_MANAGED_ENV_KEYS` to `'OPENCODE_API_KEY,OPENCODE_ZEN_API_KEY'`
6. Remove any stale `opencode-go:default` or `opencode:default` auth profiles

The Hermes key stays separate in `~/.hermes/.env` as `OPENCODE_API_KEY` — the service env and shell env are independent.

## Diagnostic Commands Used

```bash
# Check effective auth source for each provider
openclaw models status

# Check stored auth profiles
openclaw models auth list
cat ~/.openclaw/agents/main/agent/auth-profiles.json

# Check gateway process env (actual runtime env)
ps -wwp $(pgrep -f "openclaw.*gateway" | head -1) -E | tr ' ' '\n' | grep -i 'OPENCODE\|ZEN'

# Check what the plugin declares as valid env vars
grep 'envVars:' ~/openclaw/extensions/opencode-go/index.ts
grep 'envVars:' ~/openclaw/extensions/opencode/index.ts

# Check models.json SecretRef for the provider
python3 -c "
import json
d = json.load(open('$HOME/.openclaw/agents/main/agent/models.json'))
p = d.get('providers', {}).get('opencode-go', {})
print('apiKey ref:', p.get('apiKey', 'N/A'))
print('baseUrl:', p.get('baseUrl', 'N/A'))
"

# Check gateway logs for auth errors (note: log path may differ)
# Running gateway writes to ~/Library/Logs/openclaw/gateway.log
grep -iE 'opencode-go.*auth|invalid api key|HTTP 401' ~/Library/Logs/openclaw/gateway.log 2>/dev/null | tail -20

# Verify auth-profiles.json after fix
openclaw models auth list

# Confirm which log file the gateway is actively writing to
lsof -p $(pgrep -f "openclaw.*gateway" | head -1) | grep '\.log'
```

## Error Timeline

| Date | Event | Error |
|------|-------|-------|
| May 5 | First billing failure | `401 Your workspace has reached its monthly spending limit of $20.` |
| May 13 | Stale key used | `HTTP 401: Invalid API key.` (key exhausted or revoked) |
| May 30 | Stale profile removed, gateway restarted | Profile gone, falls back to env var |

## Fix Applied

Removed the `opencode-go:default` entry from `~/.openclaw/agents/main/agent/auth-profiles.json`. After restart, `openclaw models status` showed:
```
- opencode-go effective=env:sk-m6uQY...cvizLMx4 | env=sk-m6uQY...cvizLMx4 | source=env: OPENCODE_API_KEY
```

The key change: `effective=` went from `profiles:...` to `env:...`.

## Log File Location

The running gateway writes to `~/Library/Logs/openclaw/gateway.log`, NOT `~/.openclaw/logs/gateway.log`. The latter is from an earlier run and may be stale. Confirmed via `lsof -p <gateway-pid> | grep '\.log'`.
