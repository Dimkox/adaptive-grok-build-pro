# Paperwork-only closure and receipt binding: existing implementation limits

Read-only research against slice A's unchanged workflow implementation. No receipt, route, source file, tool or repository configuration was changed by this analysis.

## Finding

There is **no existing source-equivalence / paperwork-only verification-rebinding protocol** in `receipts.py`, `state.py`, `change.py`, or the CLI wrappers. The repository's no-op instruction legitimately avoids repeating full tests and review waves for paperwork; it does not provide a machine transition that converts old exact-tree receipts into current ones.

`util.tree_fingerprint` includes Git HEAD plus all non-noise changed paths/content (`util.py:183`). Runtime is excluded, but tracked engineering reports and state documents are not. `spec_fingerprint` also includes HEAD and route base. `validate_evidence` checks exact current tree, spec, architecture and governance bindings (`receipts.py:560–610`). `tests/test_change_receipts.py:630` explicitly verifies staleness after HEAD changes; there is no documentation-only exception.

## What the existing calls do and do not establish

- `write_receipt(root, kind, status, report, details, expected_tree_fingerprint=...)` is a generic current-state recorder (`receipts.py:487`). It rederives bindings and checks stability during recording. It does **not** validate that a historical full report covers current source, execute tests, or recognize a source-equivalence proof. Its `details` object is caller-supplied metadata, not a verified carry-forward contract.
- `active_architecture_binding` computes model/schema/contracts/base/HEAD identities; it does not run architecture fitness, drift or diagram checks. `active_governance_binding` freshly validates canonical governance and binds architecture identity. Thus calling the recorder after these bindings alone is weaker than the real verification path, which calls `_architecture_check` and then `_governance_check` with successful architecture evidence.
- `grok_review.py` only checks that the supplied report file exists, then records caller-supplied pass/fail. Re-running it against an old report after HEAD changes is not automatically a fresh independent review or a supported rebinding operation.
- `change.transition(..., "ready", ...)` checks only legal state transitions and writes tracked `state.json`; it does not validate receipts. The transition itself changes the fingerprint. `state.update_route` changes runtime only and does not refresh evidence. A successful ready transition is therefore not evidence that the current tree has zero gaps.
- Supplying the current fingerprint as `expected_tree_fingerprint` to a manually composed historic pass report only checks write-time stability; it does not repair historic test provenance. Do not relabel historical `created_at`, tested HEAD, fingerprint or test counts.

## Safe current approach for the seven source branches

Honor AGENTS.md's explicit no-op rule: run the mandatory full verifier and independent reviews once for each actual product change. When subsequent commits contain only final evidence/status/docs, do not repeat those long suites solely to clear local bookkeeping. Preserve the original complete JSON and review reports with their exact tested/reviewed HEAD and fingerprint. Record a separate, honestly named source-equivalence and paperwork check report, not a replacement full-run result.

That source-equivalence record should compare the full relevant inventory (path, mode, object/content identity, additions/deletions), not just files changed in that slice. Permit only an explicit list of paper/report paths; do not broadly ignore engineering/, schemas, config, scripts, fixtures, dependencies, runtime templates or executable docs. Confirm route base, acceptance criteria, contracts, rules and tested environment inputs remain unchanged; any material input change requires the affected real checks. Fresh structural checks can establish current paperwork validity, but their output remains a separate scope.

Supported read-only commands for that separate scope include:

```text
git diff --check <verified-source-commit>..HEAD
python3 scripts/grok_spec.py validate --gate --json
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py drift --json
python3 scripts/grok_architecture.py diagram --check --json
python3 scripts/grok_architecture.py fitness --base <unchanged-exact-route-base> --worktree --pre-risk yellow --json
python3 scripts/grok_governance.py validate --json
python3 scripts/grok_status.py
```

Use the actual route risk rather than always yellow. Inspect changed paperwork for secret exposure and verify referenced evidence hashes. If using existing private verifier helper functions to collect the same structural checks, label the result as a fresh structural subset and do not imply `_python` or full `verify` executed.

After a paperwork commit, the honest claim is: **the product source is unchanged from the fully verified and independently reviewed source commit; final paperwork has separate fresh checks; exact final-HEAD local receipts are stale/missing.** Do not claim zero gaps or current local-ready from stale receipts. This does not block continued local reconstruction under the no-op instruction, and cannot replace the final external exact-SHA merge check.

