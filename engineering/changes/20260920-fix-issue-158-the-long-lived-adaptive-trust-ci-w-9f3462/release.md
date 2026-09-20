# Release plan — issue #158

## Deployment
Effective only when the **worker image is rebuilt from this revision and redeployed**: the running container is an
August image whose `workspace.py` lacks `start_new_session`. Merge path is the usual one — commit → `grok_verify
--mode pr` → reviews → receipts → push → PR → App-owned exact-SHA check → delegated merge.

## Feature flags / staged rollout
None; the drain is unconditional but bounded, and declines while any spawn is in flight.

## Metrics and alerts
`SIG-001`: worker zombie count (`ps -eo ppid,stat | awk -v p=$W '$1==p && $2 ~ /^Z/' | wc -l`) must stay at 0 for jobs
after redeploy. The four pre-existing zombies persist until restart — reported, not claimed fixed. `reap_stats()` is
not exposed on `/metrics` (frozen payload; out of scope).

## Go/no-go
Go: 257 tests OK against 243 baseline; red-before-green evidence recorded; additions-only diff; ruff/compileall clean;
gate PASS; three receipts on the head; external exact-SHA SUCCESS on the same head.
No-go: any arm showing a stolen exit status, any SIGCHLD handler introduced, any change to job-status classification, or
a restart of the live worker performed as part of this change.
