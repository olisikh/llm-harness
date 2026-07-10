# Sudo-blocked nix-darwin apply from Hermes

## Scenario

User asked to pull `~/.dotfiles` and install on `olisikh-mini`.

## What happened

- Repo was clean and fast-forwarded successfully from `50e5393` to `474044f`.
- Host detection via `scutil --get LocalHostName` returned `olisikh-mini`.
- Direct apply via `sudo darwin-rebuild switch --flake ~/.dotfiles#olisikh-mini` could start only until the local sudo boundary; Hermes could not provide the password.
- `sudo -n true` confirmed the real blocker: `sudo: a password is required`.
- A fallback `darwin-rebuild build --flake ~/.dotfiles#olisikh-mini` progressed for a long time but timed out; that is evidence the eval/build was running, not evidence that install completed.

## Reusable lesson

When operating dotfiles from Hermes on Telegram/macOS:

1. Pull and verify git state first.
2. Detect host with `scutil --get LocalHostName`.
3. Check `sudo -n true` before promising a full install.
4. If sudo is blocked, stop and hand off the exact command:

```bash
sudo darwin-rebuild switch --flake ~/.dotfiles#olisikh-mini
```

5. Make clear that a timed-out dry build is incomplete verification, not a successful switch.
