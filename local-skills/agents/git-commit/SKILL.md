---
name: git-commit
description: Create a validated Conventional Commit for current repository changes, and push when requested.
disable-model-invocation: true
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git diff *) Bash(git status *)
---

## Current state

!`git status --short`

## Staged and unstaged diff

!`git diff HEAD`

## Recent commits (for style reference)

!`git log --oneline -10`

## Instructions

1. Review the diff, repository guidance, and recent commit history. If a repository defines stricter Conventional Commit types or scopes, follow that project rule.
2. Stage relevant changed files (prefer specific paths over `git add .`; never stage `.env` or secrets).
3. Compose a Conventional Commit header in this exact shape:

   ```text
   <type>(<optional-scope>)<optional-!>: <description>
   ```

   Use one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, or `revert`. Use `!` or a `BREAKING CHANGE:` footer for a breaking change. Keep the header at 72 characters or fewer. Do not create a non-Conventional commit.
4. Put the proposed complete message in a mode-`0600` temporary file and run `scripts/validate-conventional-commit.py` against it. Treat a validation failure as a hard stop; revise the message rather than bypassing validation.
5. Create the commit with `git commit -F <validated-message-file>`. Do not add `Co-Authored-By`, model/vendor attribution, or other AI attribution trailers unless the user explicitly requests them.
6. If the user also asked to **push/sync**, do not assume the earlier status check is still current. Run `git fetch origin`, inspect ahead/behind, and if the push is rejected because `origin/<branch>` moved, rebase onto the updated remote branch before retrying the push. Treat this as a normal race, not as a terminal failure.
7. Report the commit hash and validated Conventional Commit subject on success.

## Functional evaluation

Before claiming a commit succeeded, require:

- `scripts/validate-conventional-commit.py` accepts the exact message file given to Git.
- A deliberately malformed test header is rejected by that validator.
- `git log -1 --format=%s` exactly equals the validated header.

## Pitfalls

- A repository can be `0 ahead / 0 behind` when you first inspect it and still reject `git push` a minute later because another process advanced `origin/main` in the meantime. When push is part of the ask, verify again right before pushing.
- For dirty long-lived state repos, distinguish **your unique diff vs `origin/main`** from pre-existing staged/unstaged changes when explaining what your new commit actually contains.

If $ARGUMENTS is provided, treat it as guidance for the commit message or scope.
