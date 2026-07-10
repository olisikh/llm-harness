# Home Manager clobber + Homebrew trust during darwin-rebuild

## When this matters

A `darwin-rebuild switch` run gets through evaluation/build but fails during either:

1. `Homebrew bundle...` with `Refusing to load formula ... from untrusted tap ...`, or
2. Home Manager activation with `Existing file ... would be clobbered`.

## Observed successful fix

### 1) Expected tap trust

When the tap is already intentionally declared by the dotfiles repo (for example `steipete/tap` for `peekaboo` / `codexbar`), trust it as the user:

```bash
brew trust --tap steipete/tap
```

Then verify the trust file exists:

```bash
cat ~/.homebrew/trust.json
```

Expected shape:

```json
{
  "trustedtaps": [
    "steipete/tap"
  ]
}
```

If `darwin-rebuild` still errors immediately after an earlier mixed sudo/non-sudo attempt, rerun the rebuild after confirming the trust file on disk.

### 2) Back up clobbering unmanaged file

If Home Manager reports a user file would be clobbered and the repo clearly manages that path, move the file aside with a timestamped backup in the same directory:

```bash
mv ~/.config/opencode/tui.json ~/.config/opencode/tui.json.pre-home-manager-$(date +%Y%m%d-%H%M%S)
```

Then rerun:

```bash
sudo darwin-rebuild switch --flake ~/.dotfiles#$(scutil --get LocalHostName)
```

## Verification

- `git status --short --branch` is clean in `~/.dotfiles`
- `readlink /run/current-system` points at the new generation
- the previously clobbering file is now managed (often a symlink into the Nix store)
- report the backup path explicitly
