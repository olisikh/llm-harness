---
name: openclaw-ops
description: "Maintain, update, and troubleshoot a source-installed OpenClaw instance alongside Hermes."
version: 1.2.0
author: Hermes Agent
metadata:
  hermes:
    tags: [openclaw, gateway, maintenance, source-install, launchagent]
    homepage: https://github.com/openclaw/openclaw
    related_skills: [hermes-agent]
---

# OpenClaw Ops

Maintain, update, restart, and debug a **source-installed** OpenClaw instance living at `~/openclaw`. This skill covers the full lifecycle when OpenClaw is NOT installed via Nix/Homebrew but cloned from GitHub and run via a custom LaunchAgent.

## Triggers

- User asks to update OpenClaw
- OpenClaw reports wrong/old version after `git pull` or `git checkout`
- Gateway won't restart or claims it's on an old release
- `openclaw` or `openclaw-update` background processes are stale
- Need to rebuild after checkout, dependency changes, or UI updates
- User asks to migrate or look up OpenClaw Telegram routing/bindings for a Hermes profile or allowlist
- Agent reports `⚠️ Unknown model: opencode/<model-id>` — model exists in CLI but agent runtime can't find it

## Environment Assumptions

- Source repo: `~/openclaw`
- CLI wrapper: `~/.local/bin/openclaw` → `~/openclaw/openclaw.mjs`
- Gateway LaunchAgent plist: `~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- **Gateway log file**: `~/Library/Logs/openclaw/gateway.log` (NOT `~/.openclaw/logs/gateway.log` which may be stale from an earlier run). Use `lsof -p <gateway-pid> | grep '\.log'` to confirm the active log path if unsure.
- Shared skills repo: `~/.agents` with skill content under `~/.agents/skills/`; see `references/shared-skills-repo-migration.md` for the symlink-preserving move pattern.
- Shared skills repo on Oleksii's setup: `~/.agents` (with `~/.skills` kept as a compatibility symlink when needed).
- When authoring new skills, keep the canonical files under `~/.agents/skills` and reference that path in examples; only add `~/.hermes/skills` symlinks when a compatibility bridge is actually required.

## Invocation Note

On Oleksii's source-installed setup, non-interactive shells may not have `~/.local/bin` on `PATH`. For direct start commands, prefer the explicit wrapper path when you are not already sure `openclaw` resolves:

```bash
~/.local/bin/openclaw gateway start
```

After starting, verify the LaunchAgent actually came up:

```bash
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code'
```
- State dir: `~/.openclaw`
- Runtime: Node 22+ (`/nix/store/…-nodejs-slim-24.14.0/bin/node` is typical)
- Package manager: `pnpm` (NOT npm/yarn)

## Auth and Model Status Commands

OpenClaw on this setup does **not** have a top-level `openclaw auth` command. For auth checks, use the model commands instead:

```bash
openclaw models status
openclaw models auth list
```

These are the authoritative commands for checking provider auth health and token state. `openclaw models status` shows the auth overview, runtime usability, and token usage; `openclaw models auth list` shows the stored auth profiles.

When diagnosing "auth" issues, look for:

- `Providers w/ OAuth/tokens`
- `Runtime auth`
- `OAuth/token status`
- profile names like `openai-codex:default`

If a user suggests `openclaw auth status`, treat that as a synonym request for `openclaw models status` / `openclaw models auth list`, not as a real command.

## Update Workflow

### 1. Check current checkout

```bash
cd ~/openclaw
git log --oneline -1
git fetch origin --tags
git tag -l | tail -5
```

**Pitfall:** `main` and release tags diverge. The latest release may be on a `release/YYYY.M.DD` branch or a detached tag, NOT on `main`. Always check tags separately.

### 2. Checkout the desired version

```bash
cd ~/openclaw
git checkout vYYYY.M.DD   # exact release tag
```

### 3. Install dependencies

```bash
cd ~/openclaw && pnpm install
```

**Pitfall:** If post-install fails with `@homebridge/ciao` resolution errors, run `pnpm install` again before building.

### 4. Rebuild everything

```bash
cd ~/openclaw && pnpm build          # core + dist
cd ~/openclaw && pnpm ui:build       # control UI (required for full release)
```

**Critical:** `dist/` is pre-built and committed in the repo. After a `git checkout`, `dist/` can still contain files from the **previous** version. `pnpm build` regenerates `dist/` from the currently checked-out source.

Verify:
```bash
grep '"version"' ~/openclaw/dist/build-info.json
# should show the target version
```

### 5. Patch cached version in state files

OpenClaw caches its self-reported version in **two places** outside `dist/`:

**A. LaunchAgent plist**
```bash
plutil -p ~/Library/LaunchAgents/ai.openclaw.gateway.plist | grep -i version
```
If it shows the old version, patch it:
```bash
sed -i '' 's/OLD_VERSION/NEW_VERSION/g' ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

