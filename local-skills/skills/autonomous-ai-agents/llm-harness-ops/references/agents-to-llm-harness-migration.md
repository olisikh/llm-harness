# Migration to `llm-harness`

Use this reference when setting up or reinstalling the harness-first `llm-harness` repo that installs managed links into multiple harness homes.

## Proven sequence

1. Clone `llm-harness` into the user-requested location.
2. Run `./harness.py uninstall` from `~/.llm-harness` to clear any stale managed symlinks.
3. Run `./harness.py install` from `~/.llm-harness`.
4. Verify representative realpaths.

## Verification targets

Prefer checking a few high-signal paths instead of reading the whole tree:

```bash
python3 -c 'import os; print(os.path.realpath("~/.llm-harness".replace("~", os.path.expanduser("~"))))'
python3 -c 'import os; print(os.path.realpath("~/.agents".replace("~", os.path.expanduser("~"))))'
python3 -c 'import os; print(os.path.realpath("~/.claude/CLAUDE.md".replace("~", os.path.expanduser("~"))))'
```

Also inspect:

```bash
python3 - <<'PY'
from pathlib import Path
import os
for p in [Path('~/.claude/skills').expanduser(), Path('~/.agents/skills').expanduser()]:
    print(p)
    print('  exists:', p.exists() or p.is_symlink())
    print('  is_symlink:', p.is_symlink())
    if p.is_symlink():
        print('  target:', os.readlink(p))
        print('  resolved:', p.resolve())
PY
```

Expected pattern:

- `~/.claude/skills` is a real directory with Claude-specific entries
- `~/.agents/skills` contains only portable entries

## Reporting guidance

When summarizing to the user, explicitly distinguish:

- uninstall actions that removed managed links
- paths skipped because they pointed elsewhere
- successful clone destination
- successful install run
- verification results
