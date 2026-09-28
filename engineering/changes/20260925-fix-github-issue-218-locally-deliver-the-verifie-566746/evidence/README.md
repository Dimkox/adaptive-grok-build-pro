# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

Issue-level elapsed-time assumptions, salary-equivalent estimates, expensive-check accounting, and the recommended verification budget are recorded in [economics.md](economics.md).

`state.json` holds canonical local checkpoints and explicit evidence accounting. A `not_run` reason explains unfinished work; a recorded result is self-reported and does not satisfy a passing receipt. Checkpoints are observations in this worktree, and become available to another clone only when separately committed and published.

New-package and first-implementation observations are appended below by the lifecycle commands. A pending README mirror is surfaced in status and can be retried with the same explicit lifecycle command; state and README publication is not a two-file atomic transaction.

Code and test review reports perform bounded, change-relevant mutation probes in a reviewer-owned private scratch copy outside the reviewed worktree. Keep the reviewed candidate read-only; use scratch below a trusted non-sticky parent with mode `0700`. Reproduce the exact candidate (HEAD and relevant staged, unstaged, and untracked changes), record its HEAD and tree fingerprint before/after, and treat unsafe or mismatched snapshots and changed fingerprints as stale/inconclusive. Reviewer read-only configuration is not an OS-enforced isolation boundary.

Reviewers return complete reports out-of-band and do not write into the candidate worktree. Completion order is preliminary `--no-record` verification → independent reviews → persist reports and finish tracked accounting → `ready` → amend the sole candidate → final recording verification on clean exact HEAD → verification PASS receipt → review receipts → read-only zero-gap status.

The four `review-*-e824fb15-FAIL.md` files preserve the September 26 review wave exactly. Earlier `review-*_reviewer.md` and implementation sections are historical snapshots, not current PASS claims. Current repairs and focused RED/GREEN evidence are recorded in `repair-e824fb15-general_implementer.md`; current receipt accounting remains in `../state.json`.

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
  "change_id": "20260925-fix-github-issue-218-locally-deliver-the-verifie-566746",
  "route_id": "566746aef130",
  "observed_at": "2026-09-25T20:03:27+00:00",
  "branch": "fix/issue-218-scan-chain-delivery",
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
  "change_id": "20260925-fix-github-issue-218-locally-deliver-the-verifie-566746",
  "route_id": "566746aef130",
  "observed_at": "2026-09-25T20:12:33+00:00",
  "branch": "fix/issue-218-scan-chain-delivery",
  "head": "cb9af4073ba6c3d515145164d771c75ebdfa3224",
  "detached": false,
  "git_available": true,
  "git_findings": [
    "uncommitted_product_zero_ahead"
  ],
  "dirty_product_state": "dirty",
  "dirty_product_paths": [
    ".agents/skills/adaptive-delivery/SKILL.md",
    ".agents/skills/release-readiness/SKILL.md",
    ".agents/skills/verification-evidence/SKILL.md",
    ".grok-stack/adaptive_grok/_policy_legacy.py",
    ".grok-stack/adaptive_grok/architecture.py",
    ".grok-stack/adaptive_grok/doctor.py",
    ".grok-stack/adaptive_grok/python_test_runner.py",
    ".grok-stack/adaptive_grok/receipts.py",
    ".grok-stack/adaptive_grok/util.py",
    ".grok-stack/adaptive_grok/verification.py",
    ".grok-stack/templates/change/evidence/README.md",
    ".grok-stack/templates/change/tasks.md",
    ".grok-stack/templates/consumer-AGENTS.md.tmpl",
    ".grok/hooks/stop_gate.py",
    ".grok/skills/adaptive-delivery/SKILL.md",
    ".grok/skills/release-readiness/SKILL.md",
    ".grok/skills/verification-evidence/SKILL.md",
    "AGENTS.md",
    "QUICKSTART.md",
    "README.md",
    "decisions.md",
    "docs/package-status.md",
    "docs/superpowers/plans/2026-09-25-issue-227-git-env-grant-boundary.md",
    "factory/README.md",
    "factory/tests/factory_test_manifest.py",
    "factory/tests/run_disposable_exit.py",
    "factory/tests/test_migrations.py",
    "mistakes.md",
    "scripts/grok_review.py",
    "scripts/grok_status.py",
    "scripts/grok_verify.py",
    "scripts/install_into.py",
    "tests/_support.py",
    "tests/test_architecture_model_preflight.py",
    "tests/test_change_receipts.py",
    "tests/test_factory_parallel_runner.py",
    "tests/test_hooks.py",
    "tests/test_installer.py",
    "tests/test_package_status.py",
    "tests/test_policy.py",
    "tests/test_python_test_runner.py",
    "tests/test_structure.py",
    "tests/test_util_fingerprint.py",
    "tests/test_verification_doctor.py",
    "tests/test_workflow_artifacts.py"
  ],
  "note": "implementation started; preserve work before handoff"
}
```