## Avoiding fingerprint churn prospectively

The clean supported mechanism is to avoid changing the checked branch after its final source/docs commit: run full verification there, keep subsequent report outputs outside that worktree while they are being written, and record independent reports without altering the tested source. Runtime receipt writes do not change fingerprints. If durable reports must be copied into that same branch afterward, the current exact-tree format has the documented staleness limit; no existing API removes it. Keeping evidence in a separate durable evidence checkout can preserve source-branch identity, but must be explicitly documented and satisfy the repository's report-location requirement; it is not an automatic replacement for the active change package.

A new authenticated/no-op carry-forward evidence contract would be a separate workflow feature requiring its own design, tests and review. It is outside this source-splitting task. No such tool modification is needed to keep progressing honestly now.

## Evaluated alternative: separate evidence checkout in the same repository

Parent proposed a dedicated local evidence-only branch/worktree of this same repository. Independent reviewers inspect the immutable source worktree but write reports to `engineering/changes/<exact-slice>/evidence/` in the evidence checkout. **This is a valid bounded interpretation of the existing report-location instruction:** the reports remain in the exact durable change-package path in the same repository, and existing tools do not require them to be in the same worktree. This is fresh review recording, not receipt rebinding or a waiver of tests.

The current CLI has exactly these semantics: `report_path = root / args.report`, verifies `is_file()`, and passes the original `args.report` string to `write_receipt`. With an absolute path, `Path.__truediv__` keeps the absolute target; there is no repository-relative normalization/restriction in this CLI. `write_receipt` binds the **source checkout** active route/spec/architecture/governance/fingerprint and stores the external report path. It does not bind the evidence checkout commit or report content hash automatically.

Correct sequence with existing calls (run these from the source worktree, using actual absolute paths):

```text
python3 scripts/grok_review.py code_review --status pass --report /absolute/evidence-worktree/engineering/changes/<slice>/evidence/code-review.md
python3 scripts/grok_review.py test_review --status pass --report /absolute/evidence-worktree/engineering/changes/<slice>/evidence/test-review.md
python3 scripts/grok_status.py
```

Conditions for this sequence:

1. The prescribed full verifier has actually finished successfully on the unchanged source checkout, and its auto-recorded verification receipt remains current. Do not copy or rewrite that receipt from another HEAD. If full verification failed, this arrangement does not authorize passing review receipts.
2. Both selected reviewers independently inspect that exact source checkout after implementation/verification and write their own concrete reports to the evidence counterpart. Each report names source repository/worktree, route/change, actual base, exact HEAD, checked fingerprint, and relevant source manifest/report hashes. Evidence-checkout HEAD must never be described as the tested source HEAD.
3. Preserve the source checkout's complete checked tree and HEAD throughout. No report copies, README updates, status-file edits, commits, new untracked source paths, symlinks, or ignore changes. `.grok-stack/runtime` receipt writes are intentionally fingerprint-neutral.
4. Evidence files become durable source-controlled documents in the separate evidence branch. Preserve their contents after recording and explicitly hash them in the evidence index because the current review receipt records path, not report digest. Include the unchanged original full verifier JSON there as a byte-for-byte archival copy with the source HEAD clearly labeled.
5. `grok_status` from the source checkout must actually return zero evidence gaps. Then one may accurately say that this exact source tree has current full-verification and independent-review receipts. This local statement remains distinct from external exact-SHA Trust CI and merge eligibility.
6. Do not run a tracked `grok_change transition ... ready` against the source checkout after verification: its `state.json` change still invalidates the receipts. An evidence-branch completion record can document the source's zero-gap state, and runtime-only route status can reflect it, but do not claim the source's frozen durable state file was updated. Keep this bookkeeping distinction visible.
7. A local absolute report path is not a portable remote PR artifact URL. Describe the evidence branch/path locally; only link a remote branch/artifact after a separately authorized actual push/publish exists. This alternative creates no external-write or merge authority.

This avoids the seven redundant full test reruns caused solely by placing review artifacts in the checked tree. It introduces no checker changes, fabricated pass, fingerprint override or reference manipulation. If any source/test/schema/config changes emerge from review, return to the same writer and perform actual verification/review of that changed source as usual.
