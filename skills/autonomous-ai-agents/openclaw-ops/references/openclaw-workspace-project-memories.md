# OpenClaw workspace project memories

Use when the user asks about OpenClaw "projects", topic memories, running/jogging logs, or whether Hermes took over project-specific context.

## Key path lesson

OpenClaw topic projects are not necessarily under:

```text
~/.openclaw/workspace/projects
```

On Oleksii's machine, the relevant files were under:

```text
~/.openclaw/workspace/memory/projects/
```

Example discovered during migration:

```text
~/.openclaw/workspace/memory/projects/run.md
```

This contained the run/jogging project memory, including route prefix `run:` and a run log.

## Discovery commands

```bash
find ~/.openclaw/workspace -maxdepth 4 -type f | sort
find ~/.openclaw/workspace/memory/projects -maxdepth 1 -type f -print 2>/dev/null
sed -n '1,220p' ~/.openclaw/workspace/memory/projects/run.md
```

Also inspect long-term memory for canonical pointers:

```bash
sed -n '1,220p' ~/.openclaw/workspace/MEMORY.md
```

## Import pattern into Hermes

Do not dump detailed project logs into always-on memory. Keep a file and save only a compact pointer.

```bash
mkdir -p ~/.hermes/memories/projects
cp ~/.openclaw/workspace/memory/projects/run.md ~/.hermes/memories/projects/run.md
```

Then save a compact durable fact/pointer such as:

```text
Oleksii's OpenClaw run/jogging project memory was imported into Hermes at ~/.hermes/memories/projects/run.md. Trigger convention: `run:`.
```

## Run/jogging project snapshot discovered

Source file:

```text
~/.openclaw/workspace/memory/projects/run.md
```

Important content:

- Project title: `Run/Marathon Training Project`
- Goal: 5km race on 2026-09-27
- Starting/current stats recorded around 2026-04-14: 118kg, 177-178cm, BMI ~37.5
- Nutrition target: 2,200-2,400 kcal, ~220g protein, 150-200g carbs, 70-80g fats
- Weekly structure: 3 gym days + 3 run days + rest/active recovery
- Run log:
  - Run 1 — 2026-04-13: 2.49 km, 20:13, 8:06/km, felt very hard
  - Run 2 — 2026-04-19: 2.57 km, 21:35, 8:23/km, 3,046 steps, felt better
  - Run 3 — 2026-04-21: 2.59 km, 20:05, 7:45/km, 2,820 steps, easier start/hard finish
- Route prefix: `run:`

## Pitfall from the session

The user corrected the assistant after it looked at OpenClaw cron/run records instead of the workspace project-memory folder. When the user says "projects" in this OpenClaw context, first check `~/.openclaw/workspace/memory/projects/` before cron jobs, task runs, or trajectory logs.