**B. `~/.openclaw/openclaw.json`**
```bash
grep -n "lastTouchedVersion\|lastRunVersion" ~/.openclaw/openclaw.json
```
Patch both fields to the new version. They normally live under `meta.lastTouchedVersion` and `wizard.lastRunVersion`, not at the top level. If left stale, OpenClaw will still report the old version even though `dist/` is current.

**C. LaunchAgent service env file**
```bash
grep -n "OPENCLAW_SERVICE_VERSION" ~/.openclaw/service-env/ai.openclaw.gateway.env
```
Patch `OPENCLAW_SERVICE_VERSION` to the new version too. On source-installed macOS setups the plist invokes this env file via `ai.openclaw.gateway-env-wrapper.sh`, so the service can keep advertising an old version even after plist + JSON state are fixed.

### 6. Kill stale background processes

```bash
ps aux | grep -E 'openclaw|openclaw-update' | grep -v grep
```

Kill any stale `openclaw` or `openclaw-update` processes that predate the update. They can hold old state.

### 7. Restart the gateway

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
sleep 2
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
sleep 3
launchctl list | grep ai.openclaw.gateway
```

**If the restart/bootstrap fails after a version update**, reinstall the LaunchAgent from the built tree before trying again:

```bash
~/.local/bin/openclaw gateway install --force
```

Then re-verify the cached version files and launch the service again. If `launchctl` reports `Could not find service`, reinstalling is usually the fastest path back to a healthy daemon state.

**If the plist is missing** (e.g. `launchctl print` returns "Could not find service"), reinstall it:

```bash
node ~/openclaw/dist/index.js gateway install --force
```

Then re-apply any custom env-file fixes (see env-file pitfall below) before loading.

### 8. Verify

```bash
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep OPENCLAW_SERVICE_VERSION
node ~/openclaw/dist/index.js --version
```

Both must show the target version.

## OpenClaw Telegram Bindings and Hermes Access

When the user asks to let an OpenClaw-routed Telegram user talk to Hermes, inspect `~/.openclaw/openclaw.json` before asking for the ID. OpenClaw stores per-peer routing in `bindings[]` and Telegram allowlists under `channels.telegram.*`; the direct peer/user ID can be copied into Hermes `TELEGRAM_ALLOWED_USERS`. See `references/openclaw-telegram-bindings-to-hermes.md` for the redacted inspection pattern, the Hermes `.env` update, and the important caveat that allowlisting a user does not recreate OpenClaw's `agentId` → profile routing.

### Interpreting per-agent names like `wife`

On Oleksii's setup, names like `wife` refer to an **OpenClaw agent binding**, not a separate executable or LaunchAgent service. If the user says "restart wife gateway" or similar, do not assume a `wife` binary/service exists. First inspect `~/.openclaw/openclaw.json` for `agents[]` and `bindings[]` entries with `id` / `agentId` `wife`.

If `wife` is just a binding on the shared OpenClaw gateway, restart the shared service (`ai.openclaw.gateway`) instead of hunting for a dedicated `wife` daemon. Preferred macOS restart/verify flow:

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code'
curl -fsS http://127.0.0.1:18789/health
```

Use the wording "restarted the OpenClaw gateway that hosts the `wife` binding" so the user can confirm you targeted the right layer.

## OpenClaw Workspace Project Memories

OpenClaw may store user/topic "projects" (long-lived topic memories, not code projects) under the workspace memory tree, not under a top-level `projects` directory.

Discovery checklist:

```bash
find ~/.openclaw/workspace -maxdepth 4 -type f | sort
find ~/.openclaw/workspace/memory/projects -maxdepth 1 -type f -print 2>/dev/null
```

**Pitfall:** Do not assume `~/.openclaw/workspace/projects` exists. On Oleksii's setup, the project memory files were under `~/.openclaw/workspace/memory/projects/`; for example `run.md` contained the jogging/running project log and routing convention `run:`.

When taking over OpenClaw topic memories into Hermes:

1. Inspect `~/.openclaw/workspace/MEMORY.md` for canonical project pointers.
2. Read the relevant file under `~/.openclaw/workspace/memory/projects/<topic>.md`.
3. Copy or summarize it into Hermes durable memory/project notes, e.g. `~/.hermes/memories/projects/<topic>.md`, without flattening detailed logs into always-on memory.
4. Add a compact persistent pointer/fact so future Hermes sessions know where the imported project note lives and what trigger prefix to use.
5. Preserve route prefixes like `run:`, `openmu:`, `notes:`, etc.

For the concrete run/jogging memory import pattern, see `references/openclaw-workspace-project-memories.md`.

## OpenClaw Workspace Memory and Project Notes

OpenClaw's user/topic memory is usually under `~/.openclaw/workspace`, not only in cron/session stores.

