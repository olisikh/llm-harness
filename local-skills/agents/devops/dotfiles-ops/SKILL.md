---
name: dotfiles-ops
description: Operate Oleksii's ~/.dotfiles nix-darwin/home-manager repo: inspect, pull, rebuild, rollback, verify launchd/app effects, and handle wrapper/PATH/Homebrew pitfalls.
category: devops
---

# Dotfiles Ops

Use this for Oleksii's personal dotfiles repository at `~/.dotfiles`.

This is the canonical merged skill for dotfiles maintenance. It replaces the older overlapping `nix-darwin-dotfiles` skill.

## When to use

- User asks to pull, rebuild, apply, or inspect `~/.dotfiles`
- User says `dots make`, `sync my nix config`, `rebuild dotfiles`, `apply dotfiles`
- User wants nix-darwin generations, rollback, garbage collection, templates, dev shells, or secrets editing
- User reports a launchd service, Home Manager package, macOS setting, app alias, or Nix-managed tool changed after a dotfiles update

Do **not** use this for unrelated repos. Do **not** run `dots update` / flake updates unless the user explicitly asks to update inputs, hashes, or the lockfile; “pull and rebuild” means Git pull then apply.

## Environment

- Repo: `~/.dotfiles`
- Default branch: `main`
- Host configs commonly include `olisikh-mini`, `olisikh-mbair`, and `C2JF2NTH6H`
- The preferred user-facing wrapper is `dots` (`dots make`, `dots update`, etc.)
- Older notes may mention `home`; that command has been replaced by `dots`
- Avoid disruptive actions: no rebooting and no Docker/service interruption unless explicitly asked

## Key paths

```bash
DOTFILES="$HOME/.dotfiles"
SCRIPTS="$DOTFILES/modules/home/core/user/scripts"
DOTS_WRAPPER_SRC="$DOTFILES/modules/home/core/user/scripts/dots"
SYSTEM="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
```

Important files:

- `~/.dotfiles/flake.nix`
- `~/.dotfiles/flake.lock`
- `~/.dotfiles/systems/aarch64-darwin/<host>/default.nix`
- `~/.dotfiles/homes/aarch64-darwin/olisikh@<host>/default.nix`
- `~/.dotfiles/modules/home/core/user/scripts/nix-*`
- `~/.dotfiles/modules/home/core/user/scripts/dots`

## Pull + rebuild workflow

### 1. Inspect before changing anything

```bash
cd ~/.dotfiles
git status --short --branch
git remote -v
git log --oneline -5
```

If the tree is dirty, inspect before pulling. Do not overwrite local edits unless the user explicitly asks.

### 2. Pull only the current branch, fast-forward only

```bash
cd ~/.dotfiles
git fetch origin --prune
git pull --ff-only origin main
git status --short --branch
git log --oneline -1
```

If `--ff-only` fails, stop and report divergence. Do not merge or rebase automatically.

### 3. Apply the configuration

Preferred for Hermes/non-interactive runs:

```bash
cd ~/.dotfiles
SYSTEM="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
sudo darwin-rebuild switch --flake "$HOME/.dotfiles#$SYSTEM"
```

User-facing wrapper:

```bash
dots make
```

If running from Hermes/non-interactive shells, `dots` may be missing from `PATH` or may resolve `nix-build` incorrectly. In that case use the direct command above, or an explicit helper:

```bash
~/.local/bin/nix-build
# or, if testing repo edits before installation:
~/.dotfiles/modules/home/core/user/scripts/nix-build
```

### 4. Verify after apply

```bash
cd ~/.dotfiles
git status --short --branch
readlink /run/current-system || true
launchctl print gui/$(id -u)/ai.hermes.gateway 2>/dev/null | grep -E 'state =|pid =|last exit code' || true
```

When relevant, also verify affected services:

```bash
launchctl list | grep -Ei 'tailscale|hermes|openclaw|sketchybar|yabai|skhd' || true
```

For Homebrew GUI apps/casks, verify casks separately from formulae:

```bash
brew list --cask --versions 2>/dev/null | grep -Ei 'peekaboo|repobar|<app-name>' || true
mdfind 'kMDItemFSName == "*RepoBar*"c' 2>/dev/null | head || true
command -v peekaboo && peekaboo --version 2>/dev/null || true
```

## `dots` wrapper quick reference

Defined in `modules/home/core/user/scripts/dots`:

- `dots make` / `dots build` → rebuild/apply nix-darwin + Home Manager
- `dots update` → update hashes and flake lock
- `dots upgrade` → update + rebuild
- `dots tpl <template>` → instantiate flake template
- `dots dev [devshell]` → open a Nix dev shell
- `dots generations` / `dots gens` → list nix-darwin generations
- `dots rollback` → interactive generation rollback via `fzf`
- `dots gc` → Nix garbage collection
- `dots secrets` → edit SOPS secrets when enabled

