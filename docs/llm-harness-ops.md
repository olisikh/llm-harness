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
- `type: local` — first-party skills that live inside this repo, under `local-skills/<harness>/`.

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
│   ├── agents/                # portable skills
│   ├── claude/                # Claude-only skills
│   ├── codex/                 # Codex-only skills
│   └── hermes/                # Hermes-only skills
├── docs/
│   └── llm-harness-ops.md     # this file
├── harness.py                 # create/update/remove target symlinks and update submodules
├── obsidian-skills          # shared submodule
├── mattpocock-skills        # shared submodule
├── llm-wiki                 # shared submodule
└── awesome-llm-skills       # shared submodule
```

Never put skill directories under `harness/<name>/skills/`. That location is deprecated; skills now live in configured sources.

Harness directories under `harness/` are optional. The install/uninstall logic discovers active harnesses from `harness-paths.yaml` keys and from every `harness` value referenced in `config.yaml`, so a harness with only skills still gets processed even if its `harness/<name>/` directory does not exist.

## Core concepts

### Source

A source is a top-level key under `sources:` in `config.yaml`. It points at a directory inside the repo. Example source names:

- `obsidian-skills` — a git submodule directory.
- `local-skills/agents` — a local directory inside the repo targeting the `agents` harness.

### Type

- `type: submodule` — `./harness.py update-skills` will fetch and update the pinned commit, then refresh managed skill symlinks. `./harness.py install` can also refresh skills from `repo/<source-name>/<root>`.
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

### Claude mirrors

Claude Code discovers skills only as directories directly under its `skills/`
directory. To expose portable `agents` skills to Claude, configure a flat mirror:

```yaml
skill_mirrors:
  claude:
    from: agents
    flatten: true
```

`harness.py install` creates managed symlinks at `~/.claude/skills/<skill-name>`
only when `~/.claude` already exists. Direct Claude routes win on duplicate names,
and mirrored skills inherit the source skill's routing-index approval.

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

  local-skills/agents:
    type: local
    root: .
    harness: agents

  local-skills/claude:
    type: local
    root: .
    harness: claude

  local-skills/codex:
    type: local
    root: .
    harness: codex

  local-skills/hermes:
    type: local
    root: .
    harness: hermes
```

A source may have either:

- a single `root` + `harness` at the top level, or
- a `sources:` list of child sources (used when one submodule hosts skills for multiple harnesses or needs different roots).

### Source entry anatomy

Every source entry under `sources:` shares a common shape. Fields at the top level apply to the whole entry; some can also be specified per child source when using `sources:`.

- `type`: either `submodule` or `local`.
  - `submodule`: tracked as a git submodule; updated by `./harness.py update-skills`.
  - `local`: a plain directory inside the repo; ignored by `update-skills`.
- `root`: the subdirectory inside the source directory where skill directories live. The installer walks this root and creates a symlink for every directory that contains a `SKILL.md`.
- `harness`: the default target harness for every skill found under `root`.
- `sources`: optional list of child sources. Use this when one submodule needs different roots or default harnesses. Top-level `root`/`harness` are ignored when `sources:` is present.
- `exclude`: list of relative paths under `root` (or under each child source) to skip. End a folder name with `/` to exclude the whole subtree. Use without `/` to exclude a single skill.
- `overrides`: map from a skill's relative path under `root` to a different harness. Evaluated after the default `harness`.

### Explicit artifacts

Use `artifacts:` when an upstream repository ships files, directories, or paths that
do not follow the standard directory-with-`SKILL.md` layout. Each artifact is one
exact source-to-target symlink; both files and directories are supported. This avoids
running upstream installer scripts while keeping every filename explicit.

```yaml
  graphify:
    type: submodule
    artifacts:
      - from: graphify/skill-opencode.md
        harness: opencode
        to: skills/graphify/SKILL.md
      - from: graphify/skills/opencode/references
        harness: opencode
        to: skills/graphify/references
```

`from` is relative to the source directory, `to` is relative to the harness home,
and paths are case-sensitive by convention. Artifacts participate in source-order
collision handling and routing approval like discovered skills.

Order matters: later sources in `config.yaml` win if two sources produce the same target path.

### Flattening a nested skill group

Some submodules group related skills under an extra directory level. For example, `awesome-llm-skills` keeps document skills under `document-skills/docx`, `document-skills/pdf`, etc. If you used a single source with `root: .`, the installer would create:

```text
~/.agents/skills/document-skills/docx
~/.agents/skills/document-skills/pdf
...
```

To install them at the top level of `~/.agents/skills/` instead, use two child sources and an `exclude:`:

```yaml
  awesome-llm-skills:
    type: submodule
    exclude:
      - document-skills/
    overrides:
      algorithmic-art: claude
    sources:
      - root: .
        harness: agents
      - root: document-skills
        harness: agents
```

How it works:

1. The first source walks the top level and installs every skill directly under `~/.agents/skills/`.
2. `exclude: [document-skills/]` tells the first source not to recurse into `document-skills/`, so it does not create `~/.agents/skills/document-skills/...`.
3. The second source walks only `document-skills/` and installs each skill directly under `~/.agents/skills/`, producing `~/.agents/skills/docx`, `~/.agents/skills/pdf`, etc.
4. `overrides` routes `algorithmic-art` to the `claude` harness instead of the default `agents`.

