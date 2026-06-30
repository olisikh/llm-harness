# Hermes Cron Jobs Writing to Apple Calendar

Use this reference when a scheduled Hermes scouting/planning cron job should also maintain a user-visible Apple/iCloud calendar.

## Pattern

- Do not create/update Apple Calendar events by writing `Calendar.sqlitedb` directly. That database is only a local cache; direct writes can bypass Calendar/iCloud change records and fail to sync or display correctly.
- Keep the calendar writer as a narrow helper under `$HERMES_HOME/scripts/` rather than embedding Apple Calendar automation logic directly in every cron prompt.
- The helper should be idempotent: dedupe by title/date/link (or equivalent stable event identity) before creating events.
- Use Calendar.app/AppleScript automation for writes; SQLite/database backups are diagnostic safety only and do not make direct DB writes acceptable.
- Cron jobs need both `file` and `terminal` tools if they are expected to call a local helper script and inspect outputs.
- Attach the `apple-calendar` skill to every cron job that scouts/plans events so future runs inherit the Calendar.app-only policy and helper contract.
- Prompt the cron job to report a short calendar accounting line in the delivered message, e.g. `Calendar: 3 created, 5 skipped`.

## Oleksii setup observed Apr 2026

- Calendar name: `Hermes Events` (renamed from `Events from Clawdy`; an intermediate `Interesting Events` name existed briefly).
- Preferred Calendar helper path: `/Users/olisikh/.hermes/scripts/interesting_events_calendar_app.py` (Calendar.app/AppleScript automation; avoids direct DB writes).
- Legacy direct-DB helper path: `/Users/olisikh/.hermes/scripts/interesting_events_calendar.py` (intentionally disabled; do not re-enable or use for event writes).
- Event preferences + suggestion ledger:
  - Preferences: `/Users/olisikh/.hermes/event-scout/preferences.md`
  - Ledger: `/Users/olisikh/.hermes/event-scout/ledger.json`
  - Helper/pre-run script: `/Users/olisikh/.hermes/scripts/event_scout_memory.py`
- Backup path pattern used by the helper/session: `/Users/olisikh/.hermes/backups/calendar/<timestamp>`.
- Updated cron jobs:
  - `579ecda92741` — Weekly outdoor events scout
  - `0cca64da58d9` — Weekly weekend planner

## Prompting rules for event-scout cron jobs

Ask jobs to:

1. Add only main recommended events to `Hermes Events`.
2. Skip sold-out events.
3. Avoid adding maybe/backup items unless they are clearly worthwhile.
4. For long-running exhibitions/festivals, create only relevant weekend/date-specific markers instead of cluttering the calendar with the full run.
5. Dedupe by title/date/link.
6. Include created/skipped counts in the Telegram summary. If the user expects visible calendar writes, make this the first line of the delivered message (`Calendar: created X, skipped duplicates Y, failed Z`) so a successful write is not hidden in tool output.
7. Read event preferences and recent suggestion ledger via `event_scout_memory.py` before searching.
8. Record delivered main + maybe suggestions back into the ledger after each run.
9. Preserve the `TUNE:` feedback line; when Oleksii later replies with `TUNE: ...`, update `event-scout/preferences.md` first, and edit cron prompts only if the job structure itself needs to change.

## Verification

- Verify the target calendar exists after rename or creation.
- Count existing entries before/after if preserving old events matters.
- Run a duplicate test against a known existing event and confirm the helper skips instead of creating another copy.
- Remove temporary compiled/test artifacts after verification.
