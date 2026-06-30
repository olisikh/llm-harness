# Promoting a user-local skill into the shared repo

Use this when a skill starts in an installed runtime path such as `~/.hermes/skills/` but should become canonical source in `~/llm-harness`.

## Practical workflow

1. Copy the skill directory into the correct repo subtree under `~/llm-harness/harness/<harness>/skills/...`.
2. Commit the new canonical copy in the repo.
3. Run `cd ~/llm-harness && ./install.sh` so the runtime harness home points back to the canonical repo copy.
4. Remove any redundant editable runtime copy, leaving only the installed symlink/compatibility target.
5. Push the shared-repo commit.
6. Verify the skill is discoverable again in a fresh session.

## Notes

- Prefer editing the repo copy from then on.
- Keep the old path only as an installed compatibility bridge; the repo is the source of truth.
- If the repo remote changed, update the repo remote once and continue pushing to the new canonical origin.
