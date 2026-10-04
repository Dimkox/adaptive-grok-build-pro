# Independent code review — combined PR242 follow-up

Verdict: PASS for the bounded independent review; no blocking findings. Final full verification and external exact-head qualification remain pending.

Route89578a99758f; change engineering/changes/20261004-task-89578a; source <repo>/.review-scratch/verify-fast-fail; branch feat/verify-fast-fail.
Comparison base: ee3911869419204154e02900e58bf31492ee744c.
HEAD before/after: bf506ed6fb2006828de45168b2df95ccd7478e25.
Candidate fingerprint before/after: 833883eefd1897602a77329dfad1b15825c5bba32c77685caaf56b966b31019b.
Git inventory before/after: clean.
reviewed-tree-modified: no

## Identity, isolation and scope

Exact committed snapshot reproduced using `git clone --quiet --no-hardlinks --no-local <source> /tmp/grok-code-combined.c0wxmJ/candidate`; scratch matched candidate HEAD/fingerprint before probes and after restoration. Private parent, candidate and TMPDIR /tmp/grok-code-combined.c0wxmJ/tmp were0700. Fresh startup discovery at2026-10-04T22:22:18Z recorded privately in capacity.md:14physical/28logical CPUs, inherited cpuset0-27, no finite ancestor quota observed; one child-only widening probe verified28. Review allocation capped at4 CPUs/workers, with independent controls split0-1/2-3. No extra agents or candidate writes.

Inspected complete branch inventory/base diff and changed implementation/tests/specifications, both implementation reports and surrounding verifier/installer code. The combined scope includes original fail-fast/named observations, fixture isolation and exactly nine physical source-root wrapper deletions. Installer, template, canonical hook/configuration, VERSION, packages and generated-view bytes are unchanged against the base; verifier runtime is unchanged since the original reviewed3c18e9b9da5ef343f0f0d8e11f38986622ed96e5. Those byte-comparison commands returned empty output. Existing delivery and rollback boundaries remain intact.

The installer appends virtual MANAGED_FILES inventory independently of physical wrapper existence, excludes alias source reads and synthesizes aliases from the descriptor-validated template bytes/mode. The new characterization exercises all nine aliases for generic and Bitrix consumers, stdin delegation and exact fail-open JSON fallback. Structure still reads committed HEAD. The architecture edit removes only nine obsolete route-policy repository paths. Fixture patch.dict temporarily clears only the inherited capability and restores the environment; unchanged production still skips PostgreSQL only for exact repository-sandbox.

## Fresh executed controls

All Python commands used these exact environment assignments:
`GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack:. TMPDIR=/tmp/grok-code-combined.c0wxmJ/tmp`.
Every control used `timeout --kill-after=5s 180s`; prefixes below specify remaining environment and affinity. These are observations, without verification receipts or scope admission.

1. `env <assignments> GROK_TEST_WORKERS=2 GROK_VERIFY_CAPABILITY=repository-sandbox taskset -c 0-1 timeout --kill-after=5s 180s` followed by:
```bash
python3 -m unittest -q \
tests.test_verification_doctor.FailFastVerificationTests \
tests.test_quality_gates.QualityGateTests \
tests.test_verifier_recovery.VerifierRecoveryTests.test_node_cancellation_keeps_prior_command_failure \
tests.test_verifier_recovery.VerifierRecoveryTests.test_cancellation_during_coverage_preserves_completed_core_failure \
tests.test_python_test_runner.NamedSmokeTests.test_named_smoke_uses_core_imports_and_never_records_receipt \
tests.test_installer.InstallerTests.test_installed_root_hook_aliases_delegate_and_preserve_fallback \
tests.test_installer.InstallerTests.test_hook_aliases_use_the_inventoried_template_snapshot \
tests.test_structure.StructureTests.test_repository_root_holds_only_canonical_entries \
tests.test_verification_doctor.VerificationTests.test_python_pr_requires_factory_postgres_api_and_restart_exit_runner \
tests.test_verification_doctor.VerificationTests.test_python_pr_skips_factory_postgres_exit_only_in_repository_sandbox \
tests.test_verification_doctor.VerificationTests.test_python_pr_propagates_local_factory_postgres_exit_failure \
tests.test_verification_doctor.VerificationTests.test_python_pr_does_not_trust_arbitrary_verifier_capability
```
Observed exit0,33tests10.652sOK. Claims probed: completed-result QG policy, refusal boundaries/unexecuted disclosure, permitted skips, keep-going safety, stable failure receipts and source-mutation refusal, Node/Composer boundaries, retained Core coverage cancellation, named Core imports/no receipt, installed alias/template binding, committed-root inventory and exact production capability boundary.

