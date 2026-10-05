# Publication projection

Complete implementer report below; only host-local repository prefix is replaced with `<repository-root>`. Original raw report remains private. Historical identity8304ce1 precedes coordinator evidence freeze. No product modification or semantic SQL qualification is added.

# Fixed reviewed SQL pin handoff

Status: narrow pin implemented and committed; Stage B independent reviews, one qualifying full PR verifier and exact-head external Trust CI remain coordinator work. This report is implementer evidence, not a review receipt, semantic SQL qualification, deployment approval or merge authority.

## Exact identities and inventory

Checker repository: <repository-root>/.review-scratch/trust-public-checker
Branch: fix/trust-public-local-checker
Route: 249e86df9131; change: 20261005-task-249e86; generation: public-checker-pin-20261005
Actual agreed comparison base: 326908bf6367b05b65b83818ee84a093c1e45872
Starting workflow HEAD: 71d219596cfd8c365b132d0c98a8465296135acd
Previously reviewed mechanism HEAD: 39d0f9eb27d807e72219d613c290e785a035f151
Final pin HEAD: 8304ce199a0d438bbe7bcf6c38550ae2fb68432f
Final Git tree: d4bada88a17020edf349a091df250977ad566af6
Final canonical fingerprint: a1ace9823a401c35f87b9cf39d8d217c1fc6a14d8459d7b4a49bd20c595b3a9a
Working tree: clean after commit.

Pin commit diff: four files, 21 insertions / 3 deletions:

- .grok-stack/adaptive_grok/architecture_fitness.py: only the fixed literal registry entry and provenance comment.
- tests/test_architecture_fitness.py: one portable exact registry identity guard; no SQL copied into tests.
- decisions.md: update the existing three-sentence lesson to identify the actual reviewed source rather than the historical empty state.
- mistakes.md: mandatory engineering-contract root-cause record for the interrupted private test-discovery mistake described below. No product behavior added there.

Full agreed-base..HEAD inventory, 24 paths:
```
.grok-stack/adaptive_grok/architecture_fitness.py
decisions.md
engineering/changes/20261005-task-249e86/architecture.md
engineering/changes/20261005-task-249e86/brief.md
engineering/changes/20261005-task-249e86/change-spec.yaml
engineering/changes/20261005-task-249e86/evidence/README.md
engineering/changes/20261005-task-249e86/evidence/capacity.md
engineering/changes/20261005-task-249e86/evidence/prerequisite-analysis.md
engineering/changes/20261005-task-249e86/evidence/reviewed-sql-pin-provenance.md
engineering/changes/20261005-task-249e86/evidence/source-sql-data-review-bacb534.md
engineering/changes/20261005-task-249e86/evidence/stage-a-code-39d0f9e.md
engineering/changes/20261005-task-249e86/evidence/stage-a-implementer-39d0f9e.md
engineering/changes/20261005-task-249e86/evidence/stage-a-security-39d0f9e.md
engineering/changes/20261005-task-249e86/evidence/stage-a-test-39d0f9e.md
engineering/changes/20261005-task-249e86/human-gates.json
engineering/changes/20261005-task-249e86/release.md
engineering/changes/20261005-task-249e86/requirements.md
engineering/changes/20261005-task-249e86/rollback.md
engineering/changes/20261005-task-249e86/route.json
engineering/changes/20261005-task-249e86/state.json
engineering/changes/20261005-task-249e86/tasks.md
engineering/changes/20261005-task-249e86/test-plan.md
mistakes.md
tests/test_architecture_fitness.py
```

No Trust CI source/SQL/schema/loader, rule, policy, selector, factory runtime or deployment content enters this checker PR.

## Actual reviewed artifact and independent provenance

Immutable artifact source HEAD: bacb5346a95d25166e1f7c597b3f91bd5935c234.
Independent source fingerprint: 1410ef8f89b3cb621c40be1ccb0ae8af4860a813d14af4dd2b09b4244bf68145.
Primary: trust-ci/sql/004_public_admission.sql.
Sole mirror: trust-ci/src/adaptive_trust_ci/resources/004_public_admission.sql.
Both raw SHA256: 610b8fa6b759c69578bc18b007484db1c4e19cba5f613c7bd482e68badac646e.