Important paths:

- Long-term workspace memory: `~/.openclaw/workspace/MEMORY.md`
- Daily notes: `~/.openclaw/workspace/memory/YYYY-MM-DD.md`
- Project/topic memories: `~/.openclaw/workspace/memory/projects/*.md`

Pitfall: if the user says "projects", "project memories", "run records", or mentions a topic like jogging/running, do **not** jump straight to `~/.openclaw/tasks/runs.sqlite` or `~/.openclaw/cron/jobs.json`. First check `~/.openclaw/workspace/memory/projects/`. In Oleksii's setup, the running/jogging project lived at `~/.openclaw/workspace/memory/projects/run.md` and used the `run:` routing convention.

Discovery commands:

```bash
find ~/.openclaw/workspace/memory/projects -maxdepth 1 -type f -name '*.md' -print
rg -n "jog|run|running|weight|pace|km|project|prefix" ~/.openclaw/workspace/memory ~/.openclaw/workspace/MEMORY.md
```

When migrating topic memories into Hermes, copy them to `~/.hermes/memories/projects/<name>.md` and add a durable pointer/fact so future Hermes sessions know where to append updates.

## Troubleshooting Telegram Non-Response

Use this when the user says OpenClaw is "dead" or does not respond in Telegram. Diagnose from the outside in before changing auth or plugins:

```bash
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code'
curl -fsS http://127.0.0.1:18789/health || true
grep -iE 'telegram|startup failed|SecretRefResolutionError|No callable tools|model login failed|OAuth token refresh failed|refresh_token' \
  ~/.openclaw/logs/gateway.log ~/.openclaw/logs/gateway.err.log 2>/dev/null | tail -120
# Also check stability bundles for startup validation failures
ls -lt ~/.openclaw/logs/stability/*.json 2>/dev/null | head -3
cat ~/.openclaw/logs/stability/*.json 2>/dev/null | python3 -c "
import sys,json
for line in sys.stdin:
    try:
        d=json.loads(line.strip())
        err=d.get('error',{})
        if err.get('name')=='Error' and 'Invalid config' in err.get('message',''):
            print('CONFIG VALIDATION ERROR:', err['message'][:300])
    except: pass
" 2>/dev/null
```

Recovery order:

0. **If launchctl shows a crash-loop (repeat restarts with exit code ≠ 0) but no errors in gateway.log**, check stability bundles (step above). A config validation error produces NO log output in gateway.log — it only appears in stability bundles. The crash-loop symptom: repeated `loading configuration...` → `resolving authentication...` → `starting...` cycles with `last exit code` showing non-zero. The health endpoint returns nothing.

1. If logs show `GEMINI_API_KEY` missing from the LaunchAgent environment, fix the service env secret resolution first; see the next section.
2. If logs show `No callable tools` or an `active-memory` plugin failure, temporarily disable `plugins.entries.active-memory` in `~/.openclaw/openclaw.json` and restart the gateway. Preserve a timestamped backup before editing JSON.
3. If OpenAI Codex auth shows `refresh_token_reused`, switch/fallback the default model to a working provider such as `google/gemini-2.5-flash` so Telegram can respond while Codex is re-authenticated.
4. After any config/auth change that writes to `~/.openclaw/openclaw.json` or auth profiles, restart/kick the gateway; OpenClaw logs may explicitly say `config change requires gateway restart`.
5. If the gateway is healthy but Telegram still feels "dead", inspect for lane/auth mismatches like `unauthorized conn` and `token_mismatch`, and for provider startup aborts such as `codex app-server startup aborted`. A healthy gateway does not guarantee the active model lane is usable.

For the concrete redacted recovery pattern from Oleksii's setup, see `references/openclaw-telegram-recovery.md` and `references/openclaw-telegram-unresponsive-auth-and-fallback.md`.

## Troubleshooting Active Memory Plugin Config Drift

If OpenClaw starts crash-looping right after someone tries to re-enable the `active-memory` plugin, check the latest stability bundle before chasing old auth/secret errors. On Oleksii's setup, a stale plugin config key caused startup validation to fail even though historical logs still contained unrelated `GEMINI_API_KEY` errors.

Current observed failure pattern:

- `launchctl print gui/$(id -u)/ai.openclaw.gateway` shows repeated restarts / non-zero exits
- `curl -fsS http://127.0.0.1:18789/health` fails
- `~/Library/Logs/openclaw/gateway.log` shows repeated `loading configuration… -> resolving authentication… -> starting...` with no `ready`
- Latest stability bundle under `~/.openclaw/logs/stability/*.json` says:
  - `plugins.entries.active-memory.config: invalid config: must not have additional properties: "defaultEnabledProviders"`

Diagnostic commands:

