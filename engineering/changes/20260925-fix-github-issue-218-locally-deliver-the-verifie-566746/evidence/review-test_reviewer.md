# Independent test review — issue #218 delivery

Date: `2026-09-25 UTC`
Route: `566746aef130`
Route base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
Reviewed HEAD: `cdad4de5cd9620a97d3919bc47c89ff923839623`
Reviewed Git tree: `49ec3bd103c7e22b9019b10e084bc7f9b4602d70`
Clean exact-commit fingerprint: `fbfdc7c2beb6995815177fd5d3f1e6296ac1ac7a99e0ca5d3938fd35e3dd93b9`
Verdict: **FAIL**
reviewed-tree-modified: no

## Findings by severity

### Critical

None.

### Important

#### I-01 — A forged `complete` scan scope can satisfy verification evidence without scanning the selected blobs

`_scan_identity_matches_current()` recomputes and compares only the contract, HEAD, ranges, chain digest, and commit count (`.grok-stack/adaptive_grok/verification.py:1648-1668`). The three facts produced only by parent-edge/blob traversal — `blob_count`, `bytes_scanned`, and `path_edge_count` — are accepted when they are merely nonnegative, while `status == complete` and `worktree == complete` are trusted as stored claims (`verification.py:1669-1678`). `validate_evidence()` delegates PASS-receipt closure to this predicate (`.grok-stack/adaptive_grok/receipts.py:1047-1057`).

An independent private probe created a real two-commit route chain that added a regex-matching fake credential and then deleted it. Without calling `_build_chain_scan()` or `_secret_scan()`, the probe used `_enumerate_scan_identity()`, supplied `status/worktree=complete` and zero for all three coverage counters, and wrote a verification PASS receipt. `validate_evidence(root, route)` returned `[]`. The forged scope claimed `commit_count=2`, `blob_count=0`, `bytes_scanned=0`, and `path_edge_count=0`, even though the real chain necessarily contains the deleted secret blob and two path edges.

This defeats the closed-scope compatibility boundary introduced by issue #218: missing scope is rejected, but equivalent fabricated scope is accepted. Local receipts remain explicitly non-authoritative for merge, so this is Important rather than Critical; it still allows local completion/Stop evidence to falsely pass and contradicts AC-004's requirement that incomplete coverage fail closed.

Acceptance condition: validate PASS evidence against independently recomputed full selected-chain/worktree coverage, not self-declared nonnegative counters. Add a regression that constructs an add-secret/delete chain, publishes an identity-only `complete` scope without running the scan, and requires `verification: scan scope is missing or stale` (or an equally fail-closed gap). Mutations of each coverage counter and complete-status field must also be rejected; the real verifier-produced scope must remain compatible.

### Minor

None.

## Positive test assessment

- RED/GREEN evidence is coherent and independently matches the implementation boundary. The original regressions fail on endpoint-only behavior and pass after parent-edge traversal; delivery evidence also records the fresh-package whitespace RED and narrow template/helper GREEN.
- The add-then-delete regression traverses real `verify(..., mode='pr')`, proves the path is absent from the final inventory, finds the introducing commit, asserts both `pr-target` and `route` ranges, checks blob coverage, and verifies that the fake value is absent from serialized output (`tests/test_verification_doctor.py:1209-1267`).
- The repaired-intermediate-whitespace regression first proves endpoint `git diff --check` is green, then requires the per-parent-edge result to identify the introducing commit and path (`test_verification_doctor.py:1349-1404`).
- Selected-base behavior is covered by a divergent local PR-target graph, and invalid, unavailable, ambiguous, and multiple-best-base cases fail closed. Merge topology is separately characterized by asserting every merge-parent edge is present (`test_verification_doctor.py:1308-1347`).
- Bounds fail closed (`test_verification_doctor.py:1269-1306`), and `_secret_scan` returns only metadata in findings. The focused exercised report did not expose the fake secret.
- Missing `scan_scope` is correctly rejected (`tests/test_change_receipts.py:947-958`), and route/head changes stale otherwise-bound evidence. I-01 is specifically the untested fabricated-coverage case.
- The generated-package compatibility contour commits a fresh package, runs `git show --check`, performs real verification/receipt recording, and reaches review evidence with no gaps (`tests/test_change_receipts.py:1180-1203`). The three template changes only remove trailing spaces from empty bullets; receipt fixtures now use the shared real closed-scope helper instead of manufacturing scanless PASS evidence.