Read completely:
- checker package evidence/source-sql-data-review-bacb534.md
- checker package evidence/reviewed-sql-pin-provenance.md
- original <repository-root>/.review-scratch/data-review-fix1-5pOIJi/data-review-fix1.md

The independent scoped D1/D2 approval at bacb534 attributes two actual PG controls and two killed guard mutants to that reviewer. Those PG results were read, not rerun or promoted to checker/full-branch qualification. Historical rejected7334 and intermediate fbdc identities were never pinned.

Used fresh ignored private snapshot:
 <repository-root>/.review-scratch/trust-public-checker/.review-scratch/checker-pin-XCvFPT/snapshot

Creation commands, both executed with explicit checker workdir:
```
taskset -c 8-11 git clone --quiet --no-local --no-hardlinks --no-checkout <repository-root>/.review-scratch/trust-ci-public <repository-root>/.review-scratch/trust-public-checker/.review-scratch/checker-pin-XCvFPT/snapshot
git -C <repository-root>/.review-scratch/trust-public-checker/.review-scratch/checker-pin-XCvFPT/snapshot checkout --quiet --detach bacb5346a95d25166e1f7c597b3f91bd5935c234
```
No public-candidate Git writes or mutable-HEAD interpretation occurred. Snapshot HEAD, fingerprint, primary/mirror digests and clean status matched before and after the probes. Snapshot was not mutated; probe fixtures were separate temporary repositories below the trusted private directory.

Parent .review-scratch and private checker-pin-XCvFPT are owner pall, mode0700; capacity recheck is adjacent .review-scratch/checker-pin-capacity.md. At most two single-process groups ran concurrently on CPUs8-11, below the four-CPU allocation; measured online logical28, physical14, no finite applicable ancestor quota.

Historical immutable SQL byte checks also match checker baseline exactly:
001_schema.sql, primary/mirror: c03e071c1a789c856b54be23c105fd224e1f569b1662b61d46354f2212f46532
002_operational_indexes.sql, primary/mirror: f46128291b765a77568be448f5ef09d37300423afd327370ee2da79d5f33487c
003_database_roles.sql, primary/mirror: 1ba63d44639a6cb933a31b887717b021e35b6d056aa564a25f0aaba1683c888c

## RED then fixed literal

Portable identity RED:
```
taskset -c 8-11 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_migration_registry_is_only_the_fixed_independently_reviewed_identity
```
Exit1; one failure, 0.002s; empty registry differs from the exact one-entry reviewed identity.

Actual-byte positive RED before pin:
```
taskset -c 8-11 env PYTHONDONTWRITEBYTECODE=1 python3 <repository-root>/.review-scratch/trust-public-checker/.review-scratch/checker-pin-XCvFPT/actual_bytes_probe.py ActualReviewedByteControls.test_actual_reviewed_bytes_current_registry_positive
```
Exit1; one failure, 3.393s. Actual immutable byte fixture returned unsupported / unsupported_migration_semantics with "unreviewed Trust CI migration bytes or missing exact mirror", instead of pass. All001–003 byte equality checks succeeded.

Then installed only:
trust-ci/sql/004_public_admission.sql -> 610b8fa6b759c69578bc18b007484db1c4e19cba5f613c7bd482e68badac646e.

The named compatibility mechanism remains otherwise unchanged. It still requires the exact mirror, fixed Trust CI policy, immutable history, unique contiguous versions and bounded inventories/reads. No environment, CLI or expected-digest caller interface was introduced. Actual probe uses the installed checker module and the production registry without private patching. The synthetic tests continue to patch the registry privately only for their expressly synthetic fixture.

## Actual-byte GREEN and drift controls