This pattern generalizes to any submodule that mixes flat top-level skills with grouped nested skills.

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
2. Create the skill directory under `local-skills/<harness>/`.
   - Flat: `local-skills/agents/my-skill/SKILL.md`
   - Nested: `local-skills/hermes/category/my-skill/SKILL.md`
3. Run `./harness.py install`.
4. Verify the symlink in the target harness `skills/` directory.

Example: add a Claude-only skill called `my-claude-skill`.

```bash
mkdir -p local-skills/claude/my-claude-skill
cat > local-skills/claude/my-claude-skill/SKILL.md <<'EOF'
---
name: my-claude-skill
description: A custom Claude skill.
---
# my-claude-skill
EOF
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
5. Run `./harness.py update-skills <source-name>` to initialize and pin the submodule, refresh target symlinks, and remove stale managed links.

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
```

If the submodule groups some skills under an extra directory level (for example `document-skills/docx`), use the flattening pattern described in [Flattening a nested skill group](#flattening-a-nested-skill-group) above.

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

If the skill is in a shared submodule, add or change an override in `config.yaml`. If the skill is local, move its directory from `local-skills/<old-harness>/` to `local-skills/<new-harness>/`.

Example: move `local-skills/agents/old-agents-skill` to Claude.

```bash
mv local-skills/agents/old-agents-skill local-skills/claude/
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

Updates pinned commits for every source with `type: submodule` in `config.yaml`. Skips sources with `type: local` and submodules with uncommitted local changes. It then refreshes all managed harness links and removes stale managed skill symlinks; unrelated files and symlinks outside `~/.llm-harness` are preserved.

```bash
./harness.py update-skills              # update all configured submodules
./harness.py update-skills obsidian-skills
./harness.py update-skills --commit --push
```

### Routing newly discovered skills

`config.yaml` is the routing authority. Each source has a default `harness` for general-use skills; existing `overrides:` remain available for relative-path exceptions; use top-level `routes:` for a source-specific exception when the same source can expose skills through multiple roots.

The tracked `state/skill-routing-index.json` is an approval gate, not a second routing authority. It records the source path, config-selected harness, and target path for every reviewed skill. Once the baseline exists, `harness.py install`, `update-skills`, and `update-repo` install only skills whose index entry exactly matches the current `config.yaml` route. A new upstream `SKILL.md` is discovered but withheld from all harness homes until reviewed.

```bash
./harness.py routing-candidates --json
# Read each candidate's SKILL.md and, if needed, add a source-specific route to config.yaml.
./harness.py approve-skill --source source/path/to/skill --harness hermes
./harness.py audit-skills
```

Use `seed-routing-index` only to establish a deliberate baseline for a repository that predates the gate:

```bash
./harness.py seed-routing-index
```

The daily Hermes routing cron runs the source update first, reads each withheld candidate, classifies it, updates `config.yaml` for non-default routing, approves it, and then audits the resulting installation. It must keep package-bundled Hermes skills outside this index and never infer a route merely from a name: classify from the skill's actual instructions and dependencies.

### Runtime readiness

Installation state answers whether a skill symlink is correct; it cannot prove that
an installed skill has its configured vault, credential, binary, or project setup.
`state/skill-readiness.yaml` is the tracked readiness matrix for the material
prerequisites discovered during skill review. It supports:

- global checks for user-owned paths, runtime commands, and environment-variable
  presence;
- optional checks that report unavailable integrations without failing the audit;
- project checks for files such as Matt Pocock's `docs/agents/*.md`.

Run the read-only audit after installing or changing user configuration:

```bash
./harness.py audit-readiness
./harness.py audit-readiness --project /absolute/path/to/project
```

The non-secret shared path configuration is installed at
`~/.agents/config/skill-paths.json` from `harness/agents/config/skill-paths.json`.
Use `~/.agents` for durable agent artifacts; keep secrets in the relevant runtime
or provider store.

### `harness.py audit-skills`

Repairs an incorrect skill symlink only when its current target is already inside `~/.llm-harness`; external symlinks and real paths remain protected and are reported as blocked. It then verifies every **effective** configured target (after source-order collision handling) resolves to the canonical source and writes the portable inventory at `state/skill-installation.json`.

The state uses harness names and repo-relative source paths, never machine-specific absolute paths. New configured skills are reported once when first added to the state; removed skills are reported when their state entry disappears. Only exact installs are marked `complete`; protected conflicts remain `blocked` and make the command exit non-zero.

```bash
./harness.py audit-skills
```

### `harness.py update-repo`

Pulls the latest `llm-harness` repo, updates shared submodules, and runs `audit-skills`. When the audit inventory changes, it commits and pushes `state/skill-installation.json` as `chore: audit skill installations`. This is the maintenance command used by the Hermes cron wrapper at `~/.hermes/scripts/update-llm-harness.sh`.

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
