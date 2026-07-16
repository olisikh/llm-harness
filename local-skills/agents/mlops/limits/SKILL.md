---
name: limits
description: Check remaining LLM quota windows for CodexBar-enabled providers, formatted concisely for humans. This is a general CodexBar usage skill, not a Codex-specific skill.
---

# Limits

Use this skill when asked for current LLM limits, quota, remaining capacity, or whether Codex/OpenCode Go/Gemini/etc. are close to exhaustion.

## Default command

```bash
python ~/.agents/skills/mlops/limits/scripts/limits.py
```

## Output format (set in stone)

Every provider line follows this exact template:

```text
<ProviderLabel>: <remaining>%/5h <remaining>%/7d <remaining>%/30d
```

When the delivery channel supports Markdown, enclose the complete limits output in one fenced `text` code block. Otherwise, emit the provider lines as plain text.

**Provider labels (fixed):**
| Data provider | Label |
|---|---|
| `codex` (OpenAI Codex) | `Codex` |
| `ollama` (Ollama Cloud) | `Ollama Cloud` |
| `opencodego` (OpenCode Go) | `Opencode GO` |

**Rules:**
- **remaining** = `100.0 - usedPercent`, rounded to whole number (no decimals).
- Windows are always shown in order: **5h / 7d / 30d**.
  - `300 min → 5h`
  - `10080 min → 7d`
  - `43200 min → 30d`
- A window that doesn't exist for a provider simply won't appear in that provider's line.
- Default to all providers enabled in CodexBar config. No extra output.
- **No status/error text** unless the user explicitly asked for a failing provider or no provider returned data at all.
- Keep output concise — exactly one line per provider with data.

## Options

```bash
python ~/.agents/skills/mlops/limits/scripts/limits.py --provider codex --provider opencodego
python ~/.agents/skills/mlops/limits/scripts/limits.py --json
```

## Notes

- Strip `CODEX_HOME` before invoking CodexBar so isolated homes do not break Codex CLI usage reads.
- The `codex` provider should use codexbar `--source cli`; the web source can hang.
- Provider errors should be printed as short status lines only when that provider was explicitly requested or no successful limits were found.
- Skill name is `limits`; in Hermes skill-slash form this is intended to be `/limits`.
- The canonical source path is `~/.llm-harness/local-skills/agents/mlops/limits`; the installed runtime path is `~/.agents/skills/mlops/limits`.
- For harness repository maintenance, use `cd ~/.llm-harness && ./harness.py update-repo` for a full refresh or `./harness.py update-skills` for configured submodule sources only; do not link or copy `update-skills.sh` into runtime homes.
