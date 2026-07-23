---
name: autonomous-change-execution
description: Execute authorized multi-repository implementation work autonomously with real user-facing phase updates, clean-state gates, review, and safe concurrent Git reconciliation. Use for a sequence of dependent tasks, especially when a cron job or background worker continues work without user prompting.
version: 1.0.0
---

# Autonomous Change Execution

Use this skill when the user authorizes a sequence of implementation tasks to continue without further prompts.

## Progress is a deliverable

Send concise, human-readable updates at these **checkpoints**:

1. **Preflight:** task selected, blockers verified, repository state.
2. **Build:** TDD/red result or implementation boundary.
3. **Review:** findings and whether they require a fix.
4. **Verification:** focused/full validation result.
5. **Publication:** commit IDs, push status, wiki evidence, next unblocked task.

Use a delivery mechanism that actually reaches the user. A background task's final delivery is only a task-boundary report; it is not a substitute for phase updates during a long task. If the execution channel cannot emit intermediate messages, split autonomous work into separately delivered, resumable phases and make each phase leave an explicit durable state.

Use [the checkpoint and state runbook](references/checkpoints-and-state.md) for concise update content, generated-state classification, and duplicate-publication reconciliation.

## Per-task loop

1. Read the approved task, design, blockers, acceptance criteria, evidence, and out-of-scope boundaries.
2. Fetch every affected repository and prove it is clean and synchronized before mutation.
3. Implement test-first where practical. Preserve one task per run; do not begin the next task until the current task has its evidence, review, and publication boundary.
4. Run focused and full validation. Review on independent spec and safety/standards axes; convert valid findings into regression tests and fixes.
5. Update the durable wiki using actual command results and final commit IDs.
6. Create validated Conventional Commits. Fetch again immediately before pushing and verify the resulting remote state.

## Stateful automation preflight

A scheduler may update tracked housekeeping (for example, its job registry, usage counters, or user-state files) merely by running. Before the task preflight:

- classify these generated files separately from task changes;
- when the user has authorized it, validate and commit/push them as a small, independently revertible housekeeping commit;
- otherwise, report the clean-checkout blocker rather than silently absorbing it;
- encode this remediation in the autonomous job prompt so later runs do not repeatedly self-block.

## Concurrent Git reconciliation

After every fetch, compare `origin/<branch>...HEAD` before deciding how to publish.

- If the remote advanced with an unrelated change, rebase or resolve deliberately.
- If another worker already published the same logical task, compare `origin/<branch>..HEAD`.
- Preserve the remote task commit. Rebase only when conflict-free and semantically clear; otherwise reset the local task commit onto the remote tip and commit just the reviewed delta as a new Conventional Commit.
- Never force-push to conceal concurrent work. Record the final commit chain in the wiki evidence.

## Completion criteria

A task is complete only when its acceptance evidence and review findings are recorded, commits are pushed when authorized, each affected repository has been checked against its remote, and the user has received the publication checkpoint.
