---
name: obsidian-vault
description: Search, create, and organize notes in Oleksii's configured Obsidian vault. Use when the user asks to find, create, or organize notes in Obsidian.
---

# Obsidian Vault

## Vault location

Resolve the canonical vault path before any operation:

```bash
python3 ~/.llm-harness/scripts/skill-path.py path obsidian_vault
```

The setting is stored in `~/.agents/config/skill-paths.json`. Current configured value is `~/notes`. Do not use the obsolete WSL path from the upstream skill.

If the resolved path is missing, stop and report the configuration problem. Never create a replacement vault automatically.

## Conventions

- Keep note names in Title Case.
- Prefer wikilinks: `[[Note Title]]`.
- Keep durable, personal notes in the configured vault; keep project-specific documentation with its repository.
- Use index notes to aggregate topics when that is more useful than folders.

## Workflow

1. Resolve `VAULT` with the command above and verify it exists.
2. Search filenames or content only inside `VAULT`.
3. For new notes, match existing local conventions before choosing folders, frontmatter, or index links.
4. For edits, preserve user-authored material and update links only when the target is known.

## Functional evaluation

Before reporting success after a write, verify the target exists under `VAULT` and, when relevant, use the Obsidian CLI to confirm it can see the note.
