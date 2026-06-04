# Contributing PRs to OpenClaw

## Important: Do Not Contaminate Existing PR Branches

When working on changes related to an existing PR, ALWAYS create a SEPARATE branch. Never push commits to an existing open PR's branch unless those commits are directly related to that PR's scope.

**What went wrong in one session:** An agent authored a fix for the opencode Zen plugin (adding `resolveDynamicModel` + `augmentModelCatalog`) and force-pushed it to the `feat/opencode-split-provider-keys` branch, which was already an open PR about splitting env vars. This:
1. Contaminated the PR diff with 5k+ unrelated changed lines
2. Added my commit to ClawSweeper review scope (creating new P1 findings that weren't part of the original PR)
3. Required a recovery: force-push to revert the branch, then a separate PR for the correct changes

**Pre-flight check before any force push:**
```bash
git branch --show-current          # What branch am I on?
gh pr view --json headRefName      # Does this match an existing PR?
git log --oneline -3               # Are these the right commits?
```

**Recovery if contamination happens:**
```bash
# Reset the contaminated branch
git checkout <contaminated-branch>
git reset --hard HEAD~N     # where N = number of bad commits
git push --force-with-lease origin <contaminated-branch>

# Create a new branch for the correct changes
git checkout -b <new-branch> origin/main
git cherry-pick <bad-commit>  # or re-apply the changes cleanly
git push -u origin HEAD
gh pr create --repo openclaw/openclaw ...
```

## Real Behavior Proof Requirement

OpenClaw enforces a `Real behavior proof` CI check on external PRs. Without the required section in the PR body, the check fails and the PR cannot merge.

### Required Fields

The proof section must include these fields (field names are flexible):

1. **Behavior or issue addressed** — What problem does this PR fix?
2. **Real environment tested** — Where was this tested? (e.g., "macOS local dev, OpenClaw built from PR branch")
3. **Exact steps or command run after this patch** — Concrete commands showing the behavior works
4. **Evidence** — Terminal output, screenshots, recordings, console output, or redacted runtime logs in code blocks. **Unit tests, mocks, CI, lint, typechecks do NOT count.**
5. **Observed result** — What happened when you ran the steps
6. **What was not tested** — Honest scope limits (optional but recommended)

### Evidence Format

The check script (`scripts/github/real-behavior-proof-check.mjs`) looks for:
- Artifact links: `![...](...)` or GitHub asset URLs
- Terminal output in code blocks (triple backticks with actual output)
- Keywords like "screenshot", "terminal capture", "console output", "runtime logs"

**Mock-only evidence is rejected.** If the evidence only contains `pnpm test`, `vitest`, `lint`, `typecheck`, `build`, `CI passes`, `unit tests`, `mocks`, `snapshots`, the check fails with "mock_only".

### Template

```markdown
## Real behavior proof

### Behavior or issue addressed

<What this PR fixes or adds>

### Real environment tested

<Environment description>

### Exact steps or command run after this patch

```bash
<commands>
```

### Evidence

<Terminal output, screenshots, or logs showing the behavior>

### Observed result

<What happened>

### What was not tested

<Limits>
```

### Updating PR Body

```bash
gh pr edit <PR_NUMBER> --body-file /tmp/pr-body.md
```

## ClawSweeper Behavior

ClawSweeper is an automated reviewer that can:
- **Review**: Analyze PRs and leave structured review comments
- **Apply**: Auto-close PRs it determines are "already implemented on main"

Key behaviors:
- ClawSweeper uses a GitHub App installation token, so close events appear as the installing user, not the bot
- ClawSweeper's apply lane runs on a schedule and can close PRs it deems redundant
- Protected labels (`security`, `beta-blocker`, `release-blocker`, `maintainer`) prevent auto-closure
- Maintainer-authored PRs are not auto-closed unless the reason is "implemented_on_main"

### Triggering a re-review

After addressing ClawSweeper review findings, push the fixes and comment on the PR:

```bash
git push origin <branch-name>
gh pr comment <PR_NUMBER> --repo openclaw/openclaw --body "@clawsweeper re-review"
```

The `@clawsweeper re-review` trigger runs a fresh review on the updated branch. There is no explicit approval step — ClawSweeper re-analyzes the full diff.

### Common ClawSweeper finding categories

Based on real PR experience (PR #87762 feat/opencode-split-provider-keys):

| Finding | What to fix |
|---------|------------|
| **Test harness/env candidate mismatch** | The mock candidate map in test files may not include new env vars introduced by the PR. Update the map to list the new env var in priority order. |
| **Removed setup.providers[].envVars** | If the PR replaces `setup.providers[].envVars` with `providerAuthEnvVars`, ClawSweeper flags this as a manifest contract regression. Restore `setup.providers` alongside `providerAuthEnvVars`. |
| **Sibling docs still describe old behavior** | Update all docs pages that reference the changed auth pattern — not just the provider's own docs page but also the model-provider overview, wizard reference, and CL automation docs. Search the entire `docs/` tree for the old env var pattern. |
| **Auth profile fan-out** | When splitting a shared env var into provider-specific ones (e.g. `OPENCODE_API_KEY` → `OPENCODE_ZEN_API_KEY` + `OPENCODE_GO_API_KEY`), do NOT keep shared `profileIds` or `expectedProviders` from `createProviderApiKeyAuthMethod(...)` config if each provider has its OWN credential. Remove `profileIds` entirely and scope `expectedProviders: [params.providerId]`. Keeping shared fan-out with split env vars causes cross-contamination — onboarding with one provider's key writes it over the sibling's credential. This is a P1 finding, not just a forward-looking risk. |

## PR Event Forensics

When investigating why a PR was closed:

1. Check `gh pr view` for current state — PRs can be reopened
2. Check `gh api repos/OWNER/REPO/issues/NUMBER/events` for event timeline
3. Look for `head_ref_force_pushed` coinciding with `closed` — indicates bot automation
4. Check workflow runs around the close time for ClawSweeper or other automation
5. Remember: `actor.login` may show a human when the action was performed by a bot using their installation token
