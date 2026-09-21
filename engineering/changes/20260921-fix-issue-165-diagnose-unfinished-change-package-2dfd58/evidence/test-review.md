# Issue 165 renewed independent test review

Result: **PASS — T165-1 is resolved; no remaining blocking test finding in the reviewed scope.** This is the selected independent `test_reviewer` report for route `2dfd5804553e`. It is local review evidence, not a receipt, external approval, or merge authority.

Reviewed worktree: `/home/pall/grok-projects/adaptive-grok-build-issue-165`; branch `fix/issue-165-interruption-status`; exact HEAD `a946f3e3ac92dfd60ece94437b20406e2edd3959`; actual comparison base `839d3aa26bc90417424d814ee48d8b5cd3be367e`. I read the full implementation diff and surrounding package inspector, lifecycle, strict parser, serializer, receipt, status and Stop/review code, the adopted six acceptance criteria, all focused tests, and the measured repair/full-verification evidence. This renewal was **static only**: no tests, source imports, probes, compilation, lint, Docker, receipt writes, commits or external operations were executed.

The earlier failed review and independent 0.294-second reproduction remain intact in [test-review-first.md](test-review-first.md), SHA-256 `ac4d97d13712b1b8a1db2277eed720dc830ccd53a8174af421fa7d00e221cb42`. The original failure is historical evidence, not erased or relabeled. The sole writer's repaired product was fully tested at `bca409d10d01663ee90dbd083089f41edad0b2bd`; the actual diff from that commit to the reviewed HEAD changes only bootstrap, package state, tasks, and evidence/documentation.

## Resolution of T165-1

The defect crossed two boundaries: raw POSIX bytes became surrogate-bearing Python strings, which the durable UTF-8 writer could not save; merely escaping the JSON would still be rejected by the strict canonical reader. The repair addresses both before persistence. `package_status._filesystem_name()` leaves valid UTF-8 identities as strings and represents other byte names as an explicit `{"encoding":"hex","value":"..."}` object. Both filenames and observed branch names use this conversion. Deduplication and sorting occur on original bytes, so two different byte names cannot collapse into a replacement character or a text escape. The strict canonical parser, shared serializer, receipt validator and lifecycle authority fields remain unchanged.

Three measured regression methods now exercise the actual affected behavior:

- `test_raw_byte_start_persists_distinct_names_and_reloads_through_cli` (`tests/test_package_status.py:407`) creates a raw-byte branch and distinct raw `0xff`/`0xfe` names, literal escape/hex/object-looking names, a replacement-character name and valid Unicode. It invokes the real lifecycle CLI, parses stored state through the strict canonical reader, checks exact byte identities, retries start without package mutation, and invokes the real status CLI with those names still present. It also asserts that direct surrogate JSON remains rejected by the existing strict parser.
- `test_raw_byte_first_implementation_persists_and_resume_keeps_initial_identity` (`:452`) creates raw-byte WIP after a valid initial checkpoint, invokes the real transition CLI, checks persisted state/history and the unchanged initial checkpoint, then performs blocked/resumed transitions and repeated start/status reload without duplicating checkpoints.
- `test_raw_byte_representation_limit_persists_an_unknown_observation` (`:488`) creates a real deep raw-byte path set below Git's count/output caps whose expanded representation would exceed the persistence budget. Both lifecycle checkpoints remain readable, report unknown dirty state, retain their actual HEAD/base, and do not fabricate a clean or zero-ahead observation.

These tests reproduce the former write failure before repair and verify the reader as well as the writer afterward. They are behavioral regressions rather than assertions about which internal helper is called. The representation budget is checked before returning the path set: 4096 input bytes per name and 32768 bytes for the ASCII JSON path representation plus per-entry formatting reserve. Overflow raises a typed observation finding and leaves the dirty state unknown. Two bounded checkpoint path sets and their branch identities remain well below the selected-state file limit.

## Acceptance coverage

