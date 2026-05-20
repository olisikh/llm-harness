---
name: apple-notes-to-obsidian
description: Export, review, and selectively import Apple Notes into the Obsidian vault at ~/notes. Use when asked to extract Apple Notes, migrate Apple Notes to Obsidian, triage Apple Notes for a markdown vault, decide which Apple Notes are safe to store, route notes into 10 Work, 20 Learning, 30 Personal, or 40 Reference, or avoid importing sensitive personal data.
---

# Apple Notes to Obsidian

## Overview

Export Apple Notes through the Notes app automation interface, classify each note, and import only safe markdown notes into the `~/notes` Obsidian vault. Treat Apple Notes as a mixed inbox: some notes belong in the vault, some are throwaway, and some are too sensitive to store as plain markdown.

## Workflow

1. Read `references/routing.md` before changing routing, ignore, or sensitivity rules.
2. Use installed Obsidian skills when available: `obsidian:obsidian-markdown` (or `obsidian-markdown` in `~/.agents/skills`) for properties, wikilinks, embeds, and callouts; `obsidian:obsidian-cli` (or `obsidian-cli`) for vault search and Obsidian-aware file operations.
3. Inspect the vault folders with `find ~/notes -maxdepth 2 -type d | sort` when the target layout may have changed.
4. Run the exporter in report-only mode first:

```bash
python3 /Users/olisikh/.agents/skills/apple-notes-to-obsidian/scripts/export_apple_notes.py --vault ~/notes --report /tmp/apple-notes-import-report.md
```

5. Review `/tmp/apple-notes-import-report.md`. Do not import sensitive notes; discuss them by category only, without copying their content into chat or files.
6. Import only after review:

```bash
python3 /Users/olisikh/.agents/skills/apple-notes-to-obsidian/scripts/export_apple_notes.py --vault ~/notes --write --report /tmp/apple-notes-import-report.md
```

7. Show the user the import summary and any notes routed to `40 Reference/Apple Notes Import Review/`.
8. Run `git -C ~/notes diff --stat` and inspect new files before any commit. Commit only when explicitly asked.

## Safety Rules

- Prefer the helper script over direct SQLite reads. Notes.app storage is private, version-specific, and may require Full Disk Access; Apple automation is less brittle.
- Stop and report the permission issue if `osascript` cannot access Notes. The user may need to grant Terminal, iTerm, or the active host app Automation access to Notes in macOS System Settings.
- Keep sensitive bodies out of `~/notes`, reports, and chat. Store at most a title, folder path, and sensitivity category in the report.
- Treat unclassified notes as review items, not finished notes. The script routes them to `40 Reference/Apple Notes Import Review/` only when `--write` is used.
- Preserve source metadata in frontmatter for imported notes: Apple account, Apple folder, creation date, modification date, source id, and import timestamp.
- Avoid overwriting existing markdown files. Let the script create numeric suffixes for filename collisions.

## Resources

- `scripts/export_apple_notes.py`: export Apple Notes via JXA, classify notes, generate a dry-run report, and optionally write markdown into the vault.
- `references/routing.md`: vault-specific routing rules, ignore rules, and sensitive-data policy.

## Related Skills

- Use `obsidian:obsidian-markdown` or `obsidian-markdown` when imported notes need Obsidian properties, wikilinks, tags, embeds, or callouts beyond the script's default frontmatter.
- Use `obsidian:obsidian-cli` or `obsidian-cli` when checking whether imported content already exists, moving notes inside the vault, or validating that Obsidian can read the new files cleanly.
