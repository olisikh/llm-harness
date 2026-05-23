---
name: limits
description: Check remaining LLM quota windows for CodexBar-enabled providers, formatted concisely for humans.
---

# Limits

Use this skill when asked for current LLM limits, quota, remaining capacity, or whether Codex/OpenCode Go/Gemini/etc. are close to exhaustion.

## Default command

```bash
python ~/.hermes/skills/mlops/limits/scripts/limits.py
```

Default output is intentionally terse:

```text
Codex: 94%/5h 60%/7d
OpenCode Go: 100%/5h 90%/7d 0%/30d
```

Rules:
- Show **remaining**, not used.
- Convert windows to human units: `300 min → 5h`, `10080 min → 7d`, `43200 min → 30d`.
- Default to providers enabled in CodexBar config.
- Keep user-facing output concise.

## Options

```bash
python ~/.hermes/skills/mlops/limits/scripts/limits.py --provider codex --provider opencodego
python ~/.hermes/skills/mlops/limits/scripts/limits.py --json
```

## Notes

- Strip `CODEX_HOME` before invoking CodexBar so isolated Codex homes do not break Codex CLI usage reads.
- Codex should use codexbar `--source cli`; the web source can hang.
- Provider errors should be printed as short status lines only when that provider was explicitly requested or no successful limits were found.
- Skill name is `limits`; in Hermes skill-slash form this is intended to be `/limits`.
