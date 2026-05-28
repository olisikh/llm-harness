# OpenClaw Telegram bindings → Hermes allowlists/profiles

Use when the user asks to let an OpenClaw-routed Telegram user talk to Hermes, or asks for a spouse/family member/profile migration.

## What OpenClaw stores

OpenClaw may route Telegram peers to agent IDs in `~/.openclaw/openclaw.json`:

- `bindings[]`: maps a `channel` + `peer.id` + `peer.kind` to an `agentId` such as `wife`.
- `channels.telegram.allowFrom[]`: direct-message allowed user IDs.
- `channels.telegram.groupAllowFrom[]`: group sender allowed user IDs.
- `channels.telegram.groups.<chat_id>.allowFrom[]`: per-group allowed senders.
- `channels.telegram.direct.<user_id>`: per-DM behavior such as thread replies.

The useful value for Hermes `TELEGRAM_ALLOWED_USERS` is the numeric direct peer/user ID from either `bindings[].match.peer.id` where `kind == "direct"`, or from `channels.telegram.allowFrom[]`.

## Safe inspection pattern

Do not print bot tokens or API keys. Redact `tokenFile`, `token`, `apiKey`, and bot-token-looking values.

Minimal Python pattern:

```python
from pathlib import Path
import json, re
p = Path('~/.openclaw/openclaw.json').expanduser()
data = json.loads(p.read_text())
for b in data.get('bindings', []):
    m = b.get('match', {})
    if m.get('channel') == 'telegram':
        peer = m.get('peer', {})
        print({'agentId': b.get('agentId'), 'kind': peer.get('kind'), 'id': peer.get('id')})
print('telegram.allowFrom:', data.get('channels', {}).get('telegram', {}).get('allowFrom', []))
```

## Hermes migration actions

For current single-bot Hermes gateway access, add the user ID to the running profile's `.env`:

```env
TELEGRAM_ALLOWED_USERS=<owner_id>,<migrated_user_id>
```

Then restart the running gateway:

```bash
hermes gateway restart
```

If a separate Hermes profile was created for that person, also update that profile's `.env` for future use, but do not start a second gateway with the same Telegram bot token; two long-polling gateways using one Telegram token can conflict.

## Important limitation

Adding the OpenClaw-routed user ID to Hermes only authorizes the user on the currently running Hermes profile. It does not automatically reproduce OpenClaw's `bindings.agentId` routing. For true per-user profile routing in Hermes, use either:

1. a separate Telegram bot token plus `hermes --profile <name> gateway ...`, or
2. a Hermes routing hook/feature that dispatches messages from a Telegram user ID to a profile.

Until such routing exists, be explicit in the final response: the user can talk to Hermes, but the default gateway still uses the default profile unless a separate profile gateway/token or routing hook is configured.
