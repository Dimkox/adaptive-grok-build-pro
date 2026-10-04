# Combined independent test review follow-up

Verdict: PASS for the bounded claims and affected seams below; no actionable findings. This is independent test_review evidence, not a qualifying local PR result or external merge authority.

Source: .review-scratch/verify-fast-fail, branch feat/verify-fast-fail, route89578a99758f, change20261004-task-89578a, PR242. Original comparison base: ee3911869419204154e02900e58bf31492ee744c. The actual combined branch diff and surrounding implementation/tests were inspected, including the sandbox fixture repair and the nine source-root wrapper deletions.

Candidate before/after review: HEAD bf506ed6fb2006828de45168b2df95ccd7478e25; fingerprint 833883eefd1897602a77329dfad1b15825c5bba32c77685caaf56b966b31019b; porcelain inventory empty both times. Final identity observation: 2026-10-04T22:25:53Z.

reviewed-tree-modified: no

## Reproduction and resource boundary

Private scratch: /tmp/verify-fast-combined-test.jH8LcPM1/repo, below a reviewer-owned non-sticky mode0700 parent; temporary fixtures/output used its mode0700 tmp child. An independent no-hardlinks clone and detached checkout reproduced the exact committed candidate. Scratch HEAD/fingerprint/status matched the candidate before probes and after restoring every mutant; final git diff --exit-code returned0. No relevant staged/unstaged/untracked source inventory existed to overlay. Candidate reads disabled optional Git locks and Python bytecode; no candidate reports, receipts or artifacts were written.

Resource discovery was recorded privately before route/diff inspection at2026-10-04T22:22:32Z. Topology14physical/28online logical CPUs0-27, inherited effective cpuset0-27, default affinity0,1,8-27 and nproc22; actual v2 membership and all applicable ancestor quotas were checked and no finite quota applied. One bounded child-only widening probe verified affinity0-27/nproc28 under the same bounds. Reviewer allocation<=4workers, with two concurrent positive groups allocated2each; no additional agents. Raw host snapshot remains private in capacity.md.

## Fresh executable claims

Both positive groups ran concurrently in scratch. No full module discovery, live PostgreSQL or containers were invoked.

Command A:

~~~bash
env GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:. TMPDIR=/tmp/verify-fast-combined-test.jH8LcPM1/tmp GROK_TEST_WORKERS=2 GROK_VERIFY_CAPABILITY=repository-sandbox taskset -c 0-27 timeout --signal=TERM --kill-after=3s 177s python3 -m unittest -v tests.test_verification_doctor.FailFastVerificationTests tests.test_verification_doctor.VerificationTests.test_python_pr_requires_factory_postgres_api_and_restart_exit_runner tests.test_verification_doctor.VerificationTests.test_python_pr_skips_factory_postgres_exit_only_in_repository_sandbox tests.test_verification_doctor.VerificationTests.test_python_pr_propagates_local_factory_postgres_exit_failure tests.test_verification_doctor.VerificationTests.test_python_pr_does_not_trust_arbitrary_verifier_capability tests.test_quality_gates.QualityGateTests.test_completed_refusal_does_not_require_future_checks tests.test_python_test_runner.NamedSmokeTests
~~~

Observed exit0, Ran23tests in14.263s, OK. Covered actual refusal dispatch and unexecuted disclosure, retained primary output, source-stability/final QG, valid FAIL receipts versus invalid-authority/source-mutation refusal, allowed skips and successful inventories, ordinary fast compatibility and keep-going safety. Named CLI/API controls exercised repeated targets, required no-record, Core imports, dirty/missing/invalid targets and budgets, timeout, cancellation, changed source and same-tree new HEAD. Existing receipt bytes remained unchanged. The entire fail-fast class passed under inherited repository-sandbox; its new regression required local fake PostgreSQL dispatch and a non-null command inside the fixture, then restoration of the outer sandbox value. Four separate production controls retained exact sandbox skipping, ordinary local dispatch/failure propagation and rejection of an arbitrary capability string.

Command B:

~~~bash
env GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:. TMPDIR=/tmp/verify-fast-combined-test.jH8LcPM1/tmp GROK_TEST_WORKERS=2 taskset -c 0-27 timeout --signal=TERM --kill-after=3s 177s python3 -m unittest -v tests.test_installer.InstallerTests.test_installed_root_hook_aliases_delegate_and_preserve_fallback tests.test_installer.InstallerTests.test_hook_aliases_use_the_inventoried_template_snapshot tests.test_installer.InstallerTests.test_payload_is_sorted_safe_duplicate_free_and_profile_explicit tests.test_structure.StructureTests.test_repository_root_holds_only_canonical_entries tests.test_structure.StructureTests.test_hook_registration_has_required_lifecycle_events
~~~