| Criterion | Evidence inspected | Review result |
| --- | --- | --- |
| AC-001: bounded, safe package inspection | Draft/active/blocked controls; missing, malformed, duplicate-key, invalid-encoding and oversized selected inputs; traversal, absolute paths, ancestor/leaf symlinks, FIFO, permission denial, aggregate limit and replacement during read; unreferenced evidence is not crawled. | PASS. Real filesystem controls and bounded parser failures prevent silent completeness in the exercised cases. |
| AC-002: additive, nonmutating status | Repeated real CLI calls with runtime absent and with current receipts; fixture inventory compares contents, sizes, modes and mtimes, including index/runtime/bytecode paths. The CLI fixture removes the bytecode-suppression environment variable. An unsafe package path uses a sentinel control. | PASS. The tests exercise the CLI's own no-write protection while preserving the existing status fields and separate receipt gaps. |
| AC-003: named baseline, paths and unknown observations | Stacked branch fixture distinguishes initial checkpoint HEAD from the unchanged older route base. Coverage includes ordinary and raw byte identities, rename/delete/untracked paths, product Markdown, package-only paperwork, missing/invalid/unavailable base, no/unborn/detached Git, malformed or failed queries and count/representation limits. | PASS. T165-1's previously missing durable roundtrip is now covered. Unknown observations cannot become a zero-ahead success in these controls. |
| AC-004: placeholders and explicit accounting | Current standalone markers fail while quoted/fenced/indented/inline examples and arbitrary TODO/TBD prose do not. Missing obligations, empty reasons and missing references fail. `not_run` and recorded failed runs remain separate from passing receipts. | PASS. The focused tests explicitly keep canonical receipt gaps after accounting is complete. |
| AC-005: durable lifecycle observations and recovery | Initial HEAD and route identity, invalid-transition nonmutation, repeated-start inventory equality, first implementation and blocked/resumed deduplication, injected README write failure with pending canonical state and idempotent retry; new raw-byte persistence/readback cases cover both creation and first implementation. | PASS. The former checkpoint serialization failure is closed without weakening the strict reader. |
| AC-006: soft Stop and review preflight | Real Stop subprocesses warn even with no obligations or with current receipts and never block or mark incomplete work completed. The review CLI records an initial pass without circular prerequisites, refuses a later package error without replacing that receipt, and still accepts a failed review. Existing receipt and external authority code is unchanged. | PASS for the bounded local-evidence contract. No new merge-authority claim is introduced. |

## Measured verification, checked as evidence

I read the full captured outputs and independently recomputed the decoded RED/GREEN content hashes and the full-report file hash. I did not rerun their commands.

