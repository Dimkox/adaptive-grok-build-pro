# Sole-writer implementation handoff: contour A

Historical implementation evidence: this report describes the source bytes before the output-file-close repair. Independent code and test reviews failed on HEAD 30297838c1a08a0ebe3944af07dfb69968202587 because TemporaryFile context exits could replace completed results or cancellation. The complete reports are preserved in code-review-initial-fail.md and test-review-initial-fail.md; fresh repair evidence and limits are in [output-close-repair.md](output-close-repair.md). Prior GREEN results below do not verify the repaired candidate.

Route c2333ca04e25; isolated branch fix/v211-verifier-recovery; initial HEAD/base e5856acfd4bc7a186f40a740b54ec86459462db5. Source material was inspected path-by-path only; no historical commits, trees, change packages, reviews or receipts were imported. Only issue-226 deltas dde3a2601c5b68d3da1b26e2434ba00b9ba83007 / 01b14df68f39feffa93e23b285f8f1825719850a were inspected; issue 227 is excluded. Old dirty trees remain untouched. No subagents were spawned by the writer.

Implemented: main-thread shared first-signal cancellation; result-carrying signal exits; bounded TERM/KILL/reap of new-session-owned children; cleanup errors separate from completed exit codes; incremental Python/Core/npm/composer check retention; terminal verifier report preservation; stdout-error stderr fallback and failed publication receipt; atomic file/replace/directory durability; old-pass retirement on tested faults; optional exact HEAD binding and same-tree new-HEAD staleness. Scope selection, verifier modes, factory inventory and deployed external trust are unchanged.

Product inventory and tested SHA256 bytes:

- .grok-stack/adaptive_grok/python_test_runner.py: 7d87f6bbf94e6fb141fa0156e438694d4f8c383632399290a72f2def5e7483c5
- .grok-stack/adaptive_grok/verification.py: 4bbf809cc97e628694a1cd933485eecc74d17379672b5179197b4bb4a13f2434
- .grok-stack/adaptive_grok/receipts.py: 923057667277b8a31425f650bf548d6fb2d463cae3a72c2ba2d839f67d72dd2a
- scripts/grok_verify.py: b0ce3c5e371c54ac0bd041818731e644151de32f5a30abd2e402a2aae6751db2
- tests/test_verifier_recovery.py: ea4a05d38846b9d068232a63358a07e9fc527fc56664f1cd731bc83995f3e6d1

Workflow-only edits are this concrete package and the useful decisions.md/mistakes.md learning entries. VERSION, PROJECT_STATE and release artifacts are not changed by this contour.

Fresh RED evidence

- `taskset -c 0-1 env GROK_TEST_WORKERS=2 python3 -m unittest tests.test_verifier_recovery -v`: 10 tests, 9 failures/11 errors, 9.922s. Missing cancellation/report preservation, stale pass after write/fsync/replace faults, lost child result and unguarded receipt exceptions were reproduced. An earlier unsafe signal baseline exited143; the corrected fixture produced deterministic failing assertions and is recorded in mistakes.md.
- Targeted `python3 -m unittest` controls for stdout publication, completed Core scratch cleanup and malformed coverage: 3 tests/3 errors, 0.414s; OSError publication/cleanup replaced reports and list-shaped JSON escaped as TypeError.
- Same-tree new-head control: 1 failing assertion, 0.410s; the prior receipt still qualified.
- npm/Core-coverage cancellation retention controls: 2 failing assertions, 0.561s; prior failure/output was lost.
- Completed-pass cleanup control: 1 failing assertion, 0.105s; the actual completed exit0 was replaced by1.
- Report-publication old-pass/cancellation controls: 2 failing assertions, 0.916s; publication retained pass receipt and returned0 after SIGTERM.

Fresh GREEN evidence

- `taskset -c 0-1 env -u GROK_TEST_WORKERS python3 -m unittest tests.test_verifier_recovery -q`: 20 tests PASS, 9.720s.
- `taskset -c 0-1 env -u GROK_TEST_WORKERS python3 -m unittest tests.test_python_test_runner tests.test_verification_doctor tests.test_change_receipts tests.test_verifier_recovery -q`: 172 tests PASS, 306.770s. No runtime file changed after this command started. This is focused implementation evidence on the bytes above, not full PR completion.
- `ruff check .grok-stack/adaptive_grok/python_test_runner.py .grok-stack/adaptive_grok/verification.py .grok-stack/adaptive_grok/receipts.py scripts/grok_verify.py tests/test_verifier_recovery.py`: All checks passed.
- `python3 scripts/grok_spec.py validate engineering/changes/20261002-fix-verifier-lifecycle-and-cancellation-preserve-c2333c/change-spec.yaml`: ok=true, no errors; all7 typed criteria/invariants/forbidden outcomes mapped; spec digest b68b0f980ae7d8a51f755060bd2210fa2c1ff8bd17cc2ffcccdb5015f4c932a3 (draft validation).
- The same spec validation with `--gate` also passed with no errors and all7 entries mapped, at the identical digest.
- `git diff --check`: no findings.

Failed/contaminated command, not omitted or counted as GREEN: the first existing-suite command set GROK_TEST_WORKERS=2 globally and ran152 tests in296.191s with three failures: test_repo_root_without_optin_keeps_legacy_verifier_path, test_coverage_fail_under_on_tiny_pr_fixture, and test_coverage_skip_when_missing_in_pr_mode. The global override changed the path those fixtures test; all three passed after unsetting it (combined with17 recovery tests:20 tests,23.252s), then the complete172-test command above passed. Test fixture worker selection is now respected within the two-CPU allocation.

Limits and next steps

No full PR verifier, fresh independent reviews, external writes, merge, deploy, tag or release was performed by this writer. Controller owns those gates. D's early preflight integrates inside _verification_run and record=False must retain failed checks with evidence_status=not_recorded. Source changes or head/base changes require fresh controller verification/receipts.

Cleanup bounds assume the child group remains the new session owned by execute; OS inability to signal/reap is reported as cleanup_error and never qualifies successful consumers. A filesystem that refuses both publication and invalidation can leave unreadable/unretirable state; the report remains failed. If both stdout and stderr fail, the CLI can retain only its nonzero exit, not an emitted report. Process death outside installed handlers is not durable evidence.

Controller instructed merge of actual origin/main 63799f8760d3a55028d83ab5ff0116ececf8f7d1 after the first scoped commit. Exact resulting identities are returned out-of-band in the final handoff; unchanged focused tests are not rerun solely for a source-disjoint base merge.
