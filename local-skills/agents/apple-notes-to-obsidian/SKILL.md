---
name: apple-notes-to-obsidian
description: Export, review, and selectively import Apple Notes into the configured Obsidian vault. Use when asked to extract Apple Notes, migrate Apple Notes to Obsidian, triage Apple Notes for a markdown vault, decide which Apple Notes are safe to store, route notes into 10 Work, 20 Learning, 30 Personal, or 40 Reference, or avoid importing sensitive personal data.
---

# Apple Notes to Obsidian

## Overview

Export Apple Notes through the Notes app automation interface, classify each note, and import only safe markdown notes into the configured Obsidian vault. Resolve the vault from `~/.agents/config/skill-paths.json` (`paths.obsidian_vault`); the current configured value is `~/notes`. Treat Apple Notes as a mixed inbox: some notes belong in the vault, some are throwaway, and some are too sensitive to store as plain markdown.

## Workflow

1. Read `references/routing.md` before changing routing, ignore, or sensitivity rules.
2. Resolve the vault once:

```bash
VAULT="$(python3 ~/.llm-harness/scripts/skill-path.py path obsidian_vault)"
test -d "$VAULT"
```

3. Use installed Obsidian skills when available: `obsidian:obsidian-markdown` (or `obsidian-markdown` in `~/.agents/skills`) for properties, wikilinks, embeds, and callouts; `obsidian:obsidian-cli` (or `obsidian-cli` in `~/.agents/skills`) for vault search and Obsidian-aware file operations.
4. Inspect the vault folders with `find "$VAULT" -maxdepth 2 -type d | sort` when the target layout may have changed.
5. Run the exporter in report-only mode first:

```bash
python3 ~/.agents/skills/apple-notes-to-obsidian/scripts/export_apple_notes.py --vault "$VAULT" --report /tmp/apple-notes-import-report.md
```

6. Review `/tmp/apple-notes-import-report.md`. Do not import sensitive notes; discuss them by category only, without copying their content into chat or files.
7. Import only after review:

```bash
python3 ~/.agents/skills/apple-notes-to-obsidian/scripts/export_apple_notes.py --vault "$VAULT" --write --report /tmp/apple-notes-import-report.md
```

8. Show the user the import summary and any notes routed to `40 Reference/Apple Notes Import Review/`.
9. Run `git -C "$VAULT" diff --stat` and inspect new files before any commit. Commit only when explicitly asked.

## Safety Rules

- Prefer the helper script over direct SQLite reads. Notes.app storage is private, version-specific, and may require Full Disk Access; Apple automation is less brittle.
- Stop and report the permission issue if `osascript` cannot access Notes. The user may need to grant Terminal, iTerm, or the active host app Automation access to Notes in macOS System Settings.
- Keep sensitive bodies out of the configured vault, reports, and chat. Store at most a title, folder path, and sensitivity category in the report.
- Treat unclassified notes as review items, not finished notes. The script routes them to `40 Reference/Apple Notes Import Review/` only when `--write` is used.
- Preserve source metadata in frontmatter for imported notes: Apple account, Apple folder, creation date, modification date, source id, and import timestamp.
- Avoid overwriting existing markdown files. Let the script create numeric suffixes for filename collisions.

## Resources

- `scripts/export_apple_notes.py`: export Apple Notes via JXA, classify notes, generate a dry-run report, and optionally write markdown into the vault.
- `references/routing.md`: vault-specific routing rules, ignore rules, and sensitive-data policy.

## Related Skills

- Use `obsidian:obsidian-markdown` or `obsidian-markdown` when imported notes need Obsidian properties, wikilinks, tags, embeds, or callouts beyond the script's default frontmatter.
- Use `obsidian:obsidian-cli` or `obsidian-cli` when checking whether imported content already exists, moving notes inside the vault, or validating that Obsidian can read the new files cleanly.
