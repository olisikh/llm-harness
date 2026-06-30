# OpenClaw Source Update Checklist

When a user has OpenClaw installed from source at `~/openclaw` and needs to update it (e.g. after a new release tag like `v2026.4.29`), follow this checklist.

## Update Steps

1. **Fetch and checkout the release tag** (NOT `main`, which may diverge from releases):
   ```bash
   cd ~/openclaw && git fetch origin --tags
   git checkout vYYYY.M.DD
   ```

2. **Install dependencies** (required when lockfile or deps changed):
   ```bash
   pnpm install
   ```

3. **Rebuild core distribution** (`dist/` is pre-built in the repo and may be stale):
   ```bash
   pnpm build
   ```

4. **Rebuild UI** (required for control UI assets):
   ```bash
   pnpm ui:build
   ```

5. **Patch version caches**:
   - `~/Library/LaunchAgents/ai.openclaw.gateway.plist` — update `OPENCLAW_SERVICE_VERSION` env var
   - `~/.openclaw/openclaw.json` — update `lastTouchedVersion` and `lastRunVersion`

6. **Kill stale background processes**:
   ```bash
   ps aux | grep -E 'openclaw|openclaw-update' | grep -v grep
   kill <stale PIDs>
   ```

7. **Restart the gateway**:
   ```bash
   launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   sleep 2
   launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   ```

8. **Verify**:
   ```bash
   launchctl print gui/$(id -u)/ai.openclaw.gateway | grep OPENCLAW_SERVICE_VERSION
   node ~/openclaw/dist/index.js --version
   ```

## Key Pitfalls

- `main` and release tags **diverge** — `git pull origin main` may give you an older version than the latest release tag
- `dist/` contains **pre-built artifacts** that are committed — they do NOT auto-update on `git checkout`
- The LaunchAgent plist hardcodes the version string in an env var — the gateway process reads this, not `dist/build-info.json`
- `~/.openclaw/openclaw.json` caches the last-known version — OpenClaw reports this to the user
- Stale `openclaw` or `openclaw-update` background processes from previous days can hold old state

## Distinguishing Install Methods

If the user says OpenClaw is "installed from source in `~/openclaw`", **do not** look for Nix packages, home-manager traces, or `.dotfiles` definitions. The source install is standalone:
- `~/.local/bin/openclaw` → `~/openclaw/openclaw.mjs`
- Gateway plist points to `~/openclaw/dist/index.js`
- Separate from any `/nix/store/…-openclaw-gateway-…` binaries that may also exist

For the full maintenance skill (including deep version-cache diagnostics), load `openclaw-ops`.
