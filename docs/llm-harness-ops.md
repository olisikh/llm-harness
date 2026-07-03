---
title: LLM Harness Operations Guide
summary: How to add, move, register, and configure skills and harness homes in ~/.llm-harness.
tags:
  - llm-harness
  - operations
  - skills
  - onboarding
created: 2026-07-03
updated: 2026-07-03
confidence: high
---

# LLM Harness Operations Guide

This document is the canonical reference for changing the shape of the `llm-harness` repository. Read it before adding skills, registering new shared sources, or changing harness mappings.

## What this repo does

`llm-harness` is a single source of truth for LLM harness homes (`~/.agents`, `~/.claude`, `~/.codex`, etc.) across machines. It does two things:

1. **Symlinks skill sources** into target harness `skills/` directories.
2. **Symlinks harness-specific home files** (e.g. `CLAUDE.md`) into target harness homes.

Skill sources are declared in `config.yaml`. They can be:

- `type: submodule` — shared upstream skill repositories tracked as git submodules.
- `type: local` — first-party skills that live inside this repo, under `local-skills/`.

The repo does **not** copy skill files around. It creates symlinks from the target harness home directly to the source directory. This keeps the repo portable and avoids machine-specific paths in tracked files.

## Repository layout

```text
llm-harness/
├── AGENTS.md                  # contributor rules (link to this doc)
├── config.yaml                # all skill source mappings
├── harness-paths.yaml         # non-obvious harness root overrides
├── harness/                   # harness-specific home files only
│   ├── agents/
│   ├── claude/
│   │   └── CLAUDE.md
│   ├── codex/
│   ├── hermes/
│   └── opencode/
├── local-skills/              # local first-party skill sources
│   └── skills/
├── docs/
│   └── llm-harness-ops.md     # this file
├── harness.py                 # create/update/remove target symlinks and update submodules
├── obsidian-skills            # shared submodule
├── mattpocock-skills          # shared submodule
└── llm-wiki                   # shared submodule
```

Never put skill directories under `harness/<name>/skills/`. That location is deprecated; skills now live in configured sources.

Harness directories under `harness/` are optional. The install/uninstall logic discovers active harnesses from `harness-paths.yaml` keys and from every `harness` value referenced in `config.yaml`, so a harness with only skills still gets processed even if its `harness/<name>/` directory does not exist.

## Core concepts

### Source

A source is a top-level key under `sources:` in `config.yaml`. It points at a directory inside the repo. Example source names:

- `obsidian-skills` — a git submodule directory.
- `local-skills` — a local directory inside the repo.

### Type

- `type: submodule` — `./harness.py update-skills` will fetch and update the pinned commit. `./harness.py install` symlinks skills from `repo/<source-name>/<root>`.
- `type: local` — `./harness.py update-skills` ignores it. `./harness.py install` symlinks skills from `repo/<source-name>/<root>`.

### Root

The `root` value is the subdirectory inside the source that contains skill directories. For most sources it is `skills`. For `llm-wiki` it differs per child source.

### Harness

The default target harness for every skill under the source. Values are keys known to `harness-paths.yaml` and the built-in defaults:

- `agents` -> `~/.agents`
- `claude` -> `~/.claude`
- `codex` -> `~/.codex`
- `hermes` -> `~/.hermes` (via `harness-paths.yaml`)
- `opencode` -> `~/.config/opencode` (via `harness-paths.yaml`)

### Override

A per-skill mapping from its relative path inside `root` to a different harness. Overrides are evaluated after the default `harness`.

### Nested category paths

Skill directories may be nested, e.g. `mattpocock-skills/skills/engineering/ask-matt`. The relative path inside `root` is preserved when symlinking into the target harness. The above skill becomes `~/.agents/skills/engineering/ask-matt`. Category folders provide extra semantic context for LLM discovery.

## Configuration files

### `config.yaml`

Declares every skill source. Order matters: later sources win if two sources produce the same target path.

```yaml
---
sources:
  obsidian-skills:
    type: submodule
    root: skills
    harness: agents

  mattpocock-skills:
    type: submodule
    root: skills
    harness: agents
    overrides:
      misc/git-guardrails-claude-code: claude

  llm-wiki:
    type: submodule
    sources:
      - root: claude-plugin/skills
        harness: claude
      - root: plugins/llm-wiki-opencode/skills
        harness: opencode
      - root: plugins/llm-wiki/skills
        harness: codex

  local-skills:
    type: local
    root: skills
    harness: agents
    overrides:
      algorithmic-art: claude
      compress: claude
      skill-creator: claude
      limits: codex
      autonomous-ai-agents/llm-harness-ops: hermes
```

A source may have either:

- a single `root` + `harness` at the top level, or
- a `sources:` list of child sources (used when one submodule hosts skills for multiple harnesses).

### `harness-paths.yaml`

Maps harness names to install roots that do not follow the default `~/.<name>` convention.

```yaml
---
harness:
  hermes: ~/.hermes
  opencode: ~/.config/opencode
```

Only add entries here for harnesses that do not use the default path.

## Recipes

### Add a new local skill

Use this when the skill is private, experimental, or specific to your setup.

1. Choose a target harness and category.
   - Default is `agents`. Use overrides for other harnesses.
2. Create the skill directory under `local-skills/skills/`.
   - Flat: `local-skills/skills/my-skill/SKILL.md`
   - Nested: `local-skills/skills/category/my-skill/SKILL.md`
3. If the skill is not for `agents`, add an override to `config.yaml` under `local-skills:`.
4. Run `./harness.py install`.
5. Verify the symlink in the target harness `skills/` directory.

Example: add a Claude-only skill called `my-claude-skill`.

