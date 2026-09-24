# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

`state.json` holds canonical local checkpoints and explicit evidence accounting. A `not_run` reason explains unfinished work; a recorded result is self-reported and does not satisfy a passing receipt. Checkpoints are observations in this worktree, and become available to another clone only when separately committed and published.

New-package and first-implementation observations are appended below by the lifecycle commands. A pending README mirror is surfaced in status and can be retried with the same explicit lifecycle command; state and README publication is not a two-file atomic transaction.

## Current protected-main rebind

The initial reports below describe the first release-sync candidate and are retained as historical evidence. After PRs #192, #194, #191 and #193 landed, the release branch was restacked onto protected `main` at `7650a5e12aad55bdcf730cd37e2faf162bec0486`. The current release-sync checkpoint before final verification is:

```text
route: 0ea34220576f
base: 7650a5e12aad55bdcf730cd37e2faf162bec0486
head: 1498273fb9866e7b388f885518555a795e8bdd2f
tree fingerprint: 90704a206960486eb4b34feffcb9828dbc4993c67d8a57102daebb5bf103aa14
```

The current candidate contains twenty post-`v2.0.18` landing rows, including #133, #192, #194, #191 and #193. The old receipt and report identities must not be used for this checkpoint; final verification and current review receipts are recorded only after this evidence section is committed.

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
  "change_id": "20260922-release-v2-0-19-from-candidate-5d93fc3-0ea342",
  "route_id": "0ea34220576f",
  "observed_at": "2026-09-22T23:29:46+00:00",
  "branch": "release/v2.0.19-candidate-20260922",
  "head": "5d93fc3d68869ab26799935adab5fa62be5e2a80",
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
  "change_id": "20260922-release-v2-0-19-from-candidate-5d93fc3-0ea342",
  "route_id": "0ea34220576f",
  "observed_at": "2026-09-22T23:45:19+00:00",
  "branch": "release/v2.0.19-candidate-20260922",
  "head": "5d93fc3d68869ab26799935adab5fa62be5e2a80",
  "detached": false,
  "git_available": true,
  "git_findings": [],
  "dirty_product_state": "dirty",
  "dirty_product_paths": [
    ".grok-stack/adaptive_grok/__init__.py",
    "CHANGELOG.md",
    "DARK_FACTORY_ROADMAP.md",
    "GROK_BUILD_HANDOFF.md",
    "PROJECT_STATE.json",
    "README.md",
    "START_HERE.md",
    "VERSION",
    "tests/test_manifest_package.py",
    "tests/test_project_state.py",
    "tests/test_structure.py"
  ],
  "note": "implementation started; preserve work before handoff"
}
```