```bash
ls -lt ~/.openclaw/logs/stability/*.json | head -5
cat ~/.openclaw/logs/stability/openclaw-stability-*.json | grep -n 'defaultEnabledProviders\|active-memory' | tail -20
openclaw doctor --lint --non-interactive
```

Concrete fix:

1. Back up `~/.openclaw/openclaw.json`.
2. In `plugins.entries["active-memory"]`, remove `config.defaultEnabledProviders`.
3. Keep the plugin enabled and use only schema-valid keys. Observed good minimal config:

```json
"active-memory": {
  "enabled": true,
  "config": {
    "allowedChatTypes": ["direct", "group", "channel"]
  }
}
```

4. Restart/kick the gateway:

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

5. Verify:

```bash
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code'
curl -fsS http://127.0.0.1:18789/health
```

Success signal in `~/Library/Logs/openclaw/gateway.log`:

```text
http server listening (8 plugins: acpx, active-memory, browser, codex, google, memory-core, microsoft, telegram ...)
```

Important nuance: `openclaw doctor --repair --non-interactive` may quarantine the invalid plugin config and leave `active-memory` disabled. If the user's goal is to keep active memory on, manually re-enable it with a schema-valid config after the doctor run. See `references/openclaw-active-memory-config-drift.md`.

## Troubleshooting LaunchAgent Secret Resolution

If Telegram is dead and the gateway is crash-looping with:

```text
Startup failed: required secrets are unavailable
SecretRefResolutionError: Environment variable "GEMINI_API_KEY" is missing or empty
```

Check whether the user shell can see the sops-nix secret but the LaunchAgent env file cannot:

```bash
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code'
grep -n 'GEMINI_API_KEY' ~/.openclaw/service-env/ai.openclaw.gateway.env || true
stat ~/.config/sops-nix/secrets/openclaw/gemini
```

For Oleksii's source install, the robust fix is to have the service env file read the materialized sops-nix secret at launch instead of copying secret plaintext:

```bash
python3 - <<'PY'
from pathlib import Path
home = Path.home()
envfile = home/'.openclaw/service-env/ai.openclaw.gateway.env'
secret = home/'.config/sops-nix/secrets/openclaw/gemini'
line = f'export GEMINI_API_KEY="$(cat {secret})"'
text = envfile.read_text() if envfile.exists() else ''
lines = text.splitlines()
for i, l in enumerate(lines):
    if l.startswith('export GEMINI_API_KEY=') or l.startswith('GEMINI_API_KEY='):
        lines[i] = line
        break
else:
    lines.append(line)
envfile.write_text('\n'.join(lines) + '\n')
envfile.chmod(0o600)
PY
```

**NOTE:** `gateway install --force` regenerates the service env file. If you previously patched it to use `$(cat …)` syntax for sops-nix secrets, verify the generated file still contains the correct `$(cat …)` line rather than a literal (possibly truncated) key string. Re-apply the Python fix above if needed.

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

Verify `http://127.0.0.1:18789/health` returns `{"ok":true,"status":"live"}` and gateway logs show `http server listening` + `telegram ... starting provider`.

## Troubleshooting Auth Profile Resolution (API Key Profiles)

Use this when a provider returns `401 Invalid API key` or `HTTP 401: Invalid API key` despite having a valid API key in the environment.

### Root cause: auth profile priority over env vars

OpenClaw resolves provider API keys in priority order:

1. **Stored auth profiles** (`~/.openclaw/agents/<agent>/agent/auth-profiles.json`) — highest priority. If a profile entry exists for the provider, its stored key is used.
2. **Environment variables** — fallback when no profile exists. The plugin declares which env vars it can read (e.g. `opencode-go` declares `["OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY"]`).
3. **`models.json` SecretRefs** — used for model registry, not for inference-time auth.

A stale `api_key` profile (hardcoded key in `auth-profiles.json`) silently overrides the env var. The CLI command `openclaw models status` shows the effective source:

```text
# Profile exists — uses profile key, ignores env vars
- opencode-go effective=profiles:... | profiles=1 | opencode-go:default=sk-ATF...bU6q | env=sk-m6uQY...cvizLMx4 | source=env: OPENCODE_API_KEY

# Profile removed — falls back to env var
- opencode-go effective=env:sk-m6uQY...cvizLMx4 | env=sk-m6uQY...cvizLMx4 | source=env: OPENCODE_API_KEY
```

Key diagnostic: if `effective=` shows `profiles:` rather than `env:`, OpenClaw is using the stored profile key, not the env var.

### Diagnostic flow

```bash
# 1. Check auth profiles for stale api_key entries
openclaw models auth list

# 2. Check effective source for the failing provider
openclaw models status | grep -A 2 '<provider-id>'

# 3. If effective=profiles:... and a stale key is suspected,
#    check the raw auth-profiles.json
cat ~/.openclaw/agents/main/agent/auth-profiles.json
```

