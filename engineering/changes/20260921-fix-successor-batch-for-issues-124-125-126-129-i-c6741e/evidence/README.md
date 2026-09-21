# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

`state.json` holds canonical local checkpoints and explicit evidence accounting. A `not_run` reason explains unfinished work; a recorded result is self-reported and does not satisfy a passing receipt. Checkpoints are observations in this worktree, and become available to another clone only when separately committed and published.

New-package and first-implementation observations are appended below by the lifecycle commands. A pending README mirror is surfaced in status and can be retried with the same explicit lifecycle command; state and README publication is not a two-file atomic transaction.

<!-- checkpoint:initial -->
## Initial checkpoint

Local observation only; not verification or publication evidence.

```json
{
  "kind": "initial",
  "change_id": "20260921-fix-successor-batch-for-issues-124-125-126-129-i-c6741e",
  "route_id": "c6741eae6dcd",
  "observed_at": "2026-09-21T18:17:32+00:00",
  "branch": "fix/stale-controls-batch-20260921",
  "head": "21ced3709dff48abf3e15aff62e2493de75f2fa0",
  "detached": false,
  "git_available": true,
  "git_findings": [],
  "dirty_product_state": "clean",
  "dirty_product_paths": [],
  "note": "draft; implementation not started"
}
```

Initial evidence accounting (current records are in `state.json`):

```json
{
  "schema_version": 1,
  "obligations": [
    {
      "id": "verification",
      "kind": "receipt",
      "receipt_kind": "verification",
      "status": "not_run",
      "reason": "implementation not started"
    },
    {
      "id": "code_review",
      "kind": "receipt",
      "receipt_kind": "code_review",
      "status": "not_run",
      "reason": "implementation not started"
    },
    {
      "id": "test_review",
      "kind": "receipt",
      "receipt_kind": "test_review",
      "status": "not_run",
      "reason": "implementation not started"
    },
    {
      "id": "security_review",
      "kind": "receipt",
      "receipt_kind": "security_review",
      "status": "not_run",
      "reason": "implementation not started"
    },
    {
      "id": "release_review",
      "kind": "receipt",
      "receipt_kind": "release_review",
      "status": "not_run",
      "reason": "implementation not started"
    }
  ]
}
```
