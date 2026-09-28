# Independent code review — issue #218 delivery

Date: 2026-09-25 UTC
Route: `566746aef130`
Verdict: **FAIL**

## Exact review binding

- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Reviewed HEAD: `cdad4de5cd9620a97d3919bc47c89ff923839623`
- Reviewed Git tree: `49ec3bd103c7e22b9019b10e084bc7f9b4602d70`
- Clean committed-candidate tree fingerprint: `fbfdc7c2beb6995815177fd5d3f1e6296ac1ac7a99e0ca5d3938fd35e3dd93b9`
- Verified source commit/tree: `68dfc70c5f58adcc927f731c5d88de09a1b4b242` / `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`
- Reviewed-tree-modified: **no**. I made no product, test, runtime-state, or receipt changes. This review report is the only candidate-worktree file I wrote. A separate reviewer concurrently added an uncommitted adversarial test after my review began; it is not part of the reviewed commit and is identified below only as reproduction evidence.

The candidate is exactly one non-merge commit whose sole parent is the stated base. The clean fingerprint was independently computed from a private local clone checked out at the exact reviewed HEAD, because coordinator-owned `state.json` evidence was already modified in the active worktree before review. Other route reviewers added their own reports concurrently; those evidence-only changes are not part of the reviewed commit.

## Findings

### Critical

None.

### Important

1. **Verification receipt validation accepts forged coverage/completion claims when range identity is genuine.** `_scan_identity_matches_current()` re-derives and compares only `contract`, `head_sha`, `ranges`, `chain_digest`, and `commit_count`; for `blob_count`, `bytes_scanned`, and `path_edge_count` it requires merely a nonnegative integer, while `status` and `worktree` need only equal the literal `complete` (`.grok-stack/adaptive_grok/verification.py:1648-1679`). `write_receipt()` accepts caller-provided `details` (`.grok-stack/adaptive_grok/receipts.py:689-766`), and `validate_evidence()` delegates the entire scan-scope decision to that identity-only predicate (`.grok-stack/adaptive_grok/receipts.py:1047-1057`). Therefore a caller can enumerate the real commit identity, claim zero inspected blobs/bytes/edges plus `complete`, and mint a schema-v2 PASS that validation accepts even when the selected chain added and later deleted a secret. This contradicts issue #218 AC-007 (reject forged scope), FORBID-002 (never report complete after inspection uncertainty), and the delivery route's requirement not to weaken receipt validation. The local receipt is not external merge authority, but this bypasses the repository's local completion/review prerequisite chain.

   Minimal reproduction: create a disposable base → add-secret → delete-secret history; build only `_enumerate_scan_identity`; form `scan_scope = {**identity, status: complete, worktree: complete, blob_count: 0, bytes_scanned: 0, path_edge_count: 0}`; pass it to `write_receipt(..., 'verification', 'pass', details={'mode': 'fast', 'scan_scope': forged})`; then `validate_evidence()` returns `[]`. The focused regression expected `verification: scan scope is missing or stale` and failed with that exact empty result. Independently mutating each genuine counter by `+1` is also accepted.

   Acceptance condition: current verification receipt validation must independently reconstruct the bounded scan coverage for the exact stored/current range identity and reject any mismatch in coverage/completion fields, any incomplete scan, and any historical secret/whitespace failure relevant to a PASS. Add committed regressions for the identity-only add/delete-secret forgery and for each coverage counter/status/worktree mutation; they must fail on this HEAD and pass only after the repair. Review receipts must continue to require and digest-bind that newly validated verification receipt.

### Minor

None.

## Review conclusions

- Full-chain range selection is fail-closed and exact-SHA based. It resolves one immutable HEAD, validates the route base as an exact ancestor, derives a unique local PR-target merge base, and rejects unavailable delivery targets (`.grok-stack/adaptive_grok/verification.py:674`). The reviewed candidate selected both route and PR-target provenance rows at the exact base while deduplicating them to one commit edge.
- Chain scanning enumerates each selected `scan_base..head`, strictly parses bounded commit identities, unions commits, inspects every parent edge, deduplicates regular-file postimage blobs, and fails incomplete on range, edge, object, parse, or resource uncertainty (`.grok-stack/adaptive_grok/verification.py:1342`, `.grok-stack/adaptive_grok/verification.py:1446`). Secret findings expose bounded rule/path/commit metadata rather than matched bytes; parent-edge whitespace diagnostics likewise avoid carrying offending content (`.grok-stack/adaptive_grok/verification.py:1620`, `.grok-stack/adaptive_grok/verification.py:1730`).
- Reports carry scan scope and source stability re-derives exact range identity; review receipt creation validates then canonically digest-binds the current verification receipt (`.grok-stack/adaptive_grok/verification.py:1648`, `.grok-stack/adaptive_grok/verification.py:2570`, `.grok-stack/adaptive_grok/receipts.py:707`, `.grok-stack/adaptive_grok/receipts.py:1047`). However, the Important finding shows that this validation does not re-establish the claimed scan coverage/content result. Existing completion publication race checks remain intact but do not close that semantic gap.
- The implementation of `verification.py` and `receipts.py` is byte-identical to verified source `68dfc70c`. Relative to that source, the only non-package paths are the declared six: three change-package templates, `tests/test_change_receipts.py`, `tests/test_hooks.py`, and `mistakes.md`. Template changes only remove trailing spaces from empty bullets. Compatibility fixtures now obtain a real closed-scope verification receipt before review receipts, and the generated-package contour explicitly checks the committed package with `git show --check` (`tests/test_change_receipts.py:1171`). No scanner or receipt predicate was weakened.
- `trust-ci/` has no base-to-HEAD delta. External App-owned exact-SHA Trust CI remains the merge authority.