```bash
mkdir -p local-skills/skills/my-claude-skill
cat > local-skills/skills/my-claude-skill/SKILL.md <<'EOF'
---
name: my-claude-skill
description: A custom Claude skill.
---
# my-claude-skill
EOF
```

Edit `config.yaml`:

```yaml
  local-skills:
    type: local
    root: skills
    harness: agents
    overrides:
      # ... existing overrides ...
      my-claude-skill: claude
```

Run:

```bash
./harness.py install
ls -la ~/.claude/skills/my-claude-skill
```

### Add a new shared skill submodule

Use this when skills live in an external repository you want to track.

1. Add the repository as a git submodule at `~/.llm-harness`.
2. Add a `sources:` entry in `config.yaml` with `type: submodule`.
3. Set `root` and default `harness`.
4. Add overrides for any skills that belong to a different harness.
5. Run `./harness.py update-skills <source-name>` to initialize and pin the submodule.
6. Run `./harness.py install` to create target symlinks.

Example: add a new submodule `acme-skills`.

```bash
git submodule add https://github.com/example/acme-skills.git acme-skills
```

Edit `config.yaml`:

```yaml
  acme-skills:
    type: submodule
    root: skills
    harness: agents
    overrides:
      claude-only/acme-helper: claude
```

Run:

```bash
./harness.py update-skills acme-skills
./harness.py install
```

### Deprecate skills or a category

To stop installing a skill, add its relative path under the source's `exclude:` list. To exclude an entire category folder, end the entry with `/`.

Example: exclude all skills under `mattpocock-skills/skills/deprecated/`.

```yaml
  mattpocock-skills:
    type: submodule
    root: skills
    harness: agents
    exclude:
      - deprecated/
```

To deprecate a single skill, use its full relative path without a trailing slash:

```yaml
    exclude:
      - deprecated/skill-name
```

Then run `./harness.py install`. Existing target symlinks for excluded skills will be removed automatically.

### Move a skill to another harness

If the skill is in a shared submodule, add or change an override in `config.yaml`. If the skill is local, move its directory under `local-skills/skills/` and update the override.

Example: move `local-skills/skills/old-agents-skill` to Claude.

```yaml
  local-skills:
    # ...
    overrides:
      old-agents-skill: claude
```

Then run `./harness.py install`. The old symlink in `~/.agents/skills/old-agents-skill` will be removed and a new one created at `~/.claude/skills/old-agents-skill`.

### Add a new harness

1. Create a directory under `harness/` with the harness name.
2. Add any harness-specific files (e.g. `CLAUDE.md` for Claude).
3. If the default install path `~/.<name>` is wrong, add an entry to `harness-paths.yaml`.
4. Reference the harness in `config.yaml` overrides or source `harness` values.
5. Run `./harness.py install`.

Example: add `gemini` harness targeting `~/.gemini`.

```bash
mkdir -p harness/gemini
cat > harness/gemini/README.md <<'EOF'
# Gemini harness notes
EOF
```

Edit `harness-paths.yaml`:

```yaml
harness:
  gemini: ~/.gemini
```

Then add skills for it in `config.yaml`.

### Add a new harness root path

If a harness home lives somewhere other than `~/.<name>`, add it to `harness-paths.yaml`. Do not hard-code unusual paths in `harness.py install`.

```yaml
harness:
  opencode: ~/.config/opencode
  gemini: ~/custom/gemini/home
```

### Remove a skill

1. Delete the skill source directory (or remove its override if it is excluded from install).
2. Run `./harness.py install`. Stale target symlinks will be removed automatically.

For shared submodule skills you no longer want at all, also remove the override or source entry from `config.yaml`.

## Scripts reference

The single entrypoint is `harness.py`.

### `harness.py install`

Idempotent. Discovers harnesses from `harness/`, `harness-paths.yaml`, and `config.yaml`; creates symlinks; removes stale managed symlinks.

```bash
./harness.py install
```

Safe to run repeatedly. It warns and skips when a target path already exists and is not the expected symlink.

### `harness.py uninstall`

Removes all symlinks managed by `~/.llm-harness`. For skill directories it removes any symlink under `~/.<harness>/skills/` that resolves into `~/.llm-harness`. For non-skill harness entries it removes symlinks that point to the matching source in `harness/`.

```bash
./harness.py uninstall
```

### `harness.py update-skills`

Updates pinned commits for every source with `type: submodule` in `config.yaml`. Skips sources with `type: local`. Skips submodules that have uncommitted local changes.

```bash
./harness.py update-skills              # update all configured submodules
./harness.py update-skills obsidian-skills
./harness.py update-skills --commit --push
```

### `harness.py update-repo`

Pulls the latest `llm-harness` repo, runs `update-skills --commit --push`, then runs `install`. Intended for cron or periodic automation.

```bash
./harness.py update-repo
```

## Troubleshooting

### `harness.py install` skips a skill with "Skipping existing path"

A real file or directory already exists at the target path. Decide whether to back it up and remove it, or rename your skill.

### `harness.py install` skips a skill with "Skipping existing symlink (points elsewhere)"

The target is already a symlink to a path outside this repo. Back it up or remove it manually, then re-run `./harness.py install`.

### A skill appears under the wrong harness

Check `config.yaml`:

- Is the source's default `harness` correct?
- Is there an `overrides:` entry for the skill's relative path?
- If two sources define the same target path, the later source in `config.yaml` wins.

### `harness.py update-skills` says a submodule is not configured

Only sources with `type: submodule` in `config.yaml` are updated. If a submodule is new, add it to `config.yaml` first.

### Machine-specific symlink targets appear in git status

This means an intermediate symlink inside the repo is still tracked. Skills must never be symlinked inside `harness/<name>/skills/`; they must be real directories or live in configured sources. If you see a tracked symlink under `harness/`, remove it and rely on `./harness.py install` to create the target-home symlink directly.

