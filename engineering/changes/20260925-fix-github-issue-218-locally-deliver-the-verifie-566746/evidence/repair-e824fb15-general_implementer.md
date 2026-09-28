# Bounded repair handoff — e824fb15 review failures

Date: 2026-09-26 UTC. Route `566746aef130`; sole write owner `general_implementer`. Candidate root `/home/pall/grok-projects/adaptive-grok-build-issue218-delivery`. HEAD remains `e824fb1551ff37ab647c52b00a1fce38ede79213`, sole parent `cb9af4073ba6c3d515145164d771c75ebdfa3224`; this handoff is an uncommitted development tree, not a completion/review receipt.

## Preserved findings and scope

The exact four reviewer reports are preserved as `review-{code,test,security,release}-e824fb15-FAIL.md`; `cmp` against all four out-of-band originals exited 0. The lifecycle tooling transitioned `reviewing` → `implementing`, preserving earlier history and reports.

The original eleven post-source repair paths remain as enumerated in `../architecture.md`. Requested dated release corrections add only `README.md` and `START_HERE.md`, making thirteen non-package paths plus this active package. Source-relative inventory, including untracked evidence, reports `non-package paths: 13`, `out-of-scope: []`. Base-relative `trust-ci`, `.github/workflows`, `packages`, `VERSION` and `architecture` diff is empty. The source commit/tree and all source branches remain unchanged.

## Root causes and changes

1. Equal-count rank tagging discarded every occurrence of a surviving clean value when its multiplicity changed. This erased move boundaries. `_longest_clean_anchors` now returns incomplete for ambiguous unequal surviving multiplicities in a changed interval containing bad lines; it retains the existing budgeted maximum-monotone order for unambiguous cases. Prefix/suffix compatibility and existing legacy-context cases remain green. The incomplete diagnostics state ambiguity or operation exhaustion and contain no source lines.
2. `_load_git_blob_contents` requested the full object body batch before enforcing sizes. It now validates the complete metadata inventory, identity/type and per-blob/aggregate sizes first; no body is requested on over-limit input. Body headers must exactly match the preflight sizes.
3. `_secret_scan` applied only a per-file ceiling. It now uses one path/byte budget across all supplied worktree files. Paths are charged before reader calls, and safe descriptor sizes are reserved before reads. Reads stay within that reservation; the existing descriptor/name/ancestor identity checks remain after reading. Limit exhaustion stops scanning and marks coverage incomplete. Independent closed-scope recomputation enforces the same limits.
4. Typed scope, requirements, architecture, release plan, tasks, test plan and evidence accounting now describe actual post-source repairs and the mandatory committed-tail order. Previous implementation sections and checkpoint accounting are explicitly historical. Current accounting preserves the latest independent FAIL outcomes and states that new verification/reviews are pending.

`mistakes.md` records the technical root causes and the explicitly requested controller mistake: treating the 211-file candidate as final prematurely, running an expensive verifier before adversarial contours closed, and an unbounded four-review wave causing 22 minutes of review churn with little visible progress. `decisions.md` records the now-tested fail-closed ambiguity and pre-read admission pattern.

## Exact RED command and observed output

Before any production repair, ran:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_unequal_clean_multiplicities_never_erase_bad_line_moves \
  tests.test_verification_doctor.VerificationTests.test_hostile_attributes_cannot_hide_unequal_clean_count_moves \
  tests.test_verification_doctor.VerificationTests.test_closed_scope_rejects_committed_unequal_clean_count_move \
  tests.test_verification_doctor.VerificationTests.test_endpoint_blob_limits_precede_all_content_retrieval \
  tests.test_verification_doctor.VerificationTests.test_worktree_secret_scan_enforces_shared_bytes_before_reading \
  tests.test_verification_doctor.VerificationTests.test_worktree_secret_scan_enforces_shared_path_budget \
  tests.test_verification_doctor.VerificationTests.test_scan_scope_recomputation_rejects_worktree_aggregate_exhaustion