### Fix: remove stale profiles

The profile IDs are defined by the plugin. For `opencode-go`, the shared profile IDs are `["opencode:default", "opencode-go:default"]` (from `extensions/opencode-go/index.ts` line 15):

1. **Backup** the auth profiles file:
   ```bash
   cp ~/.openclaw/agents/main/agent/auth-profiles.json \
      ~/.openclaw/agents/main/agent/auth-profiles.json.bak.$(date +%Y%m%d-%H%M%S)
   ```

2. **Remove** the stale profile entry (e.g. `opencode-go:default`) from the JSON. The file uses a simple structure:
   ```json
   {
     "version": 1,
     "profiles": {
       "opencode-go:default": {
         "type": "api_key",
         "provider": "opencode-go",
         "key": "sk-ATF..."
       }
     }
   }
   ```
   Remove the stale entry entirely — the provider will then fall back to its declared `envVars`.

3. **Restart** the gateway:
   ```bash
   launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null
   sleep 2
   launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   ```

4. **Verify** the effective source changed:
   ```bash
   openclaw models status | grep '<provider-id>'
   # Should show effective=env:... not effective=profiles:...
   openclaw models auth list
   # Should no longer show the removed profile
   ```

### Pitfall: plugin envVars may not include all env vars you set

The service env file `~/.openclaw/service-env/ai.openclaw.gateway.env` may contain env vars (e.g. `OPENCODE_GO_API_KEY`) that the plugin doesn't declare in its `envVars` list. Check the plugin source for the actual declared vars:

```bash
grep 'envVars:' ~/openclaw/extensions/<provider>/index.ts
```

Example for `opencode-go` (line 32): `envVars: ["OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY"]` — note `OPENCODE_GO_API_KEY` is NOT declared and won't be read, even if set in the service env file.

### Pitfall: gateway restarts regenerate models.json with plugin-default envVar ref

After removing a stale profile and restarting the gateway, `models.json` is regenerated. The `apiKey` field for each provider resets to the plugin's primary `envVar` (declared in the plugin's `createProviderApiKeyAuthMethod` → `envVar` field, typically `OPENCODE_API_KEY` for OpenCode providers).

If the service env file only has secondary vars like `OPENCODE_ZEN_API_KEY` but NOT `OPENCODE_API_KEY`, the models.json reference becomes dangling. The gateway finds no env var matching the SecretRef and auth fails.

**Fix**: Ensure the service env file has the plugin's primary `envVar` set. For OpenCode providers, add both:
```bash
export OPENCODE_API_KEY='<shared-key>'
export OPENCODE_ZEN_API_KEY='<shared-key>'
```
Both should point to the same value. Update `OPENCLAW_SERVICE_MANAGED_ENV_KEYS` to include both names.

### Pitfall: gateway restarts wipe cooldown state for the removed profile

After removing a profile that was in auth cooldown, the cooldown state is in `auth-state.json`, not in `auth-profiles.json`. Removing the profile removes the staleness, but if the provider was also marked as "auth issue" by the gateway, the runtime may skip all its models until the gateway restarts fully.

### Pitfall: multiple profiles for the same provider can create ambiguity

If both `opencode:default` and `opencode-go:default` exist, OpenClaw may select the wrong one. The plugin defines `profileIds` to control which profiles are considered — check the plugin's `createProviderApiKeyAuthMethod` call for the exact list.

### Pitfall: `OPENCODE_GO_API_KEY` is not in the plugin's declared envVars

The service env file may set `OPENCODE_GO_API_KEY` as a separate Go-specific key, but neither the `opencode` nor `opencode-go` plugin declares it in `envVars`. The declared vars are `["OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY"]`. `OPENCODE_GO_API_KEY` is silently ignored, even if set. Remove it if present and use one of the declared vars instead.

### Consolidation pattern: single shared key for Zen + Go

When the user wants one OpenClaw key shared between both `opencode` (Zen) and `opencode-go` (Go) providers:

1. The plugin docs say "OpenCode uses one API key across the Zen and Go catalogs"
2. Set `OPENCODE_API_KEY` (primary envVar used in `models.json`) to the shared key
3. Set `OPENCODE_ZEN_API_KEY` (secondary fallback) to the same value
4. Remove `OPENCODE_GO_API_KEY` (unused by either plugin)
5. Update `OPENCLAW_SERVICE_MANAGED_ENV_KEYS` to `'OPENCODE_API_KEY,OPENCODE_ZEN_API_KEY'`
6. Remove any stale auth profiles for these providers from `auth-profiles.json`
7. Restart the gateway

The Hermes key stays separate in `~/.hermes/.env` as `OPENCODE_API_KEY` with its own value — the service env and the shell env are independent environments.

## Troubleshooting Model Auth After Update

OpenAI Codex OAuth refresh tokens can fail after restart/update with gateway messages like:

