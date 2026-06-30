# OpenClaw project memory takeover into Hermes

Use when the user refers to OpenClaw "projects", topic memories, or records such as running/jogging logs. Do not assume they mean cron jobs or task-run records.

## Important paths

- OpenClaw workspace root: `~/.openclaw/workspace/`
- OpenClaw curated long-term memory: `~/.openclaw/workspace/MEMORY.md`
- OpenClaw daily notes: `~/.openclaw/workspace/memory/YYYY-MM-DD.md`
- OpenClaw project/topic memories: `~/.openclaw/workspace/memory/projects/*.md`
- Hermes durable memory files: `~/.hermes/memories/`
- Good Hermes import target for project memories: `~/.hermes/memories/projects/<name>.md`

The path `~/.openclaw/workspace/projects` may not exist; check `~/.openclaw/workspace/memory/projects` before saying projects are absent.

## Discovery workflow

```bash
find ~/.openclaw/workspace/memory/projects -maxdepth 1 -type f -name '*.md' -print
rg -n "jog|run|running|weight|pace|km|project|prefix" ~/.openclaw/workspace/memory ~/.openclaw/workspace/MEMORY.md
```

For a specific project, read the file directly, e.g.:

```bash
cat ~/.openclaw/workspace/memory/projects/run.md
```

## Import workflow

1. Locate the OpenClaw project memory file.
2. Create the Hermes project-memory directory if needed:

```bash
mkdir -p ~/.hermes/memories/projects
```

3. Copy the project file, preserving markdown:

```bash
cp ~/.openclaw/workspace/memory/projects/run.md ~/.hermes/memories/projects/run.md
```

4. Add a small durable fact/pointer to Hermes memory/fact store so future sessions know the project exists and which trigger prefix to use.
5. When the user sends a screenshot or update for the project, append to the project file, not only to generic memory.

## Example: run/jogging project

Observed OpenClaw project file: `~/.openclaw/workspace/memory/projects/run.md`.

It tracked:
- `run:` routing convention
- 5km goal on 2026-09-27
- weight/height and health context
- nutrition/macros
- weekly training structure
- run log entries with distance/time/pace/steps/status

When the user sends a running screenshot, OCR/extract visible metrics and append a new `Run N` entry to `~/.hermes/memories/projects/run.md`. If vision tools fail, use macOS Vision OCR via a small Swift script as a fallback.

## Pitfall

If the user asks about "run records" and mentions OpenClaw projects, clarify internally that this may mean **project memory files**, not OpenClaw task run SQLite records or cron jobs. Check project memory paths first before summarizing cron migration state.