Corrected exact command:
```
taskset -c 8-11 env PYTHONDONTWRITEBYTECODE=1 python3 <repository-root>/.review-scratch/trust-public-checker/.review-scratch/checker-pin-XCvFPT/actual_bytes_probe.py ActualReviewedByteControls
```
Exit0; two tests in16.480s; zero skips. Five actually executed cases:
- Actual fixed raw004 plus identical packaged mirror: pass, reason reviewed_trust_ci_migration_byte_compatibility; disclosed raw_sha256610b... and "not semantic phase proof"; findings[].
- Raw-only drift: unsupported, unreviewed bytes or missing exact mirror.
- Paired raw/mirror drift: unsupported, unreviewed bytes or missing exact mirror.
- Mirror-only drift: unsupported, unreviewed bytes or missing exact mirror.
- Unregistered005 carrying the exact004 bytes plus mirror: unsupported, migration phase cannot be derived for trust-ci/sql/005_public_admission.sql.

The probe imports the checker test helper module for its baseline fixture and calls installed FIT._migration_safety only. It does not evaluate the full public architecture or any runtime behavior. Actual SQL exists only in immutable private snapshot and ignored temporary fixtures, not portable tests or checker product.

Portable/bounds/history GREEN:
```
taskset -c 8-11 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_migration_registry_is_only_the_fixed_independently_reviewed_identity tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_uses_named_byte_compatibility_not_phase_proof tests.test_architecture_fitness.ArchitectureFitnessTests.test_unreviewed_public_migration_cannot_accept_runtime_digest_authority tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_refuses_drift_and_incomplete_history tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_planning_and_blob_comparison_are_aggregate_bounded tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_work_and_published_findings_have_explicit_limits tests.test_architecture_fitness.ArchitectureFitnessTests.test_migration_blob_statement_and_finding_limits_stop_early tests.test_architecture_fitness.ArchitectureFitnessTests.test_canonical_migrations_seed_phased_version_history
```
Exit0; eight tests in43.977s; zero skips. Fixed-registry/current-row guard verifies exactly one literal actual reviewed identity. Synthetic positive remains synthetic; environment/caller/CLI authority is refused; all13 synthetic drift/incomplete-history subcases execute. Existing aggregate work/blob/statement/finding limits and canonical history controls pass.

git diff --check exited0. Commit8304ce1 contains the same checked product bytes. git status --short after commit had no output. Final HEAD/tree/fingerprint are above; no fingerprint-bound verification receipt is created by this report.

## Interrupted observation and root cause

One private actual-probe invocation without an explicit selector began default unittest discovery, which included ArchitectureFitnessTests because that helper class had been imported into the script's module namespace. It printed partial progress but no result. The exact owned process PID302534 was identified by its absolute script command and terminated with SIGTERM; exit143. This partial observation is discarded, neither passed nor reused. No grok_verify, root/full branch suite or PG/runtime action ran.

Corrected the ignored helper to import its module and explicitly selected ActualReviewedByteControls in the successful command above. Logged this root cause in mistakes.md per the engineering contract. No checker mechanism change was needed.

## Stage A and residual limits

Persisted Stage A code/test/security PASS reports bind mechanism39d0f9e, where the production registry was intentionally empty. They remain historical evidence for that mechanism; they do not approve the new fixed pin or current HEAD. Stage B selected five final reviews and fresh frozen full qualification remain pending.

This turn proves raw byte identity and closed checker compatibility only. SQL syntax/additivity, roles/grants, quota correctness, lock/query behavior, concurrency, cleanup, hold recovery and operational rollback were not executed here. Reviewed source retains a persistent exact-PR history-incomplete hold with no automatic recovery and unmeasured large-volume query planning; existing broad-UPDATE API retirement and final-aware rollback remain launch prerequisites. The source data review is separately attributed and scoped.

No public architecture qualification is claimed while Task5 bindings remain outstanding. No full grok_verify, agent spawning, local approval/review receipt, push, PR, merge, deploy, credentials, keys, deployed policy, rules or selector changes occurred. Coordinator owns final reviews, report persistence/freeze, full verification, external exact-head App CI and any separately delegated operational delivery.

STOP at clean committed pin.
