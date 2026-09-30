# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

`state.json` holds canonical local checkpoints and explicit evidence accounting. A `not_run` reason explains unfinished work; a recorded result is self-reported and does not satisfy a passing receipt. Checkpoints are observations in this worktree, and become available to another clone only when separately committed and published.

New-package and first-implementation observations are appended below by the lifecycle commands. A pending README mirror is surfaced in status and can be retried with the same explicit lifecycle command; state and README publication is not a two-file atomic transaction.

Code and test review reports perform bounded, change-relevant mutation probes in a reviewer-owned private scratch copy outside the reviewed worktree. Keep the reviewed candidate read-only; use scratch below a trusted non-sticky parent with mode `0700`. Reproduce the exact candidate (HEAD and relevant staged, unstaged, and untracked changes), record its HEAD and tree fingerprint before/after, and treat unsafe or mismatched snapshots and changed fingerprints as stale/inconclusive. Reviewer read-only configuration is not an OS-enforced isolation boundary.

Reviewers return the complete report to the coordinator out-of-band and do not write into the candidate worktree. After all reviews finish, the coordinator persists all reports here, then reruns final verification and records fresh fingerprint-bound receipts for the tree containing those reports.

Each report must include:

- source identity: HEAD and candidate tree fingerprint;
- scratch path and `reviewed-tree-modified: no`;
- each claim probed, exact command, concise observed output, and mutant outcome (`killed`, `survived`, or `inconclusive`);
- claims not executed and why; static claims without executable probes are unexecuted;
- surviving mutants as findings or explicit limitations (no blanket mutation-score threshold unless a scoped policy requires it).

<!-- checkpoint:initial -->
## Initial checkpoint

Local observation only; not verification or publication evidence.

```json
{
  "kind": "initial",
  "change_id": "20260930-\u0440\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c-factory-v1-5-fpf-u7-runtime-applicab-2a1125",
  "route_id": "2a112560eee9",
  "observed_at": "2026-09-30T19:41:02+00:00",
  "branch": "feature/v15-fpf-runtime",
  "head": "edf09469748c60b31a4b6f7669d1a9e35210071e",
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

<!-- checkpoint:implementation -->
## Implementation checkpoint

Local observation only; not verification or publication evidence.

```json
{
  "kind": "implementation",
  "change_id": "20260930-\u0440\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c-factory-v1-5-fpf-u7-runtime-applicab-2a1125",
  "route_id": "2a112560eee9",
  "observed_at": "2026-09-30T19:48:42+00:00",
  "branch": "feature/v15-fpf-runtime",
  "head": "edf09469748c60b31a4b6f7669d1a9e35210071e",
  "detached": false,
  "git_available": true,
  "git_findings": [],
  "dirty_product_state": "dirty",
  "dirty_product_paths": [
    "factory/src/adaptive_factory/fpf_runtime.py",
    "factory/tests/test_fpf_runtime.py"
  ],
  "note": "implementation started; preserve work before handoff"
}
```
