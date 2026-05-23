# OpenClaw Version Cache Deep Dive

When OpenClaw reports a wrong version after update, the version string can be cached in **four layers**. Check them in order.

## Layer 1: `dist/build-info.json`

Built from source during `pnpm build`. If stale, the entire distribution is old.

```bash
grep '"version"' ~/openclaw/dist/build-info.json
```

**Fix:** `pnpm build && pnpm ui:build`

## Layer 2: LaunchAgent plist env var

The `OPENCLAW_SERVICE_VERSION` env var is set in the plist and injected into the running gateway process.

```bash
plutil -p ~/Library/LaunchAgents/ai.openclaw.gateway.plist | grep -i version
```

**Fix:** `sed -i '' 's/OLD/NEW/g' ~/Library/LaunchAgents/ai.openclaw.gateway.plist`, then unload/load.

## Layer 3: `~/.openclaw/openclaw.json`

OpenClaw persists its last-known version in user state:

```bash
grep -n "lastTouchedVersion\|lastRunVersion" ~/.openclaw/openclaw.json
```

**Fix:** Patch both fields to the new version string.

## Layer 4: Stale background processes

Old `openclaw` CLI or `openclaw-update` daemon processes may hold old state in memory.

```bash
ps aux | grep -E 'openclaw|openclaw-update' | grep -v grep
```

**Fix:** `kill` any processes whose start time predates the update.

## Quick Diagnostic Script

```bash
#!/bin/bash
echo "=== dist/build-info.json ==="
grep '"version"' ~/openclaw/dist/build-info.json

echo "=== plist version ==="
plutil -p ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null | grep -i version

echo "=== openclaw.json versions ==="
grep -E '"(lastTouched|lastRun)Version"' ~/.openclaw/openclaw.json

echo "=== running gateway version ==="
launchctl print gui/$(id -u)/ai.openclaw.gateway 2>/dev/null | grep OPENCLAW_SERVICE_VERSION

echo "=== stale processes ==="
ps aux | grep -E 'openclaw' | grep -v grep
```
