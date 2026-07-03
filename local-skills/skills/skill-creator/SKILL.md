---
name: skill-creator
description: Universal guide for creating and maintaining skills in ~/.llm-harness. Use when the user wants to create a new skill, update an existing skill, package a skill, or move a skill between harnesses.
license: Complete terms in LICENSE.txt
---

# Skill Creator

This skill guides creation and maintenance of skills for any runtime that loads `SKILL.md` files.

## Start Here

Before creating or editing a skill, read `AGENTS.md` in `~/.llm-harness`. It contains rules that govern `~/.llm-harness`.

## About Skills

Skills are modular packages that extend an agent's capabilities with specialized knowledge, workflows, and tools. They act as onboarding guides for specific domains.

Skills provide:

1. Specialized workflows — multi-step procedures for specific domains
2. Tool integrations — instructions for file formats, APIs, or scripts
3. Domain expertise — project-specific knowledge and schemas
4. Bundled resources — scripts, references, and assets

### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter with name and description
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/          - Executable code
    ├── references/       - Documentation loaded on demand
    └── assets/           - Files used in output
```

## Repository Layout

All skills for this workspace must live in `~/.llm-harness`. Do not create skills outside `~/.llm-harness`.

Place skills according to scope:

- New first-party skills should live under `local-skills/skills/<skill-name>/` or `local-skills/skills/<category>/<skill-name>/`.
- The default target harness for `local-skills` is `agents`.
- If a skill should install to `claude`, `codex`, `hermes`, or `opencode`, keep the source under `local-skills/skills/...` and add an override under `local-skills:` in `config.yaml`.
- Use `harness/<name>/` only for non-skill harness-specific files such as `CLAUDE.md`, not as the primary source location for skills.

Source directories under `local-skills/` are discovered automatically by `harness.py install`. Submodules and harness-specific overrides are declared in `config.yaml`.

After editing, run:

```bash
cd ~/.llm-harness && ./harness.py install
```

Then verify with:

```bash
git status --short
```

For detailed recipes on adding skills, registering sources, moving skills, and troubleshooting, see `docs/llm-harness-ops.md`.

## Skill Creation Process

Follow these steps in order.

### Step 1: Understand the Skill with Concrete Examples

Skip only when usage patterns are already clear.

Ask focused questions:

- What functionality should the skill support?
- Can you give examples of how it would be used?
- What would a user say to trigger it?

### Step 2: Plan Reusable Contents

For each example, identify what scripts, references, or assets would help execute it repeatedly.

### Step 3: Initialize the Skill

Run the initializer from the skill-creator directory:

```bash
scripts/init_skill.py <skill-name> --path <output-directory>
```

This creates:

- Skill directory
- `SKILL.md` template with frontmatter
- Example `scripts/`, `references/`, and `assets/` directories

Delete any example files the skill does not need.

### Step 4: Edit the Skill

Focus on information beneficial to another agent instance. Include procedural knowledge, domain details, and reusable assets.

Write the skill in imperative/infinitive form, not second person. Use objective instructional language.

Answer in `SKILL.md`:

1. What is the purpose?
2. When should it be used?
3. How should the agent use it?

### Step 5: Validate and Package

Validate:

```bash
scripts/quick_validate.py <path/to/skill-folder>
```

Package:

```bash
scripts/package_skill.py <path/to/skill-folder> [output-directory]
```

Packaging runs validation first.

### Step 6: Register and Install

If the skill source is new and not under `local-skills/`, add it to `config.yaml` under the correct source with the right `harness` target. Override only when the skill is not portable.

Then run:

```bash
cd ~/.llm-harness && ./harness.py install
```

Verify with:

```bash
git status --short
```

### Step 7: Test and Iterate

Use the skill on real tasks, notice gaps, and refine `SKILL.md` or bundled resources.

## Maintenance

When updating an existing skill:

1. Edit source files in `~/.llm-harness`, not installed symlinks in harness homes.
2. Run `./harness.py install` to refresh symlinks.
3. Validate the skill.
4. Stage, commit, and push changes.

Follow `AGENTS.md` rules for every change: think before coding, simplicity first, surgical changes, goal-driven execution.

## Portability rules

Skills in this repository must remain host-agnostic. They may be cloned onto machines with different usernames, home directories, or hostnames.

- **Never** use absolute paths that contain a real username, hostname, or machine-specific directory such as `/Users/olisikh/`, `/home/alice/`, or machine names like `olisikh-mbair`.
- **Never** embed the canonical checkout path `/Users/<name>/.llm-harness` unless it is a generic placeholder like `/Users/<name>/.llm-harness` in explanatory text.
- When an absolute home path is needed in examples or commands, use `~/...` (e.g. `~/.llm-harness`, `~/.agents/skills/<skill-name>`).
- For paths inside this repository, use relative paths from the repo root (e.g. `local-skills/skills/<skill-name>/`).
- Scripts should resolve the repo root at runtime rather than hard-coding it.

Before finishing any skill edit, grep the skill directory for absolute `/Users/`, `/home/`, hostnames, or real usernames and replace them.

## Quality

For principles on writing tight, predictable skills, consult `writing-great-skills`. Use it only to improve quality; it does not replace this creation workflow.
