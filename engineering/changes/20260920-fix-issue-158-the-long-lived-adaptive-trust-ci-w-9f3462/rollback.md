# Rollback plan — issue #158

## Trigger conditions
- A tracked command is classified with the wrong exit status after the change (the theft class), or
- a job stalls because the drain released a guard it should not have, or
- the AST sweep misses a newly added spawn site so the guard balance breaks in tests.

## Application rollback
`git revert` the squashed commit. Files: `reap.py` (new), `worker.py`, `lease.py`, `sandbox.py`, `workspace.py`,
`backup.py`, `tests/test_reaping.py`. No DB migration, no schema change, no policy or attestation format involved, so
rollback is purely code.

## Data recovery / forward-fix
Nothing to recover: job state lives in PostgreSQL with lease expiry, and rolling back only stops future reaping —
zombies again accumulate harmlessly until the next attempt. Forward fix preferred: narrowing the guarded set or the
drain point, never removing the spawn-counter guard, because without it reaping turns killed commands into passing ones.

## Verification after rollback
1. `make trust-ci-test` → 243 OK (the pre-change count), confirming the revert is real, not a no-op.
2. Re-run the PID-1 pair: `after_lease_boundary` must return the zombie pid again.
3. `grok_verify --mode pr` green and a fresh exact-SHA check on the new head.
4. Issue #158 reopened with the reason that caused the revert.
