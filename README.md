# .agents

This repository contains my reusable AI agent setup.

It has two main parts:

- `skills/`: reusable `SKILL.md`-based skills for Claude Code, OpenCode, and other agent tools
- `AGENTS.md`: shared behavioral instructions for coding agents, based on a concise Andrej Karpathy-style `CLAUDE.md` pattern

## Repository Layout

```text
.agents/
├── AGENTS.md
├── README.md
├── install.sh
├── uninstall.sh
└── skills/
```

## What `install.sh` Does

Run from the repository root:

```bash
./install.sh
```

It sets up Claude-specific symlinks:

- `~/.claude/skills` -> `~/.agents/skills`
- `~/.claude/CLAUDE.md` -> `~/.agents/AGENTS.md`

Because this repository already lives at `~/.agents`, there is no separate `~/.agents/skills` symlink step.

To remove those symlinks:

```bash
./uninstall.sh
```

## Updating Shared Skill Repos

The shared skill sources live as git submodules:

- `obsidian-skills`
- `mattpocock-skills`

Shared-skill sync metadata lives in `skills-sync.yaml`:

- `skillsRoot`: folder inside submodule to scan for skills
- `skillsDest`: destination root in this repo
- `skillsExclude`: optional relative skill paths to skip

`./scripts/update-skills.sh` symlinks every directory under `skillsRoot` that contains `SKILL.md`, preserving its relative path under `skillsDest`.

To update their pinned commits from upstream and resync managed symlinks in `skills/`:

```bash
./scripts/update-skills.sh
```

To also commit and push the updated submodule pointers:

```bash
./scripts/update-skills.sh --commit --push
```

You can also limit it to specific submodules:

```bash
./scripts/update-skills.sh obsidian-skills mattpocock-skills
```

## How To Use

- Add new reusable skills under `skills/<skill-name>/`
- Put the main instructions for each skill in `skills/<skill-name>/SKILL.md`
- Keep helper files for a skill inside that same folder
- Update `skills/README.md` if you want the skill catalog and platform notes to stay documented

For the full skill catalog, setup notes, and platform-specific usage details, see [`skills/README.md`](./skills/README.md).

## Notes

- `AGENTS.md` is the canonical source for agent behavior in this repo
- Claude receives that file through `~/.claude/CLAUDE.md`
- Other tools can read from this repository directly, especially from `~/.agents/skills`
