# Delivery preparation evidence — general_implementer

Historical construction and repair log: every section below records its then-current snapshot, contour and pending work. The current scope and mandatory completion order are in `../change-spec.yaml`, `../architecture.md` and `../release.md`; the e824fb15 repair handoff is `repair-e824fb15-general_implementer.md`. Historical package-only/six-path/linear-algorithm wording below is not a current-tree assertion.

Engineering-time and salary-equivalent assumptions are separated from correctness evidence in [economics.md](economics.md); exact agent-hours are unavailable and are not claimed.

## Exact provenance

- Delivery base/HEAD: `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- Verified development source: `68dfc70c5f58adcc927f731c5d88de09a1b4b242`.
- Source tree: `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`.
- Operation: `git merge --squash 68dfc70c...`; Git reported a clean fast-forward squash and did not update HEAD.
- Immediately after the squash and before adding this package, `git write-tree` returned `0914b5d6...`; `git diff --cached --name-status 68dfc70c...` was empty.

This proves the staged product projection was byte-identical to the verified source. The new route package is the only expected subsequent delta and must be rechecked after staging.

## Boundaries

- No source ref was moved, rewritten, deleted, or committed.
- No network, remote, GitHub, deployment, Daybreak, Trust CI state, or production action occurred.
- The initial squash projection used exact source bytes. The later full-suite compatibility repair is limited to three whitespace-clean templates and two receipt-fixture modules; `mistakes.md` records why the earlier focused matrix missed them.
- Issue #219 Trust CI runner/holdout/digest work is excluded; `trust-ci/**` must remain unchanged.

## Pending gate

All four route analysis reports are present and reconciled. The candidate remains one non-merge commit directly on `cb9af407...`, excludes `trust-ci/**`, and defers full verification and independent reviews until the candidate commit exists. The authorized compatibility repair discovered after that analysis is recorded below.

The typed specification validates with 15/15 criteria mapped. The coordinator recorded the user's explicit local `scope_and_design_approval`, limited to this no-network, no-external-write delivery, and the route advanced through `scoped`, `approved`, and `implementing` via `scripts/grok_change.py`.

## Fast candidate checks

- Focused security/whitespace/range/receipt contour: `Ran 6 tests in 6.867s` — `OK`.
- Ruff on the issue #218 receipt/verifier/test contour: `All checks passed!`.
- Delivery typed spec: `ok=true`, 15/15 criteria mapped, digest `70ba0f2d175766124aec7cf34b252ea786338873e1027180b9870ae21c82650d`.
- Staged diff whitespace check: PASS.
- Current staged-file secret scan: 203 files, zero potential secrets, coverage complete.
- Before the full-suite repair, exact comparison against `68dfc70c...` had zero non-package differences and 17 source-relative package paths. The final candidate adds only the six recorded compatibility paths outside this package.
- Exact comparison against `cb9af407...`: zero `trust-ci/**` changes.

Full `grok_verify`, independent reviews, final receipts, external Trust CI, and merge remain pending after this one-commit candidate is created.

## Full-suite compatibility repair

The first full-suite attempt on candidate `4da48a0d...` exposed three compatibility failures. A fresh generated package inherited four whitespace-only empty bullets from the source templates, so the new chain hygiene preflight correctly failed and blocked `python-unittest`; two legacy fixtures also fabricated verification PASS receipts without the now-required closed `scan_scope`.

- RED: the three reported selectors failed in 2.70s. After converting the two receipt fixtures to the existing closed-scope helper and adding a direct generated-commit whitespace assertion, the same command had one expected template failure and two passes in 6.39s.
- GREEN: removing only the four template trailing spaces produced `3 passed in 14.66s`.
- Broader contour: `tests/test_change_receipts.py tests/test_hooks.py` exposed one more scanless Stop fixture after 77 passes and 116 subtests; migrating that fixture through the same helper yielded `4 passed in 17.65s` on the exact repaired selectors.
- Final affected-module contour: `78 passed, 116 subtests passed in 91.22s`.

The repair does not weaken `scan_scope` validation. It makes newly generated packages compatible with the full-chain whitespace contract and makes compatibility tests obtain verification evidence through the closed-scope path.

## Independent-review security repair

The first code/test/security review wave bound to `cdad4de5...` is preserved with FAIL verdicts. It proved that identity-only scopes could forge coverage counters, graph and diff commands inherited ambient Git controls, unsupported object/worktree types could be skipped as complete, and raw `git diff --check` output could disclose a secret-bearing source line.

- RED forged-scope contour: 4 failures, 1 pass, and 2 passing status/worktree subtests in 2.43s.
- RED combined four-finding contour: 10 failures, 1 pass, and 4 subtests in 4.04s; split mode probes independently reproduced symlink, gitlink, dirty symlink, broken-link, and FIFO gaps.
- GREEN new contour: 8 selectors and 12 subtests passed in 3.77s.
- GREEN focused existing receipt/history contour: 21 selectors and 16 subtests passed in 26.03s.

The repair retains schema v2 and `adaptive-grok.verification-scan/v1`: it recomputes full coverage for stored PASS validation, routes scan-boundary Git commands through a hardened root-bound seam, scans committed symlink blobs, rejects gitlinks and unsafe/racing worktree paths, and emits fixed metadata-only diff diagnostics. At that point the prior local scope/design record was stale; the coordinator subsequently refreshed the local gate for exactly the four reviewed findings. Full verification and fresh reviews remain pending.

## Core-collection compatibility repair

The next full-core attempt passed preflight but stopped during collection because `_policy_legacy.py` still imports the established `_GIT_REPOSITORY_SELECTORS` util symbol removed during Git-seam hardening. The direct import reproduced the exact `ImportError`; restoring the two-name compatibility tuple fixed import and all 1,042 core test collections without weakening the hardened environment.

- RED direct import: exit 1, `cannot import name '_GIT_REPOSITORY_SELECTORS'`.
- GREEN direct import and human-gate collection: import exit 0; 14 tests collected.
- GREEN policy/human-gate contour: 43 passed and 8 subtests in 10.67s.
- Initial util contour: 62 passed and 65 subtests, with five failures caused by mocks that assumed a fixed pre-hardening Git argv offset.
- GREEN semantic-subcommand mock contour: 2 passed and 4 subtests in 0.41s; full util module 20 passed and 61 subtests in 7.82s.
- GREEN core collection: 1,042 tests collected in 1.08s.

## Diff-check confidentiality assertion repair

The subsequent full-core run reached execution and failed only two legacy assertions after 1,002 passes in 66.87s. Both tests still expected raw `git diff --check` output even though the reviewed confidentiality repair intentionally exposes only bounded `diff-check-failed` metadata.

- RED exact selectors: 2 failed in 1.04s on the obsolete raw-output and `exit=N:` expectations.
- GREEN exact selectors: 2 passed in 0.88s after asserting empty stdout/stderr, sanitized paths, exact metadata code, bounded nonzero exit messages, JSON-safe escaped non-UTF-8 paths, and absence of source/raw diagnostic text.
- GREEN full owning module: 121 passed and 65 subtests in 209.51s.

This repair changes tests and evidence only; the confidentiality-hardened verifier behavior is unchanged.

## Final I-1 repository-policy repair

The bounded re-review of `ddd9988e...` found two remaining configuration bypasses: repository-local `core.worktree` redirected worktree probes, while local `core.whitespace` and tracked `-whitespace` attributes suppressed committed and endpoint whitespace findings.

- RED hostile repository contour: the root-redirection test and both committed-policy subtests false-passed (`3 failed, 1 passed in 1.01s`).
- RED endpoint attribute contour: worktree and index subtests both false-passed (`2 failed, 1 passed in 0.78s`).
- RED receipt revalidation addition: both hostile committed-policy subtests showed the closed-scope predicate still accepted a whitespace-bearing chain (`2 failed, 1 passed in 0.99s`).
- GREEN adversarial contour: 4 tests and 4 subtests passed in 1.49s.
- GREEN focused diff/history contour: 15 passed, 109 deselected, and 10 subtests passed in 6.38s.
- GREEN util fingerprint contour: 20 passed and 61 subtests passed in 7.44s.
- GREEN receipt recomputation contour: 3 passed and 5 subtests passed in 3.37s.

The Git command seam now resolves and binds both the supplied root's Git directory and worktree. Whitespace classification uses bounded raw old/new bytes for committed, index, and worktree changes, rejects unsafe inventory/content uncertainty, revalidation rejects historical whitespace findings, and every emitted diagnostic remains metadata-only.

## Sequence-aware whitespace repair

Final code review reproduced a surviving move case under tracked `* -whitespace`: `bad  \nclean\n` became `clean\nbad  \n`, but the file-wide occurrence counter treated the identical bad bytes as unchanged and reported PASS.

- RED exact reorder plus occurrence matrix: 3 failures, 1 pass, and 3 passing subtests in 0.71s; the real chain, reordered case, and reordered-duplicate case all survived.
- GREEN exact selectors: 2 passed and 5 subtests in 0.45s.
- GREEN requested hostile/diff/history contour: 17 passed, 109 deselected, and 15 subtests passed in 7.00s.

The replacement used deterministic `SequenceMatcher(..., autojunk=False)` over split lines whose source blobs/files retained the existing 2 MiB per-object bound, and treated whitespace-invalid lines as non-anchoring junk. Unchanged and removed duplicates remained compatible, while newly added, reordered, and reordered-duplicate bad occurrences were classified as additions; diagnostics remained metadata-only. Final review subsequently showed that the algorithmic availability risk and legacy-line compatibility were not acceptable; that historical implementation is superseded below.

## Linear budgeted whitespace-comparison repair

Final exact-SHA reviews of `de23e5dac4cfe9fc8d832078ec867ae05e096db1` remained FAIL. Repetitive clean-line probes grew from 0.039s at 500 lines to 12.732s at 8,000 lines/16 KiB, proving that the per-object and aggregate byte ceilings did not bound `SequenceMatcher` CPU. Review also reproduced false failures for an unchanged legacy bad line surrounded by changed clean context and for a clean insertion before that line; release review found the package inventory omitted `test_util_fingerprint.py` and `decisions.md`.

- RED: the three-selector compatibility/budget/preservation command ran in 1.004s and failed three assertions: both legacy compatibility rows returned `True`, and an 8-operation chain budget produced `chain-whitespace` instead of structured incomplete evidence. The staged/unstaged moved-and-duplicate matrix already passed and remains preservation coverage.
- GREEN: the same three selectors passed in 1.019s. Two additional aggregate/endpoint budget selectors passed in 0.179s.
- GREEN hostile/history contour: the final 13-test run passed in 4.260s, covering root binding, hostile config/attributes, committed/intermediate/staged/unstaged whitespace, moved and duplicate occurrences, legacy compatibility, both structured exhaustion paths, and metadata-only diagnostics.
- GREEN receipt/history revalidation contour: 5 tests passed in 3.607s, covering forged scan scope, coverage/completion mutations, add/delete secrets, commit bounds, and merge-parent traversal.
- Read-only repetitive probe: 500/1,000/2,000/4,000/8,000/16,000 lines completed in 0.0019/0.0037/0.0075/0.0152/0.0291/0.0575s while consuming 2,012/4,012/8,012/16,012/32,012/64,012 explicit operations. Timing is observational only; the deterministic tests assert the operation counter and typed exhaustion rather than wall time.

The `f2789117` classifier contains no pairwise dynamic program or `SequenceMatcher`. It indexes clean-line positions once, consumes those positions greedily as anchors, and checks bad-line subsequences only within the resulting disjoint intervals. Each line/position/occurrence is visited a constant number of times under one shared 2,000,000-operation budget. Final review subsequently found the greedy anchor choice incorrect; that historical implementation is superseded below.

## Maximum monotone anchor and production-wiring repair

Final reviews of `f278911796e843089cff33e2f8e59a963e79ffd8` left security at PASS but code, test, and release at FAIL. The exact counterexample `A / bad / B / C / D` to `D / A / bad / B / C` consumed 38 operations and falsely returned `error`: the greedy first anchor selected moved `D` and discarded the longer stable `A/B/C` order even though native `git diff --check` emitted no whitespace diagnostic. Reviews also found that direct aggregate-budget tests did not prove the chain and endpoint callers retained the shared budget.

- RED classifier/chain/wiring command: 4 tests ran in 0.625s with 2 failures; the direct counterexample returned `True` instead of `False`, and its real chain emitted `chain-whitespace` for `stable-order.txt`. Both wiring tests passed on the correct baseline.
- GREEN exact new contour: 4 tests passed in 0.648s after maximum monotone anchor selection.
- Mutation RED, chain reset inside loop: the exact wiring test failed in 0.222s because scope was `complete` instead of `incomplete`.
- Mutation RED, endpoint shared-budget omission: the exact wiring test failed in 0.193s because the result was `pass` instead of `fail`.
- GREEN focused hostile/history/property contour: 16 tests passed in 4.896s, including unique and repeated anchors, moved and duplicate bad occurrences, counterexample chain behavior, both aggregate wiring paths, hostile attributes/config, redaction, and intermediate history.
- Repetitive equal-count LIS probe: 500/1,000/2,000/4,000/8,000/16,000 lines completed in 0.0039/0.0079/0.0164/0.0354/0.0594/0.1177s and consumed 8,526/18,015/37,992/79,945/167,850/351,659 explicit operations. Timing is observational; deterministic tests assert the operation counter and typed exhaustion.

The repair occurrence-tags clean lines only when their old/new multiplicities agree, maps their new order to old positions, and reconstructs a longest increasing subsequence with a custom binary search that charges every comparison to the shared budget. Each line is indexed a constant number of times and each candidate performs at most `O(log n)` charged comparisons, so time is `O(n log n)` and space `O(n)` inside the existing byte bounds and the 2,000,000-operation aggregate ceiling. Interval traversal uses an index plus a sentinel branch instead of copying `[*anchors, sentinel]`, and charges even empty intervals. Budget exhaustion remains metadata-only incomplete evidence. Full verification and replacement independent reviews remain pending; no closure is claimed.