## Commands and evidence

- `git rev-list --parents -n 1 HEAD` — exact HEAD with sole parent `cb9af407...`.
- `git rev-parse HEAD HEAD^{tree}` — exact HEAD/tree above.
- `git rev-parse 68dfc70c...^{tree}` — `0914b5d6...`.
- `git diff --name-status 68dfc70c...HEAD` — only the active package and the declared six compatibility paths.
- `git diff --name-only cb9af407...HEAD -- trust-ci/` — empty.
- `git diff --check cb9af407...HEAD` — pass.
- SHA-256 comparison of candidate/source `verification.py` — both `f61c5def23fda67c250749a4bca08911cb625561c8f7e109aed7f303afa39388`.
- SHA-256 comparison of candidate/source `receipts.py` — both `c743b03516fd4b591a6e30d998f3c484896e2de9f6beabbfd64478769edde694`.
- Direct exact-candidate chain construction — two provenance rows, one deduplicated commit/edge, 206 path edges, 204 blobs, 2,501,911 bytes, zero selection failures, zero chain failures, and zero secret findings.
- Focused unittest selection covering transient secret deletion, commit bounds, merge parents, repaired intermediate whitespace, verification receipt recording/validation, all receipt kinds, generated-package contour, and Stop compatibility — `Ran 9 tests in 21.313s`, `OK`.
- Private-scratch mutant removing historical secret findings from `_secret_scan` — killed by `test_pr_secret_scan_rejects_secret_added_then_deleted_in_commit_chain` (`pass != fail`).
- Private-scratch mutant omitting chain-edge whitespace checks — killed by `test_pr_diff_check_rejects_intermediate_whitespace_repaired_before_head` (`pass != fail`). Scratch was moved to trash after use.
- Concurrent-review adversarial receipt regressions against the unchanged exact HEAD — `Ran 2 tests in 2.069s`, `FAILED (failures=4)`: the identity-only add/delete-secret forged scope was accepted, as were independent `blob_count`, `bytes_scanned`, and `path_edge_count` mutations. These uncommitted tests were not written by this reviewer and are not included in the reviewed binding.
- Coordinator-provided pre-review full verifier on the exact HEAD — PASS; Core `78.590s` with 22 workers, Factory PostgreSQL `193.585s`, all checks pass. I did not rerun the broad suite.

## Residual risk and acceptance boundary

The bounded scanner itself intentionally rejects histories, path-edge sets, blobs, or aggregate bytes beyond configured limits; this is a fail-closed operational limit, not silent coverage reduction. The verdict remains FAIL until the Important receipt-validation gap and its regressions are closed. Local reports and receipts remain workflow evidence only; merge eligibility still requires the App-owned policy-epoch check and any required external approvals.

---

## Final re-review — 2026-09-25 UTC

Verdict: **FAIL**

### Exact re-review binding

- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Re-reviewed HEAD: `ddd9988e4b43fd1502796de42fdcc52170233c61`
- Re-reviewed Git tree: `9a1dab623ee74f9f1d65e56ed5e6564c94ca5310`
- Clean committed-candidate tree fingerprint: `a4f4d88d1a0db70105d1048288af499e03ee45151e98efb4b3376c913e7b93cc`
- Reviewed-tree-modified: **no**. I made no product, test, runtime-state, or receipt changes; I appended only this required report section. Coordinator-owned `state.json` was already modified before re-review.

### Prior Important finding

**Closed.** `_scan_identity_matches_current()` now independently rebuilds the selected chain, rejects scan failures and secret findings, scans current changed files, and requires exact equality with the recomputed closed scope (`.grok-stack/adaptive_grok/verification.py:1672-1700`). Both the identity-only add/delete-secret forgery and all counter/status/worktree mutations are rejected by the committed regressions (`tests/test_change_receipts.py:961-1027`). Review receipts continue to validate and digest-bind the current verification receipt through the unchanged ordering contract.

### Critical findings

None.

### Important findings

