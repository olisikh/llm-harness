---
name: llm-harness-ops
description: >
  Manage the llm-harness repository: add, move, register, and configure skills
  and harness homes. Canonical reference lives in docs/llm-harness-ops.md.
---

# llm-harness-ops

Use this skill when the user wants to:

- Add a new skill to the llm-harness repository.
- Register a new shared skill submodule source.
- Move a skill between harnesses or categories.
- Add or change a harness mapping.
- Understand how install, uninstall, or update-skills work.
- Fix symlink problems in harness homes.

Always prefer the canonical operational guide:

[docs/llm-harness-ops.md](../docs/llm-harness-ops.md)

## Quick facts

- `llm-harness` symlinks skills directly from configured sources into `~/.<harness>/skills/`.
- Skill sources are declared in `config.yaml` under `sources:`.
- A source has `type: submodule` (git submodule, updated by `update-skills.sh`) or `type: local` (directory in this repo, ignored by `update-skills.sh`).
- Default harness mappings live in `harness-paths.yaml` or built-in defaults.
- Nested category paths inside a source are preserved when symlinking.
- Later sources in `config.yaml` win on target-path collision.

## Workflows

### Add a local skill

1. Ask the user: target harness, category (optional), skill name.
2. Create `local-skills/skills/<category>/<skill-name>/SKILL.md`.
3. If target harness is not `agents`, add an override to `config.yaml` under `local-skills:`.
4. Run `./install.sh`.
5. Verify with `ls -la ~/.<harness>/skills/<category>/<skill-name>`.

### Register a shared skill submodule

1. Ask the user: repository URL, source name, default harness, root (usually `skills`).
2. Run `git submodule add <url> <source-name>`.
3. Add a `sources:` entry in `config.yaml` with `type: submodule`.
4. Add overrides for any skills that go to a different harness.
5. Run `./scripts/update-skills.sh <source-name>`.
6. Run `./install.sh`.

### Move a skill

1. If local: move the directory under `local-skills/skills/` if needed.
2. Update the override in `config.yaml` for the skill's relative path.
3. Run `./install.sh`.

### Add or change a harness path

1. Edit `harness-paths.yaml`.
2. Run `./install.sh`.

## Verification checklist

After any structural change:

1. `python3 -m py_compile harness.py llm_harness/*.py`
2. `./harness.py update-skills [submodule...]`
3. `./harness.py install`
4. `./harness.py uninstall`
5. `git status --short`

## Templates

### Local skill SKILL.md

```markdown
---
name: <skill-name>
description: <one-line description>
---

# <skill-name>

<What this skill does and when to use it.>
```

### New shared source in config.yaml

```yaml
  <source-name>:
    type: submodule
    root: skills
    harness: <default-harness>
    overrides:
      <category>/<skill-name>: <other-harness>
```

## What not to do

- Do not put skills under `harness/<name>/skills/`.
- Do not track symlinks inside `harness/`.
- Do not edit files inside submodules directly unless you intend to fork them.
- Do not run `install.sh` without first checking for existing real files at target paths.
