# Shared skill dedup and cleanup

Use when a shared-skill cleanup task spans the canonical repo in `~/llm-harness` and installed runtime trees such as `~/.agents/skills` or `~/.hermes/skills`.

## Operating rule

- Canonical physical skill source lives under `~/llm-harness/harness/<harness>/skills`.
- Installed runtime trees are compatibility/install targets, not the preferred edit locations.
- Git is the backup. Do not manufacture `*.backup.*`, `.archive`, or import-dump trees as routine cleanup output.

## Cleanup pattern

1. Inventory duplicate skill families across the repo and installed runtime trees by semantic skill name, not folder name alone.
2. Diff the canonical repo candidate against any installed, imported, or archived copies.
3. Merge only durable, class-level improvements into the canonical repo copy.
4. Delete redundant runtime copies after merge.
5. Delete backup/archive trees instead of preserving them as clutter.
6. Run `cd ~/llm-harness && ./install.sh` if the canonical source moved or changed path.
7. Verify no duplicate editable skill names remain across repo and runtime trees.

## Matching pitfall

Do not assume `openclaw-imports/`, `.archive/`, or `*.backup.<timestamp>/` denotes a distinct skill family. These often hold migrated or archived copies of the same underlying skill and should be matched semantically before deciding what stays.

## User-specific preference captured here

On Oleksii's setup:

- shared/user skills should live canonically in `~/llm-harness`
- Hermes runtime trees should be install targets or explicit compatibility bridges, not source-of-truth edit locations
- duplicate skill copies and backup/archive skill folders are unwanted garbage
- rely on git history instead of keeping extra backup folders
