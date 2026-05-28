# Shared skills repo migration

On Oleksii's setup, the shared skills repository now lives at `~/.agents` with skill content under `~/.agents/skills/`.

When moving a skill from Hermes-managed storage into the shared repo:

1. Copy the skill directory into `~/.agents/skills/<category>/<skill>`.
2. Replace the original Hermes path with a symlink back to the shared copy.
3. Verify both the shared path and the symlink resolve to the same skill files.

This keeps the shared library version-controlled while preserving backward compatibility for Hermes skill loading.