1. **Repository-local `core.worktree` still redirects the supposedly root-bound Git diff boundary.** The new environment whitelist removes inherited selectors and ambient configuration, but `_root_bound_git_command()` invokes plain `git` with `cwd=root` and configuration overrides without an explicit `--work-tree=<resolved root>` (`.grok-stack/adaptive_grok/util.py:19-59`, `.grok-stack/adaptive_grok/util.py:164-186`). Git therefore honors `core.worktree` from the selected repository's local `.git/config`. All verifier diff checks use this seam (`.grok-stack/adaptive_grok/verification.py:1742-1778`), so a local configuration value can redirect worktree/index comparison away from the explicit root while selection/object operations still appear healthy. The committed hostile-config regression covers inherited `GIT_CONFIG_COUNT`, `GIT_DIR`, and `GIT_WORK_TREE`, but not repository-local `core.worktree` (`tests/test_verification_doctor.py:1332-1383`). This violates AC-008's explicit-root and configuration-isolation requirement and can produce a false whitespace PASS.

   Minimal reproduction in a private exact-HEAD clone: create an empty foreign directory; run `git config core.worktree <foreign>` in the clone; append `trailing whitespace  ` to the clone root's tracked `VERSION`; call `_git_diff_check(root, 'fast', _git_range_selection(root, None, 'fast'))`. Observed result was `status=pass`, empty details, and `2/2 checks passed`. Running `git --work-tree=<clone-root> diff --check --no-ext-diff -- VERSION` against the same state reported `VERSION:2: trailing whitespace` and exited `2`.

   Acceptance condition: every root-bound Git operation that consults a worktree must explicitly bind it to the resolved supplied root (and fail closed if the root/repository relationship is inconsistent), irrespective of repository-local `core.worktree`. Add a regression using local `.git/config core.worktree=<foreign>` that proves selection, inventories/fingerprint, worktree/index diff checks, and exact-root whitespace detection cannot be redirected. Preserve the new sanitized environment, replacement-ref suppression, bounded diagnostics, and no-follow scanner behavior.

### Minor findings

None.

### Focused evidence

- `git rev-list --parents -n 1 ddd9988e...` and `git rev-list --count cb9af407...ddd9988e...` — candidate remains exactly one non-merge commit directly on the stated base.
- `git diff --check cb9af407...ddd9988e...` — pass; `trust-ci/` base-to-head diff — empty.
- Focused receipt/history/hardening selection: forged identity scope, all scope fields, ambient selectors/config, replacement refs, symlink blob, gitlink rejection, dirty symlink/broken-link/FIFO rejection, named-file replacement race, redacted diff output, transient historical secret, repaired historical whitespace, and normal receipt recording — `Ran 11 tests in 8.599s`, `OK`.
- Private scratch `/tmp/issue218-rereview.huYsVQ` reproduced the exact HEAD and clean fingerprint above. The local `core.worktree` adversarial probe survived as described; scratch was moved to trash afterward.
- Coordinator-provided full verifier on exact HEAD — PASS; Core `83.888s`, Factory PostgreSQL `190.977s`. I did not rerun the broad suite.

### Residual/acceptance boundary

The prior receipt-forgery blocker is genuinely repaired, and the new no-follow file/object and bounded diagnostic paths passed focused review. The final verdict remains FAIL solely because repository-local worktree redirection leaves AC-008 unfulfilled. Local evidence remains non-authoritative; external exact-SHA Trust CI is still required after this blocker is repaired and the candidate is re-reviewed.

## Historical final-review appendix — `de23e5da`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `de23e5dac4cfe9fc8d832078ec867ae05e096db1`, reviewed-tree-modified **no**, verdict **FAIL**.
- Important I-1: `_has_added_whitespace_error()` used unbudgeted `SequenceMatcher(..., autojunk=False)`. Repetitive clean-line probes measured 500/1,000/2,000/4,000 lines at 0.039s/0.169s/0.705s/2.922s and 8,000 lines (16 KiB) at 12.732s, so byte ceilings did not bound comparison CPU across edges or receipt revalidation.
- Minor M-1: the junk-line alignment false-failed an unchanged legacy bad line when surrounding clean lines changed, and also false-failed a clean insertion before that unchanged bad line. Moves and duplicate bad occurrences still had to remain rejected.

## Historical final-review appendix — `f2789117`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `f278911796e843089cff33e2f8e59a963e79ffd8`, tree `5f3275e0eb81e82a68dd8419d18bd8b7b65fae70`, reviewed-tree-modified **no**, verdict **FAIL** with 0 Critical, 1 Important, and 1 Minor finding.
- Important: greedy first-viable clean-anchor selection falsely returned `error` after 38 operations for `A / bad / B / C / D` to `D / A / bad / B / C`; native diff-check had no whitespace diagnostic because the longer stable `A/B/C` order preserves the bad line.
- Minor: `[*anchors, sentinel]` duplicated the full anchor list and empty intervals consumed zero budget. Closure required a bounded non-greedy maximum stable order plus charged, non-copying interval traversal.
