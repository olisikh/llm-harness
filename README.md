# llm-harness

Personal harness hub for LLM skills and harness-specific home files.

## Layout

```text
llm-harness/
├── AGENTS.md                  # repo contributor rules
├── harness/
│   ├── agents/                # mirrors ~/.agents/
│   │   └── skills/
│   ├── claude/                # mirrors ~/.claude/
│   │   ├── CLAUDE.md
│   │   └── skills/
│   ├── opencode/              # mirrors ~/.config/opencode/
│   │   └── skills/
│   ├── hermes/                # mirrors ~/.hermes/
│   │   └── skills/
│   └── codex/                 # mirrors ~/.codex/
│       └── skills/
├── harness-paths.yaml         # non-obvious harness root overrides
├── install.sh
├── uninstall.sh
├── scripts/
└── skills-config.yaml         # shared submodule sync rules
```

## Install model

Run from repo root:

```bash
./install.sh
```

Installer behavior:

- auto-discovers `harness/*`
- maps harness homes by convention:
  - `agents` -> `~/.agents`
  - `claude` -> `~/.claude`
  - `codex` -> `~/.codex`
- reads `harness-paths.yaml` for non-obvious roots like OpenCode and custom Hermes skill installs
- symlinks each skill directory individually under target `skills/`, preserving nested category paths
- symlinks non-skill top-level files and directories 1:1 into target harness home
- removes stale managed symlinks
- warns and skips when target path already exists and is not matching expected symlink

To remove managed symlinks later:

```bash
./uninstall.sh
```

## Shared upstream skill sync

Shared skill sources live as git submodules:

- `obsidian-skills`
- `mattpocock-skills`

Update them with:

```bash
./scripts/update-skills.sh
```

Optional commit/push flow:

```bash
./scripts/update-skills.sh --commit --push
```

Sync rules:

- submodule skills default to portable `harness/agents/skills`
- exceptions use explicit harness overrides in `skills-config.yaml`
- local first-party skills can shadow upstream names; shared sync skips conflicting real directories

## Notes

- canonical checkout path is `~/llm-harness`
- portable skill sources live under `~/llm-harness/harness/agents/skills` and install to `~/.agents/skills`
- custom Hermes-only skill sources live under `~/llm-harness/harness/hermes/skills` and install to `~/.hermes/skills`
- Hermes package-bundled skills stay in the Hermes install/source tree, not in `llm-harness`
- OpenCode will discover both `~/.agents/skills` and `~/.config/opencode/skills`
- Claude portable-skill auto-discovery is deferred for now
