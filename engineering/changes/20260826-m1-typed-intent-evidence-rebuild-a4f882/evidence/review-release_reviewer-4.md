# Release review 4 — M1 typed intent and evidence

## Verdict

**BLOCKED** for exact candidate HEAD `ee9ed6ada12f78f808a12df311a41d7888ca9d30` against original review base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`.

Code review 4 and test review 4 pass this candidate, and the previous source-readiness overstatement has been corrected. Security review 4 is `BLOCKED`, however, with one mandatory-approval bypass and one trusted-worker resource-exhaustion boundary failure. This candidate therefore cannot receive passing local release evidence or transition from `verifying` to `ready`.

This verdict concerns local source readiness only. It neither requires nor authorizes a push, PR update, merge, deployed Trust CI change, or production rollout.

## Blocking findings

### REL-R4-001 — P0: exact-path remediation leaves protected dot paths outside approval scopes

Security review 4 demonstrates that `ApprovalRule.from_dict()` rewrites authored globs with `.replace('\\', '/').lstrip('./')`, while changed Git paths are now intentionally preserved exactly. Current deployed-shape rules such as `.grok/**`, `.grok-stack/**`, `.github/**`, and `.coveragerc` therefore lose their leading dot and fail to match the actual changed path; literal-backslash policy globs are also rewritten away from the exact filename. A real repository reproduction returned `.grok-stack/hook.py` from Git but no required `governance` scope.

This is release-blocking because the branch changes governance-sensitive workflow and Trust CI source, and M1 explicitly requires local code not to bypass externally required human scopes. Preserve approval-glob identity, support any convenience `./` prefix by removing exactly that prefix only, and add both policy-level and full-runner action-required/no-command regressions for protected dot paths and a literal-backslash target.

### REL-R4-002 — P1: claimed Git output bounds do not bound trusted-worker allocation

Security review 4 confirms that `GitWorkspace._git_bytes()` captures all stdout before checking the 100 MB limit, and `_nul_records()` allocates the complete split/tuple before checking the record-count limit. An attacker-controlled diff/status stream can therefore exhaust trusted-worker memory before the intended fail-closed checks execute.

Stream Git stdout with a hard `max+1` read, terminate the child on overflow, and enforce aggregate bytes, record count, and per-record length incrementally. Add exact-boundary and over-limit tests that prove bounded termination. Re-review the new exact HEAD.

### REL-R4-003 — P1: required local evidence remains incomplete by design and because security is blocked

`python3 scripts/grok_status.py` reports all five required receipts missing. The package correctly remains `verifying`, AC-006 and Task 6 remain unchecked, and no passing `security_review` or `release_review` receipt may be recorded for this snapshot. Because the repairs will change product/security code, rerun PR verification and every affected route-selected review on one final tree, then record fingerprint-bound receipts and require zero status gaps before transitioning to `ready`.

## Release-readiness checks that pass

- `review-code_reviewer-4.md` is `PASS` for the exact candidate HEAD and closes the prior exact Git path, surrogate, raw-provenance, and immutable holdout-bundle findings within the exercised scope.
- `review-test_reviewer-4.md` is `PASS`: root tests report 223/223, Trust CI tests report 182 passed with 10 honestly reported conditional PostgreSQL skips, compileall/diff checks pass, and two consecutive default Trust CI runs preserve the exact holdout file set and digest.
- README now calls the branch a locally green remediation candidate and explicitly requires fresh reviews before `source-ready`; it does not claim deployment.
- The roadmap now explains that checked work items mean source plus local regression coverage, while source completion still depends on fresh verification/reviews and deployed exit criteria remain open.
- `requirements.md`, `tasks.md`, and `state.json` consistently leave AC-006, Task 6, and `ready` incomplete.
- `release.md` and `rollback.md` preserve dual-read/single-write migration, PR-based source rollback, and the separation between repository source and separately authorized immutable Trust CI policy/holdout/image rollout.
- No database migration, destructive data operation, GitHub Actions workflow, or deployment action is part of this candidate.

## External boundary after local repair

Passing local reviews and receipts will remain advisory. After an explicitly authorized PR update, merge eligibility still requires the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on that exact PR head plus the human-signed `governance` scope required by deployed policy. Deployment of the new holdout, worker reader, policy epoch, or attestation emitter is a separate operator-controlled rollout and requires immutable artifact/digest, rollback, and live exact-SHA proof; it must not be inferred from M1 source readiness.

## Evidence inspected

- Exact commit history and diff through `ee9ed6ada12f78f808a12df311a41d7888ca9d30`.
- All three remediation reports and preserved earlier review history.
- Fresh wave-4 code, test, and security reports.
- Active typed spec plus package requirements, tasks, state, test plan, release plan, and rollback plan.
- `README.md`, `DARK_FACTORY_ROADMAP.md`, and the repository/Trust CI source boundary.
- Current active-spec gate validation: valid, 6/6 declaration-mapped criteria.
- Current status: five missing evidence receipts; package state `verifying`.