Observed exit0, Ran5tests in4.079s, OK. Generic and Bitrix payloads each retained all nine literal compatibility names; materialized aliases matched inventoried template bytes/modes, forwarded stdin to canonical hooks and returned the existing missing-canonical JSON, including PreToolUse allow. The unchanged minimal-source snapshot control retained the descriptor-bound bytes/mode after its deliberate post-read mutation. The committed-HEAD root inventory passed with the nine source files absent; lifecycle registration and payload ordering/profile contracts remained valid.

The fixture repair retains the original successful and keep-going inventory assertions. It corrects the fixture environment and adds isolation/restoration coverage rather than weakening expected production behavior. The installer characterization now exercises installed aliases independently of physical source-root files and pins the literal nine-name set. The root inventory still reads git ls-tree HEAD.

## Private mutation probes

All mutants were applied with apply_patch only in private scratch, sequentially, and restored. Commands used the same environment/cwd/affinity/timeout as above with GROK_TEST_WORKERS=4. Mutant commands and observed failures:

M1, retain inherited sandbox capability: replace only the fixture's capability pop with pass. Command:

~~~bash
env GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:. TMPDIR=/tmp/verify-fast-combined-test.jH8LcPM1/tmp GROK_TEST_WORKERS=4 GROK_VERIFY_CAPABILITY=repository-sandbox taskset -c 0-27 timeout --signal=TERM --kill-after=3s 177s python3 -m unittest -v tests.test_verification_doctor.FailFastVerificationTests.test_dispatch_fixture_isolates_and_restores_inherited_sandbox_capability tests.test_verification_doctor.FailFastVerificationTests.test_default_optional_skip_keeps_successful_python_inventory tests.test_verification_doctor.FailFastVerificationTests.test_optional_skips_keep_success_inventory_and_keep_going_collects_failures
~~~

KILLED: exit1,3tests/3failures in0.011s. New regression rejected skip!=pass; both unchanged inventories detected missing factory-postgres-exit dispatch. This independently reproduces the repaired environment leak.

M2, remove virtual alias inventory: filter ROOT_HOOK_SHIMS out of the installer's MANAGED_FILES inventory extension. Command:

~~~bash
env GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:. TMPDIR=/tmp/verify-fast-combined-test.jH8LcPM1/tmp GROK_TEST_WORKERS=4 taskset -c 0-27 timeout --signal=TERM --kill-after=3s 177s python3 -m unittest -v tests.test_installer.InstallerTests.test_installed_root_hook_aliases_delegate_and_preserve_fallback
~~~

KILLED: exit1,1test/2profile failures in0.169s. Literal names<=entries failed for both generic and Bitrix. The replacement characterization detects loss of consumer aliases after physical source wrapper removal.

M3, remove environment restoration: remove only the fixture's patch.dict context while retaining capability removal. Command:

~~~bash
env GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:. TMPDIR=/tmp/verify-fast-combined-test.jH8LcPM1/tmp GROK_TEST_WORKERS=4 GROK_VERIFY_CAPABILITY=repository-sandbox taskset -c 0-27 timeout --signal=TERM --kill-after=3s 177s python3 -m unittest -v tests.test_verification_doctor.FailFastVerificationTests.test_dispatch_fixture_isolates_and_restores_inherited_sandbox_capability
~~~

KILLED: exit1,1test/1failure in0.005s, None!=repository-sandbox at the post-fixture assertion. Restoration is independently executable coverage, not merely a static expectation.

No mutant survived these scoped probes; no blanket mutation-score claim is made.

## Static findings, historical evidence and limits

The exact source diff leaves installer runtime, alias template, canonical hook scripts/configuration, VERSION, release archives and generated views unchanged; hook README prose changes. The architecture edit removes only the nine obsolete NODE-LOCAL-ROUTE-POLICY source paths. Final qualifying verification and the other selected review remain responsible for architecture validation/drift/diagram evidence. This reviewer did not execute those commands, a private committed-wrapper restoration mutant, the complete installer suite, the broad doctor module, full Core/coverage/PostgreSQL qualification, external App checks or delivery operations.

The original review/probes at3c18e9b9da5ef343f0f0d8e11f38986622ed96e5 and partial observations at39dd5dc72976022e25058edf3255dc210c5b0a8b are historical, not fresh combined-head passes. Production verifier/runner/CLI code is byte-unchanged from the original reviewed implementation, but this follow-up relies on the28fresh combined-head tests and3fresh mutants above for its bounded verdict. Previous full local results or App outcomes do not qualify this head.

Source stability is a before/after identity contract, not continuous detection of transient edits restored before comparison. Named subprocess budgets include bounded cleanup afterward, not a strict total wall-clock guarantee. Ten-minute delivery remains unproven and Core/PostgreSQL overlap is not implemented.

After both selected complete reports are persisted, the coordinator must commit/freeze and run the ONE final qualifying local PR gate, with unchanged fail-closed scope, separately from the App-owned exact-head Trust CI and required approvals. This report grants no extra skip or merge authority.
