# llm-harness

Personal harness hub for LLM skills and harness-specific home files.

## Layout

```text
llm-harness/
├── AGENTS.md                  # repo contributor rules
├── harness/                   # harness-specific home files
│   ├── agents/                # mirrors ~/.agents/
│   ├── claude/                # mirrors ~/.claude/
│   │   └── CLAUDE.md
│   ├── opencode/              # mirrors ~/.config/opencode/
│   ├── hermes/                # mirrors ~/.hermes/
│   └── codex/                 # mirrors ~/.codex/
├── local-skills/              # local first-party skill sources
│   ├── agents/                # portable skills → ~/.agents/skills/
│   ├── claude/                # Claude-only skills → ~/.claude/skills/
│   ├── codex/                 # Codex-only skills → ~/.codex/skills/
│   └── hermes/                # Hermes-only skills → ~/.hermes/skills/
├── docs/
│   └── llm-harness-ops.md     # canonical operational guide
├── harness-paths.yaml         # non-obvious harness root overrides
├── harness.py                 # unified entrypoint
├── llm_harness/               # Python implementation
├── scripts/                   # automation helpers
├── obsidian-skills            # shared upstream skill submodule
├── mattpocock-skills          # shared upstream skill submodule
├── llm-wiki                   # shared upstream skill submodule
└── config.yaml                # skill source mapping rules
```

## Install model

Run from `~/.llm-harness`:

```bash
./harness.py install
```

Installer behavior:

- discovers harnesses from `harness/`, `harness-paths.yaml`, and `config.yaml`
- maps harness homes by convention:
  - `agents` -> `~/.agents`
  - `claude` -> `~/.claude`
  - `codex` -> `~/.codex`
- reads `harness-paths.yaml` for non-obvious roots like OpenCode and custom Hermes skill installs
- reads `config.yaml` to symlink all configured skill sources (submodules and `local-skills/<harness>/`) directly under target `skills/`, preserving nested category paths
- symlinks non-skill top-level files and directories from `harness/<name>/` 1:1 into target harness home
- removes stale managed symlinks
- warns and skips when target path already exists and is not matching expected symlink

To remove managed symlinks later:

```bash
./harness.py uninstall
```

## Operations

For step-by-step recipes on adding skills, registering shared sources, moving skills between harnesses, and troubleshooting, see [docs/llm-harness-ops.md](docs/llm-harness-ops.md).

There is also a local skill, `llm-harness-ops`, that provides a guided workflow for managing this repository.

## Skill source sync

Shared skill sources live as git submodules:

- `obsidian-skills`
- `mattpocock-skills`
- `llm-wiki`

Update submodule pointers with:

```bash
./harness.py update-skills
```

Optional commit/push flow:

```bash
./harness.py update-skills --commit --push
```

Sync rules:

- `config.yaml` defines all skill sources under `sources:` with `type: submodule` or `type: local`
- `harness.py update-skills` updates pinned submodule commits only for sources with `type: submodule`, then refreshes managed skill symlinks in target harness homes and removes stale managed links
- `harness.py audit-skills` repairs safe wrong managed symlinks, verifies every effective configured skill resolves to its canonical source, and records the complete/blocked inventory in `state/skill-installation.json`
- `state/skill-routing-index.json` is the approval gate for discovered source skills: after the initial baseline, a new `SKILL.md` is withheld from every runtime harness until the routing cron has read it and approved the config-selected harness
- `config.yaml` remains the routing source of truth: source defaults route general skills, existing `overrides:` handle relative-path exceptions, and source-specific `routes:` entries record new Claude/Hermes/etc. exceptions
- `harness.py update-repo` runs the audit after its pull/update cycle and commits/pushes state changes, so newly discovered skills and corrected installs become durable repository state
- install-time mapping of skills to target harness homes is controlled by `config.yaml`
- later sources in `config.yaml` win on target-path collision

## User-owned skill data

`config.yaml` controls installation and routing only. Non-secret, user-owned settings
and durable agent artifacts live under `~/.agents/`:

- `~/.agents/config/skill-paths.json` — configured vault and artifact paths;
- `~/.agents/handoffs/`, `research/`, `reports/`, `learning/`, `writing/`, and
  `questionnaires/` — durable portable artifacts.

The tracked source for `skill-paths.json` is `harness/agents/config/`; the
installer exposes it at `~/.agents/config/skill-paths.json`. Do not store API
tokens, passwords, or other secrets there.

Audit declared prerequisites without mutating runtime state:

```bash
./harness.py audit-readiness
./harness.py audit-readiness --project /path/to/project
```

`audit-skills` verifies symlink installation; `audit-readiness` reports whether
declared paths, binaries, credentials, and per-project setup documents are ready.

## Notes

- canonical checkout path is `~/.llm-harness`
- all skill sources are configured in `config.yaml` and symlinked directly to target harness homes
- shared skill submodules install from `~/.llm-harness/<submodule>`
- local first-party skill sources live under `~/.llm-harness/local-skills/<harness>/`
- harness-specific non-skill files live under `~/.llm-harness/harness/<name>/`
- Hermes package-bundled skills stay in the Hermes install/source tree, not in `llm-harness`
- OpenCode will discover both `~/.agents/skills` and `~/.config/opencode/skills`
- Claude portable-skill auto-discovery is deferred for now