2. `env -u GROK_VERIFY_CAPABILITY <assignments> GROK_TEST_WORKERS=2 taskset -c 2-3 timeout --kill-after=5s 180s python3 -m unittest -q tests.test_verification_doctor.FailFastVerificationTests`: exit0,13tests3.775sOK in ordinary environment.

3. `env <assignments> GROK_TEST_WORKERS=2 taskset -c 2-3 timeout --kill-after=5s 180s python3 scripts/grok_architecture.py`, independently with `validate --json`, `drift --json` and `diagram --check --json`: each exit0/ok true; validate/drift findings empty and diagram mismatches empty for all five checked-in views. `GIT_OPTIONAL_LOCKS=0 git diff --check ee3911869419204154e02900e58bf31492ee744c..HEAD`: exit0, empty output.

## Mutation probes and restoration

Both probes used apply_patch exclusively in private scratch. Neither altered the reviewed candidate.

M1: Change installer alias selection from virtual inventory to require `(source / relative).is_file()`. With `env <assignments> GROK_TEST_WORKERS=4 taskset -c 0-3 timeout --kill-after=5s 180s python3 -m unittest -q tests.test_installer.InstallerTests.test_installed_root_hook_aliases_delegate_and_preserve_fallback`, exit1/one test0.165s/two profile assertions failed because aliases disappeared. KILLED; demonstrates coverage of the deletion/virtual-inventory seam.

M2: After restoring M1, remove the fixture's `os.environ.pop('GROK_VERIFY_CAPABILITY', None)`. With `env <assignments> GROK_TEST_WORKERS=4 GROK_VERIFY_CAPABILITY=repository-sandbox taskset -c 0-3 timeout --kill-after=5s 180s python3 -m unittest -q` and these exact targets:
```text
tests.test_verification_doctor.FailFastVerificationTests.test_dispatch_fixture_isolates_and_restores_inherited_sandbox_capability
tests.test_verification_doctor.FailFastVerificationTests.test_default_optional_skip_keeps_successful_python_inventory
tests.test_verification_doctor.FailFastVerificationTests.test_optional_skips_keep_success_inventory_and_keep_going_collects_failures
```
exit1/three tests0.011s/three failures: skip versus pass and missing PostgreSQL dispatch. KILLED; reproduces the repaired fixture defect without weakening production.

After restoring M2, the same sandbox prefix ran those three targets plus both InstallerTests targets listed in control1: exit0,five tests9.943sOK. No surviving or inconclusive mutants.

Finally, clean scratch ran the same sandbox prefix with:
```bash
python3 scripts/grok_verify.py --mode fast --no-record \
--test tests.test_installer.InstallerTests.test_installed_root_hook_aliases_delegate_and_preserve_fallback \
--test tests.test_verification_doctor.FailFastVerificationTests.test_dispatch_fixture_isolates_and_restores_inherited_sandbox_capability \
--test tests.test_structure.StructureTests.test_repository_root_holds_only_canonical_entries \
--budget 30 --json
```
Exit0; three tests10.407sOK, subprocess10.933s; exact HEAD/fingerprint stable, terminal completed, evidence_status not_recorded. Scratch runtime retained only .gitkeep.

## Limits and handoff

Unexecuted: full PR/release suites, real PostgreSQL integration, broad installed-hook lifecycle, dedicated landing controls, external Trust CI and operational delivery. Static compatibility/authority/rollback findings above are inspection claims, not additional executed qualification. Original review at3c18e9b9da5ef343f0f0d8e11f38986622ed96e5, earlier39dd5dc observations and prior local/external results are historical only; none replaces fresh final evidence. No server environment was inspected. Named budget bounds its subprocess plus bounded cleanup, not total wall time.

Coordinator must collect both complete selected reports, persist/commit/freeze, then run the agreed ONE final qualifying full local gate and external exact-head Trust CI under exact delegated transport. This report grants no merge authority.