| Run | Actual result | Evidence binding |
| --- | --- | --- |
| Repair RED, `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_package_status -k raw_byte -v`, 09:40:22–09:40:24 UTC | Exit 1; three failures, zero errors; unittest 1.879 seconds, measured process 2.0907751969934907 seconds. Each failure reaches the real lifecycle CLI's former `UnicodeEncodeError`. | [review-repair-red.log.json](review-repair-red.log.json), decoded SHA-256 `93eb3fa3d930a847c5258f25b228029b9ee47190ea3dac9427f4dfcf42beb756`. |
| Repair GREEN, `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_package_status -v`, 09:43:13–09:43:29 UTC | Exit 0; all 28 tests pass, including the three raw-byte methods; unittest 15.678 seconds, measured process 15.900929602008546 seconds. | [review-repair-green-1.log.json](review-repair-green-1.log.json), decoded SHA-256 `80b85b264eb01353f528d19a8d7224139beb63f1b4c1b12bb30f94e8f5b10c21`. |
| Corrected full PR gate, `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, 10:17:57–10:26:15 UTC | **PASS / exit 0**, profiles `base` and `contracts`; diff check 4/4, spec, architecture, governance, security/SQL scans, Ruff, Bandit, pilot/root/factory units, coverage, PostgreSQL and source stability pass. Workflow artifacts are explicitly skipped because they are unconfigured. | Tested HEAD `bca409d10d01663ee90dbd083089f41edad0b2bd`; tree fingerprint `1a37c3098177239578508680ae2bfa82c326114f4df206ed4d76dcd0a47d2dae`; [full-review-repair-report.json](full-review-repair-report.json) SHA-256 `cdebdb7105546cf5396e91491fea9c04c902b8eaf706e096d80f67046a3b3c7a`, matching the meta/result records. |

The earlier full run at `738ea719d91cf439d3332ce621418dc994e7365b` remains **FAIL** because of raw RED-log trailing whitespace; passing component results from that run were never promoted to an overall PASS. The corrected full result above is a separate actual run on repaired source. Subsequent reports/documentation still require current final receipt binding; this report does not assert that the older tree fingerprint equals the current tree.

## Remaining limits and nonblocking notes

- Raw-name status fixtures assert that receipt gaps remain nonempty, but they create no current passing receipts. That assertion does not independently prove receipt-fingerprint sensitivity to every raw-byte filename mutation. The fingerprint implementation is unchanged and outside this fix; do not cite these tests as proof that a separate fingerprint issue is resolved.
- An available nonancestor baseline, HEAD changing between the final two reads, each exact individual/file/finding-count threshold, and initial-start mirror failure are not separately exercised by the focused suite. The source handles these as bounded/unknown or pending-retry cases; no concrete residual defect was found in this review. Query failure is injected using the existing bounded-runner error, not a fresh timing benchmark of every cap.
- The new raw-byte identity representation and its 4096/32768 limits are described in the adopted architecture and repair plan. The public `docs/package-status.md` guide should also state the string-or-tagged-object shape for `branch` and `dirty_product_paths`; this is a nonblocking documentation clarification for the final paperwork pass.
- Checkpoints remain observations in the current worktree. The tests do not prove cross-host recovery of unpublished files, true crash detection, remote writes, deployed behavior, required signed approval scopes, or the external exact-SHA Trust CI result.

## Current source binding

The combined implementation/test/contract diff against the stated base, limited to the paths below, has SHA-256 `996ce043e04a55cffd50007fc43e1b92cd138bccf000666c46c48885a9b57c00`. File SHA-256 values were recomputed from the reviewed worktree:

```text
b438510389762f4d62ea3dbb0f4d235580e6b1baa7c7fb7ee1d6f477ad912aa6  .grok-stack/adaptive_grok/package_status.py
99586b99387285408f48dbb68b52e20a768c8551e872d3bb4b84d6c62befb886  .grok-stack/adaptive_grok/change.py
7dd3a2acd933f7b4240f44248b773715d30931385e62a2d8c9ca6db89a3058c9  .grok-stack/adaptive_grok/state.py
461b381c637dc0c5cf1ce7f82a2f4d4f1cc39f142f9f19fb473b737391f340dd  .grok-stack/templates/change/evidence/README.md
7be3f2be3fb9ea1e581344388a40da84c3a092945e3fb1a51a024847ad0bf48b  .grok/hooks/stop_gate.py
7bd6e8fd4268dde34c88705a6ed7fcf12dbd9b4b3ff9200ef9191fda44ec4281  scripts/grok_status.py
11b2bd54c307867d775b80b227fda3298722d3cddaa5819b6287458d6f4c46b1  scripts/grok_review.py
87394eaf15e708a06a8b42aa8b25f4b93352ab25ee6e3c31d833eb33fd67d1b0  tests/test_package_status.py
85097a484d15a19f1201056a6935b8e03d57abd7b10a45cdd36381b569f955dd  docs/package-status.md
```

Only this renewed report was written. Shared-memory fact for the coordinator: the corrected regressions cross actual CLI creation, canonical persistence and readback with collision controls and encoded-size overflow; successful path collection alone was insufficient. Keep the original failed review and RED as part of the permanent defect history.
