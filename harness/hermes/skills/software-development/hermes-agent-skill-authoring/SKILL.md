---
name: hermes-agent-skill-authoring
description: "Author in-repo SKILL.md: frontmatter, validator, structure."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, authoring, hermes-agent, conventions, skill-md]
    related_skills: [writing-plans, requesting-code-review]
---

# Authoring Hermes-Agent Skills (in-repo)

## Overview

There are three places a SKILL.md can live:

1. **User-local runtime path:** `~/.hermes/skills/<maybe-category>/<name>/SKILL.md` — personal, not shared, and not the preferred durable source on Oleksii's machine. `skill_manage(action='create')` writes here.
2. **Shared harness-managed repo (default on Oleksii's machine):** `~/llm-harness/harness/<harness>/skills/.../SKILL.md` — committed in the central skills repo, then installed into harness homes with `cd ~/llm-harness && ./install.sh`. This is the right home for durable skills.
3. **Hermes source tree:** `/home/bb/hermes-agent/skills/<category>/<name>/SKILL.md` — committed and shipped with the hermes-agent package itself.

## When to Use

- User asks you to add or maintain a durable skill in the shared repo
- User asks you to add a skill "in this branch / repo / commit"
- You're committing a reusable workflow that should ship with hermes-agent
- You're editing an existing skill under `~/llm-harness/harness/.../skills/` or `/home/bb/hermes-agent/skills/` (use `patch` for small edits, `write_file` for rewrites; `skill_manage` still works for patch on in-repo skills, but not for `create`)

## Required Frontmatter

Source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:

- Starts with `---` as the first bytes (no leading blank line).
- Closes with `\n---\n` before the body.
- Parses as a YAML mapping.
- `name` field present.
- `description` field present, ≤ **1024 chars** (`MAX_DESCRIPTION_LENGTH`).
- Non-empty body after the closing `---`.

Peer-matched shape used by every skill under `skills/software-development/`:

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars (MAX_NAME_LENGTH)
description: Use when <trigger>. <one-line behavior>.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

`version` / `author` / `license` / `metadata` are NOT enforced by the validator, but every peer has them — omit and your skill sticks out.

## Size Limits

- Description: ≤ 1024 chars (enforced).
- Full SKILL.md: ≤ 100,000 chars (enforced as `MAX_SKILL_CONTENT_CHARS`, ~36k tokens).
- Peer skills in `software-development/` sit at **8-14k chars**. Aim for that range. If you're pushing past 20k, split into `references/*.md` and reference them from SKILL.md.

## Peer-Matched Structure

Every in-repo skill follows roughly:

```
# <Title>

## Overview
One or two paragraphs: what and why.

## When to Use
- Bulleted triggers
- "Don't use for:" counter-triggers

## <Topic sections specific to the skill>
- Quick-reference tables are common
- Code blocks with exact commands
- Hermes-specific recipes (tests via scripts/run_tests.sh, ui-tui paths, etc.)

## Common Pitfalls
Numbered list of mistakes and their fixes.

## Verification Checklist
- [ ] Checkbox list of post-action verifications

## One-Shot Recipes (optional)
Named scenarios → concrete command sequences.
```

Not every section is mandatory, but `Overview` + `When to Use` + actionable body + pitfalls are the minimum for the skill to feel like a peer.

## Directory Placement

```
# shared harness-managed skills on Oleksii's machine
harness/<harness>/skills/<skill-name>/SKILL.md
harness/hermes/skills/<category>/<skill-name>/SKILL.md   # Hermes keeps category folders

# hermes-agent source-tree skills
skills/<category>/<skill-name>/SKILL.md
```

Repository root is the *repo root*, not necessarily the `skills/` directory itself. On Oleksii's setup the central skill repo lives at `~/llm-harness`, with durable skill sources under `~/llm-harness/harness/<harness>/skills`. Installed runtime views such as `~/.agents/skills` and `~/.hermes/skills` are not the preferred edit locations. Before moving or creating skills, confirm the actual git root with `git rev-parse --show-toplevel`.

Categories currently in repo (confirm with `ls skills/`): `autonomous-ai-agents`, `creative`, `data-science`, `devops`, `dogfood`, `email`, `gaming`, `github`, `leisure`, `mcp`, `media`, `mlops/*`, `note-taking`, `productivity`, `red-teaming`, `research`, `smart-home`, `social-media`, `software-development`.

Pick the closest existing category. Don't invent new top-level categories casually.

## Workflow

When the task is about **shared-skill cleanup / migration / deduplication** on Oleksii's setup, follow this operating rule first:

- Canonical physical skill source lives under `~/llm-harness/harness/<harness>/skills`.
- Installed runtime trees such as `~/.agents/skills` and `~/.hermes/skills` are install targets, compatibility bridges, or stale residue — not the preferred source of truth.
- Do **not** create timestamped backup/archive skill trees as a safety blanket when cleaning up duplicates; rely on git history in the canonical repo instead.
- After merging useful content into the canonical shared skill, delete duplicate/import/archive copies from installed runtime trees rather than leaving clutter behind.
- Avoid cross-tree symlinks except as explicit compatibility bridges managed by `~/llm-harness/install.sh`.
- See `references/shared-skill-dedup-and-cleanup.md` for the cleanup pattern.
- For missing/mislinked shared skills in `~/llm-harness`, inspect `skills-config.yaml` excludes and local-shadow rules before assuming `scripts/update-skills.sh` is broken; see `references/shared-skill-sync-diagnosis.md`.
- When the user wants `~/llm-harness` to stop excluding any Matt Pocock skills and sync the full upstream tree, remove the `mattpocock-skills.skillsExclude` block, update `AGENTS.md` shadow-policy text to match, then rerun `scripts/update-skills.sh`; see `references/shared-skill-full-matt-sync.md`.
- If `~/llm-harness` has local edits and the user asks to pull first, prefer `git pull --rebase --autostash` over stopping at a failed plain pull, as long as no destructive conflict resolution is needed.

1. **Survey peers** in the target category:

   ```
   ls skills/<category>/
   ```
   Read 2-3 peer SKILL.md files to match tone and structure.
2. **Check validator constraints** in `tools/skill_manager_tool.py` if unsure.
3. **Choose the correct repo path** for the target harness, then draft with `write_file`. On Oleksii's machine that is usually under `~/llm-harness/harness/<harness>/skills/...`.
4. **Validate locally**:
   ```python
   import yaml, re, pathlib
   content = pathlib.Path("<path/to/SKILL.md>").read_text()
   assert content.startswith("---")
   m = re.search(r'\n---\s*\n', content[3:])
   fm = yaml.safe_load(content[3:m.start()+3])
   assert "name" in fm and "description" in fm
   assert len(fm["description"]) <= 1024
   assert len(content) <= 100_000
   ```
5. **Run `cd ~/llm-harness && ./install.sh`** after shared-repo edits so installed harness homes pick up the new symlinks or moved paths.
6. **Git add + commit** on the active branch.
7. **If promoting a user-local skill into the shared repo**, follow `references/skill-promotion-to-shared-repo.md` for the copy/commit/push/install pattern.
8. **Note:** the CURRENT session's skill loader is cached — `skill_view` / `skills_list` will not see the new skill until a new session. This is expected, not a bug.

## Cross-Referencing Other Skills

`metadata.hermes.related_skills` unions both trees (`skills/` in-repo and `~/.hermes/skills/`) at load time. You CAN reference a user-local skill from an in-repo skill, but it won't resolve for other users who clone the repo fresh. Prefer referencing only in-repo skills from in-repo skills. If a frequently-referenced skill lives only in `~/.hermes/skills/`, consider promoting it to the repo.

## Editing Existing In-Repo Skills

- **Small fix (typo, added pitfall, tightened trigger):** `skill_manage(action='patch', name=..., old_string=..., new_string=...)` works fine on in-repo skills.
- **Major rewrite:** `write_file` the whole SKILL.md. `skill_manage(action='edit')` also works but requires supplying the full new content.
- **Adding supporting files:** `write_file` to `skills/<category>/<name>/references/<file>.md`, `templates/<file>`, or `scripts/<file>`. `skill_manage(action='write_file')` also works and enforces the references/templates/scripts/assets subdir allowlist.
- **Always commit** the edit — in-repo skills are source, not runtime state.

## Common Pitfalls

1. **Using `skill_manage(action='create')` for a shared repo-managed skill.** It writes to `~/.hermes/skills/`, not the canonical repo tree. Use `write_file` for shared skill creation, then run `~/llm-harness/install.sh`.

2. **Leading whitespace before `---`.** The validator checks `content.startswith("---")`; any leading blank line or BOM fails validation.

3. **Description too generic.** Peer descriptions start with "Use when ..." and describe the *trigger class*, not the one task. "Use when debugging X" > "Debug X".

4. **Forgetting the author/license/metadata block.** Not validator-enforced, but every peer has it; omitting makes the skill look half-finished.

5. **Writing a skill that duplicates a peer.** Before creating, `ls skills/<category>/` and open 2-3 peers. Prefer extending an existing skill to creating a narrow sibling.

6. **Expecting the current session to see the new skill.** It won't. The skill loader is initialized at session start. Verify in a fresh session or via `skill_view` using the exact path.

7. **Linking to skills that don't exist in-repo.** `related_skills: [some-user-local-skill]` works for you but breaks for other clones. Prefer only in-repo links.

8. **Creating backup/archive trees during cleanup.** On Oleksii's setup, this is usually the wrong safety mechanism. Prefer git history in the canonical `~/llm-harness` repo, merge any useful content, then delete duplicate/import/archive copies from installed runtime trees instead of leaving `*.backup.*`, `.archive`, or import-dump trees behind.

9. **Leaving duplicated shared skills in both trees.** If a shared/user skill has been merged into `~/llm-harness`, remove redundant runtime copies rather than keeping two editable versions. Runtime compatibility bridges are the exception, not the default.

## Verification Checklist

- [ ] File is in the canonical repo path for the target harness (for Oleksii, usually under `~/llm-harness/harness/<harness>/skills/...`, not directly in `~/.hermes/skills/`)
- [ ] Frontmatter starts at byte 0 with `---`, closes with `\n---\n`
- [ ] `name`, `description`, `version`, `author`, `license`, `metadata.hermes.{tags, related_skills}` all present
- [ ] Name ≤ 64 chars, lowercase + hyphens
- [ ] Description ≤ 1024 chars and starts with "Use when ..."
- [ ] Total file ≤ 100,000 chars (aim for 8-15k)
- [ ] Structure: `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist`
- [ ] `related_skills` references resolve in-repo (or are explicitly OK to be user-local)
- [ ] `~/llm-harness/install.sh` ran after shared-repo changes
- [ ] `git add` + `git commit` completed on the intended branch
