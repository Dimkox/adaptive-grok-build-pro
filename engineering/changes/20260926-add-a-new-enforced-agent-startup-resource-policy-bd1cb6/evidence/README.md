# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

Current repair index: [code-review.md](code-review.md) is the unaltered **historical FAIL** against exact HEAD `554a29d6396555ebd4961508eca86917126ce4f1`, SHA-256 `a77338963c5b4789f57442a4b3e714bfde343f990d39115cb98094458ed83a6a`; it is not a successor review or approval. [review-repair-20260926.md](review-repair-20260926.md) records the writer's verified repair and bounded probes. Independent re-review follows exact committed-tree local verification.

Successor index: [code-review-successor-fail-b70f5790.md](code-review-successor-fail-b70f5790.md) is the unaltered **historical successor FAIL** (SHA-256 `60890ef3ebe119ca1834c38db5ae53538e77d9ed53d05fd5ee5c3d65cf286635`). [successor-review-disposition.md](successor-review-disposition.md) closes the prior selector finding, distinguishes the standalone jq probe from the original gh embedded interface, and records b70f5790's successful pre-review verifier versus the required post-evidence verification. Neither report is relabelled as PASS.

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
  "change_id": "20260926-add-a-new-enforced-agent-startup-resource-policy-bd1cb6",
  "route_id": "bd1cb67aa011",
  "observed_at": "2026-09-26T00:47:12+00:00",
  "branch": "docs/parallel-resource-startup-20260926",
  "head": "cb9af4073ba6c3d515145164d771c75ebdfa3224",
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
  "change_id": "20260926-add-a-new-enforced-agent-startup-resource-policy-bd1cb6",
  "route_id": "bd1cb67aa011",
  "observed_at": "2026-09-26T01:24:46+00:00",
  "branch": "docs/parallel-resource-startup-20260926",
  "head": "5681d0c8da7cf3f6dc0b8612b80aa026e1a7eb3c",
  "detached": false,
  "git_available": true,
  "git_findings": [],
  "dirty_product_state": "dirty",
  "dirty_product_paths": [
    "AGENTS.md",
    "README.md",
    "START_HERE.md",
    "mistakes.md"
  ],
  "note": "implementation started; preserve work before handoff"
}
```
