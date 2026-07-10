# Homebrew cask reopen SIGTERM after upgrade

Use when `brew upgrade` updates some GUI casks successfully, then exits non-zero while trying to reopen a closed app.

## Observed pattern

`brew upgrade` can:
- finish the actual cask replacement for one or more apps,
- then fail in `Cask::Upgrade.reopen_apps_after_upgrade` with `Error: SIGTERM`,
- leaving the overall command non-zero even though several upgrades already landed.

This happened after upgrading GUI casks such as `codexbar` and `raycast`.

## Recovery flow

1. Do **not** assume the whole upgrade failed.
2. Verify remaining outdated packages:

```bash
brew outdated
```

3. Verify installed versions for the target casks:

```bash
brew list --cask --versions betterdisplay bitwarden codex codexbar handy ollama-app raycast repobar spotify telegram 2>/dev/null
```

4. Re-run only the still-outdated casks, ideally one by one if the batch keeps tripping on reopen:

```bash
brew upgrade repobar
brew upgrade spotify
brew upgrade telegram
```

5. Confirm `brew outdated` is empty.

## Takeaway

Treat this as a **post-upgrade verification + targeted retry** problem, not as evidence that Homebrew or the cask install itself failed. The durable lesson is the recovery sequence, not the transient SIGTERM.
