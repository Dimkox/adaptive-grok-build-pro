# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

`state.json` holds canonical local checkpoints and explicit evidence accounting. A `not_run` reason explains unfinished work; a recorded result is self-reported and does not satisfy a passing receipt. Checkpoints are observations in this worktree, and become available to another clone only when separately committed and published.

New-package and first-implementation observations are appended below by the lifecycle commands. A pending README mirror is surfaced in status and can be retried with the same explicit lifecycle command; state and README publication is not a two-file atomic transaction.

## Artifact build provenance

```text
source parent: 3f41be92161fef451a2dfa7451eb458ce8f022b3
source tree: aed3246585fc6435463c3e3a58f1fe6a16070e6a
staging: private 0700 directory
builds: two successful package_stack.py invocations
zip sha256: 4176a872acdca873e840855d0b2c9e379cf8f796c9de69e5560b3e2bf85634b9
sidecar sha256: 77057e0be72b38dd6f6946e31d151f8d80c96b5b7470b92798f7422147791cf8
reproducible: yes; cmp returned success
```

The package files are the only artifact delta. Candidate publication fields remain false/pending until the exact artifact-child PR merges, after which tag and GitHub Release are separate protected actions.

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
  "change_id": "20260924-build-v2-0-19-artifact-child-from-merged-release-09407b",
  "route_id": "09407b46cb4b",
  "observed_at": "2026-09-24T19:56:40+00:00",
  "branch": "release/v2.0.19-artifact-child-20260924",
  "head": "3f41be92161fef451a2dfa7451eb458ce8f022b3",
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
  "change_id": "20260924-build-v2-0-19-artifact-child-from-merged-release-09407b",
  "route_id": "09407b46cb4b",
  "observed_at": "2026-09-24T20:10:58+00:00",
  "branch": "release/v2.0.19-artifact-child-20260924",
  "head": "3f41be92161fef451a2dfa7451eb458ce8f022b3",
  "detached": false,
  "git_available": true,
  "git_findings": [
    "uncommitted_product_zero_ahead"
  ],
  "dirty_product_state": "dirty",
  "dirty_product_paths": [
    "CHANGELOG.md",
    "DARK_FACTORY_ROADMAP.md",
    "GROK_BUILD_HANDOFF.md",
    "PROJECT_STATE.json",
    "README.md",
    "START_HERE.md",
    "packages/README.md",
    "packages/adaptive-grok-build-pro-v2.0.19.zip",
    "packages/adaptive-grok-build-pro-v2.0.19.zip.sha256",
    "tests/test_project_state.py"
  ],
  "note": "implementation started; preserve work before handoff"
}
```
