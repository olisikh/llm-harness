# OpenClaw Telegram Recovery Notes

Session-derived pattern for when OpenClaw appears dead in Telegram while the macOS LaunchAgent may still be running.

## Symptoms observed

- User reported OpenClaw did not respond in Telegram.
- Gateway process could be running, but startup or provider initialization failed.
- Logs contained combinations of:
  - `SecretRefResolutionError: Environment variable "GEMINI_API_KEY" is missing or empty`
  - `No callable tools` from the `active-memory` plugin path
  - OpenAI Codex OAuth errors such as `refresh_token_reused`
  - `config change requires gateway restart`

## Safe diagnostic commands

```bash
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E 'state =|pid =|last exit code'
curl -fsS http://127.0.0.1:18789/health || true
grep -iE 'telegram|startup failed|SecretRefResolutionError|GEMINI_API_KEY|No callable tools|active-memory|openai-codex|refresh_token|config change requires gateway restart' \
  ~/.openclaw/logs/gateway.log ~/.openclaw/logs/gateway.err.log 2>/dev/null | tail -160
```

Avoid printing secret values. Check existence/mtime/permissions instead:

```bash
stat ~/.config/sops-nix/secrets/openclaw/gemini
sed -n '/GEMINI_API_KEY/p' ~/.openclaw/service-env/ai.openclaw.gateway.env
```

## Recovery sequence that worked

1. Restore `GEMINI_API_KEY` visibility to the LaunchAgent environment by making `~/.openclaw/service-env/ai.openclaw.gateway.env` read the materialized sops-nix secret at launch time:

   ```bash
   export GEMINI_API_KEY="$(cat ~/.config/sops-nix/secrets/openclaw/gemini)"
   ```

   Keep the env file mode restrictive (`chmod 600`).

2. Back up `~/.openclaw/openclaw.json`, then disable the broken `plugins.entries.active-memory` entry if it causes `No callable tools` startup/provider failures.

3. Set/keep a working non-Codex default model such as `google/gemini-2.5-flash` so Telegram recovers while Codex OAuth is repaired.

4. Restart/kick the LaunchAgent after config/auth changes:

   ```bash
   launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
   ```

5. Verify health and Telegram provider startup:

   ```bash
   curl -fsS http://127.0.0.1:18789/health
   grep -iE 'http server listening|telegram.*starting provider|OAuth token refresh failed|No callable tools' \
     ~/.openclaw/logs/gateway.log ~/.openclaw/logs/gateway.err.log 2>/dev/null | tail -60
   ```

## Pitfalls

- Do not assume a running LaunchAgent means Telegram is usable; check health endpoint and provider logs.
- Do not spend time on Codex first if a missing gateway secret prevents startup entirely.
- Device-code Codex login can time out; if the user does not authorize in the window, start a fresh flow rather than waiting indefinitely.
- Duplicate Codex profiles (`openai-codex:default` and `openai-codex:<email>`) can make auth state ambiguous; see `openclaw-codex-auth-rotation.md`.
