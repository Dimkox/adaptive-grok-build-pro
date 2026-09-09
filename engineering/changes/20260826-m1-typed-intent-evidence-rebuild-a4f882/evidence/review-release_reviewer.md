# Release review — M1 typed intent and evidence

## Verdict

**BLOCKED** for reviewed HEAD `62b9c601de980b1e06cf78bd69e02c4847c7e2de` against base `0a4dd0a`.

This is a source-readiness review only. It does not authorize a push, PR update, merge, Trust CI policy/holdout/image deployment, or production change. The deployed App-owned policy-epoch check on the exact PR head SHA remains the merge authority after local blockers are repaired.

## Blocking findings

### REL-001 — P0: required independent reviews reject the current release candidate

The current `code_reviewer`, `security_reviewer`, and `test_reviewer` reports are all `BLOCKED`. Code/security review demonstrates that the external holdout accepts nested v2 structures rejected by the canonical schema and that Trust CI metadata counts invalid evidence such as `{"test": null}` as mapped. Code review additionally reproduces an exception when multiple changed specs reuse an unmapped local criterion ID and a gate-valid production signal that proves no current objective. Test review identifies missing fail-closed boundary tests, receipt-staleness/selection regressions, and signed-runner-path coverage. These findings directly invalidate the current go/no-go requirement in `release.md:17` and AC-006.

Required repair: return all findings to the same route-selected write owner, rerun verification on the repaired exact HEAD, and repeat every affected independent review. Do not create passing review receipts for this snapshot.

### REL-002 — P1: README, roadmap, and package completion markers overstate source readiness

`README.md:10` calls M1 source-ready; `DARK_FACTORY_ROADMAP.md:330-341` checks every M1 source work item; and `requirements.md:7-11` checks AC-001 through AC-005. Those claims are inconsistent with the demonstrated holdout bypass and false mapped-coverage result. In particular, the checked holdout and attestation items at roadmap lines 337-338 and AC-004/AC-005 cannot be treated as complete while the independent boundary accepts/signs invalid declarations.

Required repair: either fix and re-review those behaviors before retaining the completed/source-ready wording, or revert the corresponding checkmarks and qualify README/package status until evidence is green. Keep the deployed exit criteria explicitly open.

### REL-003 — P1: no fingerprint-bound release evidence exists for the candidate

`python3 scripts/grok_status.py` reports five gaps: `verification`, `code_review`, `test_review`, `security_review`, and `release_review`. The package remains `verifying`; `requirements.md:12` and `tasks.md:8` are correctly unchecked. Current review reports are uncommitted files layered on top of the reviewed commit, so this is not yet a single final tree/fingerprint eligible for transition to `ready`.

Required repair: after the implementation and documentation stop changing, bind verification and all four passing review receipts to that exact final fingerprint, confirm `grok_status.py` reports zero gaps, and only then transition the package to `ready`.

## Release-boundary checks

- The source/deployment distinction is stated correctly in `README.md:10`, `DARK_FACTORY_ROADMAP.md:343`, `release.md:5-9`, and `rollback.md:9`: the repository changes do not prove that the external holdout, worker, policy epoch, or attestation emitter is deployed.
- Rollback is non-destructive and appropriately uses a PR revert; no database migration or data backfill is present.
- The branch changes governance-scoped `trust-ci/**` and `.grok-stack/**` source. A later PR head therefore still requires the external exact-SHA App-owned check and any human-signed `governance` approval required by the deployed policy. Local receipts or this report cannot substitute for either.
- No release, deployment, or external mutation should be attempted until the local P0/P1 blockers are repaired. Deployment of the trusted components remains a separate, explicitly delegated operator rollout with immutable artifact/holdout digests and its own rollback proof.

## Evidence inspected

- Exact commit diff `0a4dd0a..62b9c601de980b1e06cf78bd69e02c4847c7e2de`.
- Approved M1 design and implementation plan.
- Active typed spec and durable package (`brief`, `requirements`, `architecture`, `test-plan`, `release`, `rollback`, `tasks`, and `state`).
- Current `code_reviewer`, `security_reviewer`, and `test_reviewer` reports.
- `README.md`, `DARK_FACTORY_ROADMAP.md`, and the changed Trust CI policy example.
- `python3 scripts/grok_status.py`: five missing evidence receipts.
- `python3 scripts/grok_spec.py validate ... --gate --json`: local active-spec gate passes with 6/6 declaration-mapped criteria; this does not override the independent review findings.
