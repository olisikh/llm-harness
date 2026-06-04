# OpenClaw active-memory config drift causing gateway crash-loop

Use when OpenClaw was healthy, then someone tried to turn `active-memory` back on and the gateway started crash-looping on restart.

## Symptom bundle

- `launchctl print gui/$(id -u)/ai.openclaw.gateway` shows repeated restarts / non-zero exit.
- `curl -fsS http://127.0.0.1:18789/health` fails.
- `~/Library/Logs/openclaw/gateway.log` repeats:
  - `loading configuration…`
  - `resolving authentication…`
  - `starting...`
  - then restart, with no `ready`
- Fresh stability bundle in `~/.openclaw/logs/stability/` says:

```text
Invalid config at ~/.openclaw/openclaw.json.
plugins.entries.active-memory.config: invalid config:
must not have additional properties: "defaultEnabledProviders"
```

## Key lesson

Do not trust old `gateway.err.log` auth/secret failures as the current root cause when the newest stability bundle points at config validation. In the observed session, stale `GEMINI_API_KEY` errors existed historically, but the active failure was a schema-invalid `active-memory` plugin config.

## Minimal recovery

Back up config, then change the plugin block from this invalid shape:

```json
"active-memory": {
  "enabled": true,
  "config": {
    "defaultEnabledProviders": ["telegram"],
    "allowedChatTypes": ["direct", "group", "channel"]
  }
}
```

To this schema-valid shape:

```json
"active-memory": {
  "enabled": true,
  "config": {
    "allowedChatTypes": ["direct", "group", "channel"]
  }
}
```

Then restart:

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

## Verification

```bash
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code'
curl -fsS http://127.0.0.1:18789/health
tail -n 80 ~/Library/Logs/openclaw/gateway.log
```

Healthy markers:

- `state = running`
- health returns `{"ok":true,"status":"live"}`
- log includes active memory in the loaded plugin list, e.g.:

```text
http server listening (8 plugins: acpx, active-memory, browser, codex, google, memory-core, microsoft, telegram ...)
```

## Doctor nuance

`openclaw doctor --repair --non-interactive` can help surface the issue and may quarantine the invalid plugin config, but it can leave `active-memory` disabled. If the user explicitly wanted active memory enabled, re-check `plugins.entries["active-memory"]` after doctor runs and restore a schema-valid enabled block manually.
