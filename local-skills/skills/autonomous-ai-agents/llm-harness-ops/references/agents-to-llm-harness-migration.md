# Standalone `~/.agents` → `llm-harness` migration

Use this reference when replacing an old standalone `~/.agents` checkout with a harness-first repo that installs managed links into multiple homes.

## Proven sequence

1. Run old uninstall from the old repo root:
   ```bash
   cd ~/.agents
   bash ./uninstall.sh
   ```
2. Remove the retired source tree only after uninstall finishes.
3. Clone the new harness repo into the user-requested location.
4. Run `bash ./install.sh` from the new repo root.
5. Verify representative realpaths.
6. If `~/.skills` exists and the user does not want it, remove the legacy chain and reinstall:
   - remove `~/.claude/skills` first when it points to `~/.skills`
   - remove `~/.skills`
   - rerun `bash ./install.sh`
   - verify `~/.claude/skills` is now a normal directory
7. Prune any stale `~/.agents/skills/*` symlinks that still resolve into `harness/claude/skills`.

## Observed uninstall semantics

The old `.agents` uninstaller removed only matching managed symlinks.

Concrete observed behavior during migration:

- `~/.claude/skills` was **skipped** because it existed but did **not** point to `~/.agents/skills`.
- `~/.claude/CLAUDE.md` reported **nothing to do** when absent.

This means a clean uninstall log can still leave unrelated target paths untouched by design.

## Observed install semantics in `llm-harness`

The new installer:

- created/managed `~/.agents/skills/*` as per-skill symlinks
- linked `~/.claude/CLAUDE.md`
- linked harness-specific Claude skills under `~/.claude/skills/*`
- linked Codex skills under `~/.codex/skills/*`
- left OpenCode with its configured home path even if there was nothing new to link

## Legacy `~/.skills` trap

A legacy layout may look like this:

```text
~/.skills -> ~/.agents/skills
~/.claude/skills -> ~/.skills
```

That chain can make the install log look successful while silently mixing Claude-only skills into portable `~/.agents/skills`.

Concrete observed effect:

- Claude-only entries such as `algorithmic-art`, `compress`, and `skill-creator` appeared under `~/.agents/skills`
- after removing the legacy chain and rerunning install, those stale entries still had to be removed manually from `~/.agents/skills`

## Good verification targets

Prefer checking a few high-signal paths instead of reading the whole tree:

```bash
python3 -c 'import os; print(os.path.realpath("~/llm-harness".replace("~", os.path.expanduser("~"))))'
python3 -c 'import os; print(os.path.realpath("~/.agents".replace("~", os.path.expanduser("~"))))'
python3 -c 'import os; print(os.path.realpath("~/.claude/CLAUDE.md".replace("~", os.path.expanduser("~"))))'
```

Also inspect:

```bash
python3 - <<'PY'
from pathlib import Path
import os
for p in [Path('~/.skills').expanduser(), Path('~/.claude/skills').expanduser(), Path('~/.agents/skills').expanduser()]:
    print(p)
    print('  exists:', p.exists() or p.is_symlink())
    print('  is_symlink:', p.is_symlink())
    if p.is_symlink():
        print('  target:', os.readlink(p))
        print('  resolved:', p.resolve())
PY
```

Expected post-cleanup pattern:

- `~/.skills` is absent
- `~/.claude/skills` is a real directory with Claude-specific entries
- `~/.agents/skills` contains only portable entries

## Reporting guidance

When summarizing to the user, explicitly distinguish:

- uninstall actions that actually removed managed links
- paths skipped because they pointed elsewhere
- the requested directory deletion
- successful clone destination
- successful install run
- verification results
- whether legacy `~/.skills` was removed
- whether stale Claude-only entries had to be pruned from `~/.agents/skills`