## Provenance and compatibility contour

- HEAD is one non-merge commit with sole parent `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- Verified source `68dfc70c5f58adcc927f731c5d88de09a1b4b242` resolves to tree `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`, matching the recorded pre-package squash projection.
- Relative to that source, every non-package delta is confined to the three change-package templates, `tests/test_change_receipts.py`, `tests/test_hooks.py`, and `mistakes.md`; the only behavior repair is whitespace cleanup plus truthful fixture setup.
- `git diff cb9af4073..HEAD -- trust-ci` is empty. `git diff --check cb9af4073..HEAD` passed.
- The coordinator-provided exact-head full verifier passed: core with 22 workers in `78.590s`; factory in `193.585s`. It was not rerun during this bounded review.

## Executed commands and results

- Exact identity and graph inspection: HEAD `cdad4de5cd9620a97d3919bc47c89ff923839623`, tree `49ec3bd103c7e22b9019b10e084bc7f9b4602d70`, sole parent `cb9af4073ba6c3d515145164d771c75ebdfa3224`; PASS.
- Focused ten-selector matrix covering add/delete secret, history bound, merge parents, repaired whitespace, divergent selected base, missing/stale scan scope, generated-package compatibility, and Stop compatibility: **10 passed in 19.517s**.
- Private forged-scope probe: **survived** — a scanless PASS receipt over a two-commit deleted-secret chain yielded `forged_gaps=[]`. This determines the FAIL verdict.
- No broad/full suite, network, GitHub, external system, or deployed-state operation was run.

## Residual risk

The verifier's live execution path itself correctly detects the reviewed secret and whitespace histories, including merge parents and incomplete bounds. The blocker is persistence/validation: the receipt consumer cannot distinguish that real result from identity-only fabricated coverage. Until I-01 is repaired, local completion evidence can false-pass even though the external App-owned Trust CI gate remains separate merge authority.

At review start, a coordinator-owned uncommitted lifecycle transition in this package's `state.json` was already present; another reviewer report appeared concurrently. This reviewer did not alter either. This report is the only worktree file written by the test reviewer; product, tests, runtime receipts, and external systems were not modified.

---

## Final re-review — issue #218 forged-scope repair

Date: `2026-09-25 UTC`
Route: `566746aef130`
Route base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
Reviewed HEAD: `ddd9988e4b43fd1502796de42fdcc52170233c61`
Reviewed Git tree: `9a1dab623ee74f9f1d65e56ed5e6564c94ca5310`
Clean exact-commit fingerprint: `a4f4d88d1a0db70105d1048288af499e03ee45151e98efb4b3376c913e7b93cc`
Observed review-time fingerprint, including the pre-existing coordinator-owned `state.json` change: `f9266a5f5141c930d85e720ff728af783790cb7e3c9f94a7beb521fa690445ab`
Final verdict: **PASS** — this supersedes the historical exact-`cdad4de5` FAIL above.
reviewed-tree-modified: no

### Findings by severity

#### Critical

None.

#### Important

None. Historical I-01 is closed at this exact HEAD.

#### Minor

None.

### I-01 closure and mutation evidence

`_scan_identity_matches_current()` now preserves the identity-only path only for `require_complete=False`, while PASS-evidence validation rebuilds the selected chain scan and changed worktree inventory, rejects scan failures or secret findings, and requires exact equality between the stored and recomputed scope (`.grok-stack/adaptive_grok/verification.py:1672-1700`). The receipt regressions exercise both sides of that boundary: an identity-only `complete` receipt over a real add-secret/delete-secret history is rejected, and independent mutations of `blob_count`, `bytes_scanned`, `path_edge_count`, `status`, and `worktree` are rejected (`tests/test_change_receipts.py:961-1027`).

The historical independent exploit probe was rerun unchanged against this HEAD. Its forged scope still had `commit_count=2` with zero blob, byte, and path-edge coverage, but validation now returned `forged_gaps=["verification: scan scope is missing or stale"]`.

Two private-scratch mutants establish that the tests pin both required semantics:

- Replacing the final exact-scope comparison, `return stored == scan.scope`, with `return True` caused all five counter/status/worktree mutation cases to fail. The identity-only deleted-secret case continued to pass because the independent scan rejected the secret before scope comparison.
- Bypassing the complete scan with an early `return True` after the `require_complete=False` branch, in addition to removing the final comparison, caused the identity-only deleted-secret regression and all five field-mutation cases to fail.

The baseline was restored after each private-scratch mutation; the candidate worktree was never mutated.

### Four security families

The repaired suite covers all four required families without relying only on mocked receipt fields:

1. **Forged coverage and recomputation (AC-007):** real Git history is used for the identity-only add/delete-secret receipt, while exact counter/status/worktree mutations prove stored claims cannot substitute for recomputation.
2. **Root-bound Git execution (AC-008):** focused coverage exercises inherited `GIT_DIR`, inherited `GIT_WORK_TREE`, both selectors empty, hostile `GIT_CONFIG_COUNT`, replacement refs, and branch/tag refs (`tests/test_change_receipts.py:1340-1383`).
3. **Object/worktree type and race handling (AC-009):** committed symlink blobs are scanned; gitlinks, dirty symlinks, broken symlinks, FIFOs, and named-file replacement races fail closed.
4. **Diagnostic redaction (AC-010):** the diff-check regression asserts that a secret-bearing source line is absent from the serialized result.

The surrounding original contours remain represented: add/delete secret history, merge-parent traversal, intermediate whitespace, missing scan scope, and exact receipt compatibility all passed in the bounded matrix.

### Commands and results

- Exact identity/graph/status inspection: HEAD, tree, and sole parent matched the binding above; `git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224..HEAD` passed.
- Focused 12-selector scan/receipt matrix covering the two forged-scope regressions, root-bound selectors/config/replacement refs, symlink and gitlink behavior, dirty special files, replacement race, diagnostic redaction, add/delete history, merge parents, and intermediate whitespace: **12 passed in 5.329s**.
- Historical forged-scope probe: **rejected**, with the exact stale-scope gap shown above.
- Private exact-scope-equality deletion mutant: **killed** by all five field-mutation cases.
- Private complete-recomputation bypass mutant: **killed** by the identity-only exploit regression and all five field-mutation cases.
- Coordinator-provided full exact-head verification: core **PASS** in `83.888s`; DB/factory **PASS** in `190.977s`. This bounded reviewer did not rerun the full verifier.
- No broad suite, live external service, network, GitHub, deployed-state, or publication operation was performed.

### Residual risk

This review intentionally used the focused security matrix rather than independently rerunning the full verifier. The remaining assurance depends on the coordinator-provided exact-head full result and the external App-owned Trust CI check, which remains the merge authority. Local receipts and this review report do not substitute for that external gate.

A coordinator-owned `state.json` modification predated this final review, and the security-review report was concurrently modified by its owner; both remained untouched. The only file written by this reviewer is this report; product code, tests, runtime receipts, and external systems were not modified.

## Historical final-review appendix — `de23e5da`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `de23e5dac4cfe9fc8d832078ec867ae05e096db1`, reviewed-tree-modified **no**, verdict **FAIL**.
- The test contour did not deterministically constrain comparison work or typed budget exhaustion. It also missed unchanged legacy bad-line compatibility under fully replaced clean context and a clean insertion before the bad line, while moved/duplicate coverage had to stay intact across committed, staged, and unstaged paths.
- The independent repetitive-line measurements were 0.039s, 0.169s, 0.705s, 2.922s, and 12.732s at 500, 1,000, 2,000, 4,000, and 8,000 lines respectively.

## Historical final-review appendix — `f2789117`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `f278911796e843089cff33e2f8e59a963e79ffd8`, tree `5f3275e0eb81e82a68dd8419d18bd8b7b65fae70`, reviewed-tree-modified **no**, verdict **FAIL** with 0 Critical, 1 Important, and 0 Minor findings.
- Important: direct budget tests did not prove production wiring. A mutant resetting the chain budget inside the path/edge loop and a mutant omitting the shared budget from endpoint calls both survived; required coverage was two individually fitting comparisons whose cumulative work exhausts, with exact incomplete codes, incomplete chain scope, and redacted diagnostics.