```

Observed exit 1:

```text
Ran 7 tests in 2.074s
FAILED (failures=14)
```

The fourteen expected assertion failures were:

- Two direct reviewer fixtures: `AssertionError: 'clean' == 'clean'`.
- Six real hostile-attribute cases (both fixtures, unstaged/staged/committed): `AssertionError: 'pass' != 'fail'`, with `fast` gate context.
- Committed closed-scope revalidation: `AssertionError: True is not false`.
- Oversized endpoint blob and aggregate-overlimit endpoint blobs: `AssertionError: Lists differ: [['cat-file', '--batch']] != []`, message `over-limit bodies must never be requested`.
- Shared worktree byte and path limits: `AssertionError: 'pass' != 'fail'`.
- Worktree aggregate scope recomputation: `AssertionError: True is not false`.

Both exact byte pairs were used: `bad  \nA\nA\nA\nB\n` → `A\nA\nA\nA\nbad  \nB\n`, and `A\nbad  \nA\nB\n` → `A\nA\nA\nbad  \nB\n`. Endpoint size limits were deliberately lowered to 16 bytes for bounded proofs: one 17-byte object and two distinct 12-byte objects. The worktree byte probe used two 12-byte files and a 16-byte shared limit. The path probe used three files and a one-path limit. Real Git/file operations remained active, with observers at the body-retrieval/read boundary.

## Exact GREEN commands and results

After the ordering repair:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_unequal_clean_multiplicities_never_erase_bad_line_moves \
  tests.test_verification_doctor.VerificationTests.test_hostile_attributes_cannot_hide_unequal_clean_count_moves \
  tests.test_verification_doctor.VerificationTests.test_closed_scope_rejects_committed_unequal_clean_count_move \
  tests.test_verification_doctor.VerificationTests.test_added_whitespace_classifier_tracks_duplicate_occurrences_and_order \
  tests.test_verification_doctor.VerificationTests.test_chain_whitespace_uses_longest_stable_clean_order \
  tests.test_verification_doctor.VerificationTests.test_chain_wires_one_aggregate_whitespace_budget_across_edges \
  tests.test_verification_doctor.VerificationTests.test_endpoint_wires_one_budget_across_worktree_and_index
```

`Ran 7 tests in 2.322s` / `OK`, exit 0. This includes both fast and PR gates for all six real Git cases.

After endpoint metadata preflight:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_endpoint_blob_limits_precede_all_content_retrieval \
  tests.test_verification_doctor.VerificationTests.test_hostile_attributes_cannot_hide_unequal_clean_count_moves \
  tests.test_verification_doctor.VerificationTests.test_endpoint_wires_one_budget_across_worktree_and_index
```

`Ran 3 tests in 1.994s` / `OK`, exit 0. Both over-limit cases requested no body batch.

After shared worktree budgeting:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_worktree_secret_scan_enforces_shared_bytes_before_reading \
  tests.test_verification_doctor.VerificationTests.test_worktree_secret_scan_enforces_shared_path_budget \
  tests.test_verification_doctor.VerificationTests.test_scan_scope_recomputation_rejects_worktree_aggregate_exhaustion \
  tests.test_verification_doctor.VerificationTests.test_worktree_scan_rejects_symlinks_broken_links_and_fifos \
  tests.test_verification_doctor.VerificationTests.test_worktree_scan_detects_named_file_replacement_during_read
```

`Ran 5 tests in 0.302s` / `OK`, exit 0; aggregate bytes stay below the limit and path exhaustion stops further reader calls.

Complete affected-module sweep after all production changes:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_verification_doctor tests.test_change_receipts tests.test_util_fingerprint
```

`Ran 205 tests in 289.966s` / `OK`, exit 0. This is the three affected modules, not the full PR verifier or a current completion claim.

Additional checks:

```bash
python3 -m ruff check .grok-stack/adaptive_grok/verification.py tests/test_verification_doctor.py
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_spec.py validate --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_gate.py status
git rev-list --parents -n 1 HEAD
git rev-list --count cb9af4073ba6c3d515145164d771c75ebdfa3224..HEAD
```

Ruff: `All checks passed!`; whitespace: exit 0 with no output; spec: `ok=true`, 22/22 criteria mapped; gate: approved against digest `d2cc86307c68ffd2a0f5b0bf2482b75e08a6ea1698175419ae918eab9a9971de`; topology: `e824fb1551ff37ab647c52b00a1fce38ede79213 cb9af4073ba6c3d515145164d771c75ebdfa3224` and count `1`.

The scope decision was recorded through `grok_gate.py decide` from the existing explicit user instruction to continue #227 through #0. It is local workflow evidence only and creates no external operation grant, human security signature or merge authority.

## Residual risks, rollout and next handoff

Ambiguous repeated-clean changes may now require the user to remove legacy bad whitespace or restructure the edit; they deliberately return incomplete instead of guessing clean. The algorithm is not claimed equivalent to every Git diff algorithm. Byte/path limits bound these scan phases, not total process memory; Git/object administration and the executable remain trusted. No production-scale stress, exhaustive filesystem race schedule or fresh independent review is claimed by the writer.

No service, dependency, API/schema migration, production write or feature flag is introduced. Before external delivery, retain or abandon the isolated branch; after delivery, rollback is a separately reviewed revert of the one commit. Existing source branches/artifacts remain recoverable and unchanged.

The focused evidence supports handing this candidate to the coordinator for preliminary full verification and renewed independent review. Lifecycle remains `implementing`; no `ready` transition, self-review, commit, completion receipt, full PR verifier, fetch/network/GitHub call, tag/release/deploy or external write was performed by this repair owner. The remaining order is preliminary full `--no-record` → four reviews → persist reports and tracked accounting → ready → amend sole candidate → final recording verification → verification PASS receipt → review receipts → read-only zero-gap status. External exact-SHA Trust CI and required approvals remain separate.
