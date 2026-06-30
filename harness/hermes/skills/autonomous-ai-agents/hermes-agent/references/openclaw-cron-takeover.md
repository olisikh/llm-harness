# OpenClaw cron takeover into Hermes

Use when replacing existing OpenClaw scheduled jobs with Hermes cron jobs, especially Telegram announcement jobs.

## Discovery

- OpenClaw user config is usually `~/.openclaw/openclaw.json`.
- OpenClaw cron definitions are usually `~/.openclaw/cron/jobs.json`.
- OpenClaw cron runtime state is usually `~/.openclaw/cron/jobs-state.json`.
- OpenClaw LaunchAgent on macOS may be `~/Library/LaunchAgents/ai.openclaw.gateway.plist`.
- Hermes cron tool state can be inspected with `cronjob(action="list")` or `hermes cron list --all`.
- Hermes messaging targets can be inspected with `send_message(action="list")`, but group/channel targets may not be listed. Copy explicit OpenClaw delivery targets from `jobs.json` when needed, e.g. `delivery.to: telegram:-...`.

## Migration steps

1. Load the Hermes skill before making Hermes config/cron changes.
2. Read OpenClaw cron jobs from `~/.openclaw/cron/jobs.json` and summarize:
   - `id`, `name`, `enabled`, `schedule`, `payload.message`, `payload.toolsAllow`, `delivery`.
3. Read `jobs-state.json` to preserve cadence:
   - convert `lastRunAtMs` / `nextRunAtMs` to local timezone with Python `datetime` + `zoneinfo`.
   - for OpenClaw `every` schedules with an anchor, recreate in Hermes with an equivalent cron expression when preserving the exact next run is important.
4. Create Hermes cron jobs with `cronjob(action="create", ...)`:
   - `deliver` should usually be the copied OpenClaw `delivery.to` value.
   - for web/event/weather scout jobs, set `enabled_toolsets` to at least `web`; add `session_search` when avoiding duplicate recommendations matters.
   - update prompt identity from OpenClaw/Clawdy to Hermes while preserving task requirements.
   - embed durable user filters that affect the class of recommendations, such as excluding Russia-related events and avoiding repeated suggestions.
5. Verify Hermes jobs with `cronjob(action="list")` and, if useful, a quick web-search smoke test.
6. Disable old OpenClaw jobs only after Hermes jobs are created:
   - from `/Users/olisikh/openclaw`: `pnpm openclaw cron edit <job-id> --disable --timeout 60000`
   - verify by reading `~/.openclaw/cron/jobs.json` and confirming `enabled=false`.
7. Do not stop the whole OpenClaw gateway unless the user explicitly wants it. Disabling jobs avoids double-posting while preserving other OpenClaw functions.

## Pitfalls

- `send_message(action="list")` may show only configured/home targets, not all Telegram groups/channels. For takeover, OpenClaw's `delivery.to` is the more reliable target source.
- OpenClaw CLI output may include banners or postbuild messages, so piping `pnpm openclaw ... --json` directly into JSON parsers can fail. Prefer reading the JSON store directly for verification.
- Do not migrate OpenClaw state-backup cron blindly into Hermes if it exists solely to back up OpenClaw state; disable it when OpenClaw scheduled work is retired unless the user asks to keep OpenClaw backups.
- Avoid duplicate announcements: create Hermes jobs first, then disable OpenClaw jobs in the same session, and verify both sides.
