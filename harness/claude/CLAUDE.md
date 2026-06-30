# Claude Harness

Global Claude-specific files for this machine live here.

- Claude-specific skill sources live in `~/llm-harness/harness/claude/skills` and install to `~/.claude/skills`.
- Portable skill sources live in `~/llm-harness/harness/agents/skills` and install to `~/.agents/skills`.
- Custom Hermes-only skill sources live in `~/llm-harness/harness/hermes/skills` and install to `~/.hermes/skills`.
- Hermes package-bundled skills stay in the Hermes install/source tree and should not be mirrored into `~/llm-harness`.
- Portable-skill auto-discovery from installed `~/.agents/skills` is not wired for Claude yet.
- Repo contributor rules for `~/llm-harness` live in repo-root `AGENTS.md`, not here.
