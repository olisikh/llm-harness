# Dotfiles Pull/Rebuild — PATH Pitfall (2026-05)

Context: Oleksii asked to pull and rebuild `~/.dotfiles` on `olisikh-mini`.

Observed sequence:

```bash
cd ~/.dotfiles
git status --short --branch     # clean, main...origin/main
git fetch origin --prune
git pull --ff-only origin main  # 815dfb6 -> 33ab9e6
home make                       # failed from Hermes terminal
```

Failure:

```text
error: path '/Users/olisikh/.dotfiles/default.nix' does not exist
```

Cause: in the Hermes non-interactive terminal, the `home` wrapper resolved `nix-build` to legacy Nix's `/nix/var/nix/profiles/default/bin/nix-build`, not Oleksii's dotfiles helper. The user's zsh environment had `~/.local/bin/nix-build` earlier, so the same `home make` command works interactively.

Fix used:

```bash
~/.dotfiles/modules/home/core/user/scripts/nix-build
# equivalent to the generated helper at ~/.local/bin/nix-build after activation
```

Successful apply highlights:

```text
setting up launchd services...
removing service com.tailscale.up
Activating home-manager configuration for olisikh
Activating sops-nix
```

Verification:

```bash
git status --short --branch     # clean, main...origin/main
readlink /run/current-system    # /nix/store/...-darwin-system-26.05.06648f4
launchctl print gui/$(id -u)/ai.hermes.gateway | grep -E 'state =|pid =|last exit code'
```

Future rule: the user-facing wrapper is now `dots make` (formerly `home make`). If wrapper use fails with a missing `default.nix` or `dots` is not found, immediately suspect PATH/wrapper resolution before changing repo files or flake structure. In Hermes runs, prefer direct `darwin-rebuild` or explicit `~/.local/bin/nix-build`.
