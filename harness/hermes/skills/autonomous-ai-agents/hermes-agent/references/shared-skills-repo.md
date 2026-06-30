# Shared skills repository layout

On Oleksii's setup, durable physical skill sources live in `~/llm-harness` and should be edited there, not in installed runtime trees.

Compatibility rule:
- Edit and commit only the repo copy.
- Run `cd ~/llm-harness && ./install.sh` after creating, moving, or renaming skills.
- Do not maintain two editable copies of the same skill.

Current convention:
- Canonical skills repo root: `~/llm-harness`
- Portable skills source subtree: `~/llm-harness/harness/agents/skills`
- Hermes-specific skills source subtree: `~/llm-harness/harness/hermes/skills`
- Claude-specific skills source subtree: `~/llm-harness/harness/claude/skills`
- Runtime install paths: `~/.agents/skills`, `~/.hermes/skills`, `~/.claude/skills`
