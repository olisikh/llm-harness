---
name: openclaw-ops
description: "Maintain, update, and troubleshoot a source-installed OpenClaw instance alongside Hermes."
version: 1.0.0
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

## Environment Assumptions

- Source repo: `~/openclaw`
- CLI wrapper: `~/.local/bin/openclaw` → `~/openclaw/openclaw.mjs`
- Gateway LaunchAgent plist: `~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- Shared skills repo: `~/.agents` with skill content under `~/.agents/skills/`; see `references/shared-skills-repo-migration.md` for the symlink-preserving move pattern.
- Shared skills repo on Oleksii's setup: `~/.agents` (with `~/.skills` kept as a compatibility symlink when needed)

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
```

Recovery order:

1. If logs show `GEMINI_API_KEY` missing from the LaunchAgent environment, fix the service env secret resolution first; see the next section.
2. If logs show `No callable tools` or an `active-memory` plugin failure, temporarily disable `plugins.entries.active-memory` in `~/.openclaw/openclaw.json` and restart the gateway. Preserve a timestamped backup before editing JSON.
3. If OpenAI Codex auth shows `refresh_token_reused`, switch/fallback the default model to a working provider such as `google/gemini-2.5-flash` so Telegram can respond while Codex is re-authenticated.
4. After any config/auth change that writes to `~/.openclaw/openclaw.json` or auth profiles, restart/kick the gateway; OpenClaw logs may explicitly say `config change requires gateway restart`.

For the concrete redacted recovery pattern from Oleksii's setup, see `references/openclaw-telegram-recovery.md`.

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

## Distinguishing Install Methods

Before troubleshooting, confirm HOW OpenClaw is installed:

- **Source install** (this skill): `~/openclaw` exists as a git repo, `~/.local/bin/openclaw` is a symlink to `~/openclaw/openclaw.mjs`, plist points to `~/openclaw/dist/index.js`
- **Nix install**: Binary in `/nix/store/…-openclaw-gateway-…/bin/openclaw`, managed via `nix profile` or home-manager
- **Homebrew**: `brew list openclaw` would show it

**If the user says "installed from source in ~/openclaw", stop looking for Nix or dotfiles traces.**

## References

- `references/openclaw-version-cache.md` — Deep dive on where version strings hide
- `references/openclaw-telegram-recovery.md` — Redacted recovery pattern for Telegram non-response caused by LaunchAgent secrets, plugin failures, or stale model auth
- `references/openclaw-billing-retry-loop.md` — Token-drain pattern when a billing-failed fallback has no further fallback (`next=none`)
- `references/openclaw-telegram-bindings-to-hermes.md` — Inspect OpenClaw Telegram bindings/allowlists and migrate user IDs into Hermes access without confusing authorization with per-profile routing