- `Model login failed on the gateway for openai-codex`
- `OAuth token refresh failed for openai-codex`
- `Your refresh token has already been used to generate a new access token. Please try signing in again.`

### Diagnose without exposing secrets

```bash
cd ~/openclaw
node ~/openclaw/dist/index.js models auth --help
grep -iE 'openai-codex|model login failed|OAuth token refresh failed|refresh token|auth.*failed' \
  ~/.openclaw/logs/gateway.log ~/.openclaw/logs/gateway.err.log 2>/dev/null | tail -80
```

### Re-auth with device pairing

The browser login flow may require local browser handoff; in remote/agent contexts prefer device pairing so the user can authorize manually:

```bash
cd ~/openclaw
node ~/openclaw/dist/index.js models auth login --provider openai-codex
```

When prompted for auth method, choose **OpenAI Codex Device Pairing**. The CLI prints:

```text
URL: https://auth.openai.com/codex/device
Code: XXXX-XXXXX
```

Send the URL and code to the user, keep the process running, and wait until authorization completes. Treat the device code as short-lived but still avoid logging it to durable notes/skills. After success, restart or kick the gateway if the running process does not pick up the refreshed profile.

Verification:

```bash
node ~/openclaw/dist/index.js models auth --help >/dev/null
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code' || true
grep -iE 'openai-codex|OAuth token refresh failed|auth.*failed' ~/.openclaw/logs/gateway.err.log | tail -20 || true
```

## OpenAI Codex Re-auth After Updates

Use this when the gateway reports `Model login failed on the gateway for openai-codex`, `OAuth token refresh failed for openai-codex`, or `Your refresh token has already been used to generate a new access token`.

1. Confirm the installed version and error without printing secrets:

```bash
cd ~/openclaw
node ~/openclaw/dist/index.js --version
grep -iE 'openai-codex|model login failed|refresh token|OAuth token refresh failed' \
  ~/.openclaw/logs/gateway.log ~/.openclaw/logs/gateway.err.log 2>/dev/null | tail -80
```

2. Prefer the direct device-code method instead of relying on the interactive method picker:

```bash
cd ~/openclaw
node ~/openclaw/dist/index.js models auth login \
  --provider openai-codex \
  --method device-code \
  --set-default
```

3. Send the user the generated URL/code and wait. If an earlier auth process keeps spinning after the user says they already authorized, kill that stale process and start a fresh direct `--method device-code` run; stale/expired device flows can remain stuck on `Waiting for device authorization…`.

4. After the login command exits successfully, **restart/kick the gateway immediately**. Do not leave the running gateway process holding the old refresh token in memory:

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

5. If the user says they refreshed Codex yesterday but `refresh_token_reused` recurs, inspect for duplicate Codex profiles and reload hints. A log line like `config change requires gateway restart (auth.profiles.openai-codex:<email>)` followed by `refresh_token_reused` usually means the refreshed profile was written but the gateway kept stale token state or another OpenClaw process raced refresh-token rotation. Also check for both `openai-codex:default` and `openai-codex:<email>` profiles; stale duplicates can create profile-selection ambiguity. See `references/openclaw-codex-auth-rotation.md` for redacted inspection commands and the repair sequence.

6. Verify with a small gateway/model request or by confirming the next logs no longer contain `OAuth token refresh failed for openai-codex`. If fallback also fails because `opencode-go` is in billing cooldown, fix Codex first; the fallback error is secondary.

## Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `git pull origin main` gets an older version than latest release | `main` and release branch diverged | Use `git checkout vYYYY.M.DD` instead |
| `dist/build-info.json` still shows old version after checkout | `dist/` is committed and stale | Run `pnpm build` |
| Gateway reports old version but `dist/` is new | Cached in plist or `~/.openclaw/openclaw.json` | Patch both, then restart |
| `pnpm build` fails with `@homebridge/ciao` error | Missing/broken dependency | Run `pnpm install` first |
| UI shows old branding/strings | UI assets not rebuilt | Run `pnpm ui:build` |
| Gateway won't start after `gateway install --force` | Install regenerates env file; may lose custom `$(cat …)` secret resolution | Verify env file after install, re-apply fix if needed |
| `launchctl print` says "Could not find service" | LaunchAgent plist was deleted or never installed | Run `gateway install --force`, then fix env file |
| `⚠️ Unknown model: opencode/<id>` in agent runtime, but `models list --refresh` shows it | opencode Zen plugin lacks `resolveDynamicModel`; model only in CLI cache, not agent registry | Add to `agents.defaults.models` + `models.providers` in config, OR inject into `models.json` with `apiKey: "***"`, restart gateway |
| Gateway crash-loop — repeated loading config... -> starting... cycles, no `ready` message, health endpoint down | Config validation failure: (a) `models.providers` apiKey has invalid `SecretRef` format (missing `provider` field), OR (b) `"models": null` in `openclaw.json` (schema rejects null — must remove key entirely) | Check `~/.openclaw/logs/stability/*.json` for `Invalid config` error; fix `SecretRef` to have 3 fields (`source`, `provider`, `id`) or remove `apiKey` entirely if provider handles own auth at runtime; if error says `"models": Invalid input`, delete the `"models"` key (don't set to null) |

## Distinguishing Install Methods

Before troubleshooting, confirm HOW OpenClaw is installed:

- **Source install** (this skill): `~/openclaw` exists as a git repo, `~/.local/bin/openclaw` is a symlink to `~/openclaw/openclaw.mjs`, plist points to `~/openclaw/dist/index.js`
- **Nix install**: Binary in `/nix/store/…-openclaw-gateway-…/bin/openclaw`, managed via `nix profile` or home-manager
- **Homebrew**: `brew list openclaw` would show it

**If the user says "installed from source in ~/openclaw", stop looking for Nix or dotfiles traces.**

## Troubleshooting Model Discovery

Use this when a model `opencode/<model-id>` is expected to be visible but `openclaw models list --provider opencode` either returns nothing, errors, or omits the model, OR when the agent runtime reports `⚠️ Unknown model: opencode/<model-id>` while the CLI lists it fine.

**TL;DR for `⚠️ Unknown model: opencode/<id>`:** The opencode Zen plugin lacks a `resolveDynamicModel` runtime hook. The model can ONLY be resolved through the `models.json` cache OR through a `models.providers` config entry. Fix: (a) add to `agents.defaults.models` in `openclaw.json`, (b) add the provider to `models.providers` (config-based) OR manually inject the `opencode` provider entry into `models.json` with `apiKey: "***"` (hot-fix), (c) ensure a matching `auth.profiles` entry exists, (d) restart the gateway. See `references/openclaw-model-resolution-architecture.md` → "Manual models.json Injection" for the hot-fix recipe, "Config-Based Fix: models.providers" for the config approach, and "Upstream PR Fix" for the proper upstream fix (adding `resolveDynamicModel` to the Zen plugin).

### 0. Understand the two-path resolution architecture (critical) {#critical}

OpenClaw has **two completely separate model resolution paths** that often diverge:

| Path | Source | Used by |
|------|--------|---------|
| **CLI / live API** | Provider plugins via `runProviderCatalog()` → queries the provider API directly (e.g. OpenCode `/v1/models`) | `openclaw models list`, `openclaw models list --refresh`, `openclaw models list --provider <id>` |
| **Agent runtime / cache** | Cached file `~/.openclaw/agents/<agent-id>/agent/models.json` | Agent inference, fallback chain resolution (`modelRegistry.find()`) |

These paths use **different data** and can produce different results. It is common for `models list` to show a model that the agent runtime then reports as **"Unknown model"** — this is the core diagnostic signal.

**The resolveDynamicModel runtime hook gap**: Unlike every other major bundled provider (opencode-go, openai-codex, anthropic, openrouter, google, etc.), the opencode Zen plugin does **not** implement the `resolveDynamicModel` runtime hook. This means `opencode/<model>` models can ONLY be resolved through the `models.json` cache — they cannot be resolved dynamically at inference time. See `references/openclaw-model-resolution-architecture.md` for the full diagnosis and the `apiKey: "***"` placeholder rule required when manually constructing cache entries.

**Why `models.json` exists**: The agent runtime relies on a serialized snapshot of available models rather than querying provider APIs at inference time. This snapshot is built by `ensureOpenClawModelsJson()`, which merges:
- Models listed in `agents.defaults.models` in the user's config
- Provider catalog entries (for the **default provider only** during gateway startup)

**The startup prewarm gap**: When the gateway starts, `ensureOpenClawModelsJson` is called with `providerDiscoveryProviderIds: [defaultProvider]` — it only discovers models for the **default model's provider** (e.g. `openai-codex`). Other providers' models are NOT automatically cached. The CLI on the other hand queries every matching provider plugin's API live.

**The `models` vs `fallbacks` trap**: Models listed in `agents.defaults.model.fallbacks` are NOT added to `models.json`. Only models in `agents.defaults.models` (the configured models map) get written to the cache. A fallback model that is not also in `models` will fail at runtime with "Unknown model" when the agent attempts to fall back to it.

**`models list --refresh` does NOT write to `models.json`** — it only refreshes the CLI view from provider APIs.

### 1. Identify which binary is responding

OpenClaw on Oleksii's setup has **two** install sources that can diverge:

| Install | Path | Invocation |
|---------|------|------------|
| **Nix (nix-darwin)** | `/nix/store/…openclaw-gateway-…/bin/openclaw` | `openclaw` (if on `PATH`) |
| **Source (git repo)** | `~/openclaw` | `pnpm openclaw` from `~/openclaw` |

Always verify which one is answering:

```bash
/nix/store/*openclaw*/bin/openclaw --version 2>/dev/null | head -3
cd ~/openclaw && pnpm openclaw --version 2>/dev/null | head -3
```

The nix-built binary lags behind `main` and the PR branch. If `~/.openclaw/openclaw.json` contains keys a nix binary doesn't recognise (e.g. `agentRuntime`, `spawnSessions`, `bundledDiscovery`), the nix binary refuses to start and returns no models at all.

### 2. Check config compatibility

```bash
openclaw config get providers.opencode 2>&1
# If it says "Config invalid" with Unrecognized key errors,
# the binary is too old for the config — use the source build instead.
```

**Pitfall:** A config written by a newer OpenClaw version (source build) can lock out the older nix binary. Run `openclaw doctor --fix` on the problematic binary OR use the source build for model operations.

### 3. Verify model via source build

```bash
cd ~/openclaw && pnpm openclaw models list --provider opencode
```

If the model appears here but not via the nix binary, it's a binary-staleness issue, not a model-discovery problem.

### 4. Model discovery mechanism

The opencode Zen provider (`opencode` id) does **not** have a static model catalog. Models are discovered dynamically from the OpenCode API endpoint `https://opencode.ai/zen/v1/models`. The `-free` models (e.g. `deepseek-v4-flash-free`, `mimo-v2.5-free`) are returned by this endpoint and appear in the model list.

The `isModernModelRef` function in `extensions/opencode/index.ts` classifies models ending in `-free` as **not modern** (`returns false`). This affects display filtering and routing heuristics but does **not** prevent the model from being listed or usable.

The opencode-go provider (`opencode-go`) has a separate, statically-bundled model catalog in `extensions/opencode-go/provider-catalog.ts` that does **not** include `-free` variants. To use `-free` models, route through the Zen provider (`opencode/` prefix), not the Go provider (`opencode-go/` prefix).

### 5. Verify the PR branch is actually built

If the source checkout is on a PR branch (e.g. `feat/opencode-split-provider-keys`) but `pnpm openclaw` still shows old behaviour, the `dist/` directory may be stale:

```bash
cd ~/openclaw
git log --oneline -1
grep '"version"' dist/build-info.json
# If version predates the branch, rebuild:
pnpm build
```

`dist/` is committed and pre-built in the repo. After checking out the PR branch, `pnpm build` must be run to regenerate `dist/` from the PR source.

### 6. Fix: config-based `models.providers` approach

When the error is `Found agents.defaults.models["X"], but no matching models.providers["X"].models[] entry`, add the provider definition to the top-level `models` section of `openclaw.json`. See `references/openclaw-model-resolution-architecture.md` → "Config-Based Fix: models.providers" for the exact JSON structure, the `apiKey` object format (`{ source: "env", id: "ENV_VAR" }`), the auth profile requirement, and which fix to use when.

### 7. Fix: manual `models.json` injection (hot-fix)

See `references/openclaw-model-resolution-architecture.md` → "Manual models.json Injection" for the full recipe. Requires `apiKey: "***"` placeholder to survive `isWritableProviderConfig` filter on gateway restart.

### 8. Upstream PR fix

The proper upstream fix is to add `resolveDynamicModel` to the opencode Zen plugin (`extensions/opencode/index.ts`). See `references/openclaw-model-resolution-architecture.md` → "Upstream PR Fix" for the exact code changes needed, modeled after the `opencode-go` plugin.

## References

- `references/openclaw-pr-contribution.md` — Contributing PRs to OpenClaw: Real behavior proof requirements, ClawSweeper behavior, PR event forensics
- `references/openclaw-version-cache.md` — Deep dive on where version strings hide
- `references/openclaw-telegram-recovery.md` — Redacted recovery pattern for Telegram non-response caused by LaunchAgent secrets, plugin failures, or stale model auth
- `references/openclaw-billing-retry-loop.md` — Token-drain pattern when a billing-failed fallback has no further fallback (`next=none`)
- `references/openclaw-telegram-bindings-to-hermes.md` — Inspect OpenClaw Telegram bindings/allowlists and migrate user IDs into Hermes access without confusing authorization with per-profile routing
- `references/openclaw-auth-profile-diagnosis.md` — Diagnosing stale API key auth profiles: priority over env vars, env var map, fix pattern
- `references/openclaw-model-resolution-architecture.md` — Two-path model resolution: CLI live API vs agent runtime `models.json` cache, how the cache gets built, `models` vs `fallbacks` trap, diagnostic flow, key code paths, config-based `models.providers` fix, manual `models.json` injection, `apiKey: "***"` placeholder rule, upstream PR fix for missing `resolveDynamicModel`, and auth profile requirements