## Helper scripts quick reference

### `nix-build`

```bash
~/.local/bin/nix-build [system] [darwin-rebuild args...]
```

Examples:

```bash
~/.local/bin/nix-build
~/.local/bin/nix-build olisikh-mini --show-trace
sudo darwin-rebuild switch --flake ~/.dotfiles#olisikh-mini --show-trace
```

### `nix-update`

Use only when explicitly asked to update pins/lockfile.

```bash
~/.local/bin/nix-update [flags] [search-dir] [nix flake update args...]
```

Notable flags:

- `--hashes-only` / `--no-flake`
- `--flake-only` / `--no-hashes`

### `nix-gens`

```bash
~/.local/bin/nix-gens
# equivalent core command:
sudo darwin-rebuild --list-generations
```

### `nix-rollback`

Interactive; avoid in autonomous runs unless the target generation is already clear.

```bash
~/.local/bin/nix-rollback
```

### `nix-gc`

```bash
~/.local/bin/nix-gc
```

### `nix-dev`

```bash
~/.local/bin/nix-dev [devshell]
```

### `nix-tpl`

```bash
~/.local/bin/nix-tpl <template> [nix flake init args...]
```

### `nix-secrets`

```bash
~/.local/bin/nix-secrets
```

Never print secret values in chat or tool summaries.

## Safety notes

- Avoid rebooting unless explicitly asked
- Be careful with Docker/Colima changes; Oleksii has important Docker Compose workloads
- Prefer `git pull --ff-only`; stop on divergence
- Do not edit or print secrets
- Some actions require sudo; if sudo blocks, report the exact blocked command
- Do not claim success from a dry build or a started build; only report a real switch as applied once it completes and is verified

## Common pitfalls

1. **Wrapper/PATH mismatch in Hermes.** `dots make` can fail if `~/.local/bin` is missing from `PATH`, or it can call legacy Nix `nix-build` instead of the dotfiles helper. Suspect PATH/wrapper resolution first. In agent runs, prefer direct `darwin-rebuild` or explicit `~/.local/bin/nix-build`.

2. **Homebrew trusted-tap failures can abort a successful rebuild late in activation.** If the configured tap is expected (for example `steipete/tap` for `peekaboo`/`codexbar`), trust it as the user, verify the trust file on disk, then rerun the rebuild.

3. **Home Manager clobber failures.** If activation says an existing file would be clobbered and the repo clearly manages that path, move the file aside to a timestamped backup, rerun the build, then report the backup path explicitly.

4. **Confusing pull with update.** `git pull` syncs repo commits. `dots update` / `nix-update` changes pins and lockfiles. Use the latter only when explicitly requested.

5. **Interactive rollback helper.** `nix-rollback` uses `fzf`; list generations first unless the target is already known.

6. **Sudo boundary from Hermes/Telegram.** Do not use generic `sudo -n true` as the only gate. Oleksii's setup may grant NOPASSWD only for the exact whitelisted `darwin-rebuild` path. Verify the actual command that matters.

7. **Homebrew cask reopen SIGTERM noise.** `brew upgrade` may exit non-zero while reopening GUI apps even though some upgrades already landed. Verify actual installed cask versions and rerun only remaining outdated casks.

## References

- `references/path-wrapper-pitfall.md` — wrapper/PATH failure and successful fallback
- `references/home-manager-clobber-and-brew-trust.md` — trusted tap + clobber recovery
- `references/homebrew-cask-reopen-sigterm.md` — post-upgrade reopen/SIGTERM verification flow
- `references/sudo-blocked-apply.md` — sudo-blocked Telegram/Hermes apply pattern

## One-shot recipes

### Pull and rebuild current Mac

```bash
cd ~/.dotfiles
git status --short --branch
git fetch origin --prune
git pull --ff-only origin main
SYSTEM="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
sudo darwin-rebuild switch --flake "$HOME/.dotfiles#$SYSTEM"
git status --short --branch
readlink /run/current-system || true
```

### Rebuild with trace

```bash
cd ~/.dotfiles
SYSTEM="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
sudo darwin-rebuild switch --flake "$HOME/.dotfiles#$SYSTEM" --show-trace
```

### List generations safely

```bash
~/.local/bin/nix-gens
```

### Check helper wiring

```bash
command -v dots || true
command -v nix-build || true
~/.local/bin/dots help || true
~/.local/bin/nix-build --help || true
sed -n '1,120p' ~/.dotfiles/modules/home/core/user/scripts/dots
```
