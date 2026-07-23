# Autonomous Task Runbook

## Checkpoint payload

Keep every user update to five lines or fewer:

- **Stage:** preflight, build, review, verification, or publication.
- **Task:** current task ID and objective.
- **Evidence:** one concrete result (test count, review finding, or repository state).
- **Decision:** proceed, fix, publish, or blocked.
- **Next:** the next durable boundary and whether it is automatic.

## Generated-state classification

Treat scheduler-owned registries, run counters, usage data, and memory metadata as housekeeping only when their content is mechanically generated and independently reviewable. Commit those files separately from implementation and documentation. Any other unexpected path is a real preflight blocker.

## Duplicate-publication reconciliation

When a concurrent runner published an equivalent task first:

1. fetch and compare the two commits against their merge base;
2. retain the remote implementation commit;
3. preserve only the meaningful local delta as a follow-up fix commit;
4. correct all evidence pages to name the actual pushed commit chain.
