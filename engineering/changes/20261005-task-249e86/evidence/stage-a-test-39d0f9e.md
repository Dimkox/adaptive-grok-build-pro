Persisted Stage A evidence only: source HEAD `39d0f9eb27d807e72219d613c290e785a035f151`, fingerprint `b7c59b62ec6e3d29e4d09376f74bc22975bf5198767a74991570e0484b52d68c`. The complete report below is projected only by replacing the host repository prefix with `<repository-root>` and removing trailing whitespace. Actual 004 pin, final reviews and final verification remain pending; this is historical source-bound evidence, not a completion receipt.

# Independent Stage A test review

Reviewer: selected `test_reviewer`, route `249e86df9131`, change `20261005-task-249e86`. Date: 2026-10-05 UTC.

Verdict: PASS for the frozen Stage A checker mechanism and its scoped test adequacy. No blocking test-quality finding was observed. This is not completion of AC-001/AC-004, qualification of actual Task1 SQL, a final delivery review, a verification receipt, or merge authority. The production reviewed-migration registry remains EMPTY. A later actual migration pin needs independently reviewed frozen actual SQL, affected controls and fresh review identity.

reviewed-tree-modified: no

## Identity and isolation

Candidate: `<repository-root>/.review-scratch/trust-public-checker`.
HEAD before and after: `39d0f9eb27d807e72219d613c290e785a035f151`.
Git tree before and after: `f0fb961fd7f3a3469cc6253ace8bb508065ecd4c`.
Candidate fingerprint before and after: `b7c59b62ec6e3d29e4d09376f74bc22975bf5198767a74991570e0484b52d68c`.
Source Git status before and after: empty `git status --porcelain=v1 --untracked-files=all`; no staged, unstaged or relevant untracked changes existed to overlay.
Task diff base: `fd5f5fcc32358bb07c51c23881bede751e76f197`; actual agreed PR base: `326908bf6367b05b65b83818ee84a093c1e45872`.

Private scratch: `<repository-root>/.review-scratch/test-review-39d0f9e-SOORQB`, mode 0700, owner pall; trusted parent `<repository-root>/.review-scratch`, mode 0700, owner pall, non-sticky. Private product clone is the `snapshot` child, also mode 0700, with its own `.git`, mode 0700. No shared mutable candidate or Git metadata was used.

Exact snapshot creation:

```bash
mktemp -d -p <repository-root>/.review-scratch test-review-39d0f9e-XXXXXX
git clone --no-hardlinks --no-local --no-checkout <repository-root>/.review-scratch/trust-public-checker <repository-root>/.review-scratch/test-review-39d0f9e-SOORQB/snapshot
git checkout --detach 39d0f9eb27d807e72219d613c290e785a035f151
```

Checkout ran only in the private clone. Source and clone independently produced the same 4,470-path tracked-byte manifest, `de1eca123c1e283b350a74aa2b67bcb51823d9e61d446e094bfdf791d8c81a94`, before probes and after restoration. Manifest algorithm: sorted `git ls-files -z` paths; SHA256 over each path followed by NUL and that file's binary SHA256 digest. The product checker inodes differ and `.git/objects/info/alternates` is absent. Both fingerprints and statuses match again after restoring private mutants with `apply_patch`.

Checker SHA256: `a7705e636074781464b5fb5830e0de03dd7bf007b00cbf45a403162890f09be5`.
Test-module SHA256: `3d53af0d00acd1dd97d22e3c97b310d37eb3bc824065d56ec98400e90f267c6c`.

Identity checks used `PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3`, importing `adaptive_grok.util.tree_fingerprint`, and read-only `git rev-parse HEAD`, `git rev-parse 'HEAD^{tree}'`, `git status --porcelain=v1 --untracked-files=all`, and `git ls-files -z`. No artifact, receipt or test execution occurred in the candidate; clone/checkout and all deliberate mutations occurred only in private scratch. Full verification and report persistence remain coordinator responsibilities.

## Startup capacity and dependencies

CPU discovery was recorded locally before inspecting route/handoff/diff: `/tmp/trust-checker-test-review-capacity-4109918.md`, timestamp `2026-10-05T03:03:18 UTC`.
Commands: `lscpu`, `nproc --all`, `nproc`, `taskset -pc <reviewer-process-pid>`, reads of `/proc/self/cgroup`, `/proc/self/mountinfo`, `/sys/devices/system/cpu/online`, and applicable cgroup ancestor `cpu.max` / `cpuset.cpus.effective`; bounded child affinity probes.
Observed topology: 14 physical cores / 28 online logical CPUs, IDs 0-27. Initial process affinity `0,1,8-27`; initial `nproc` 22; `nproc --all` 28. Actual cgroup-v2 mount `/sys/fs/cgroup`, membership `/user.slice/user-1000.slice/session-2050.scope`. Session, user-1000.slice and user.slice quotas each `max 100000`; root has no finite quota. Effective inherited cpuset `0-27`.
Child-only widening command `taskset -c 0-27 bash -c 'nproc; taskset -pc $$; cat /proc/self/cgroup; cat /sys/fs/cgroup/user.slice/user-1000.slice/session-2050.scope/cpu.max /sys/fs/cgroup/user.slice/user-1000.slice/cpu.max /sys/fs/cgroup/user.slice/cpu.max /sys/fs/cgroup/user.slice/cpuset.cpus.effective'` returned 28 CPUs, affinity 0-27, unchanged membership, all three quotas `max 100000`, cpuset 0-27. Bounded child 12-15 probe returned 4 CPUs and affinity 12-15. Verified effective host capacity 28; reviewer allocation 4 CPUs 12-15, one serial test process, no process-worker pool. Platform slots and route permissions do not enlarge this allocation; no subagents were spawned.

Dependency order: capacity record → candidate route/scope and frozen diff/report inspection → independent snapshot validation → baseline → serial isolated implementation mutants → restore private source → positive controls → candidate identity recheck → private report. Serialization prevents overlapping mutations. Per delegated Stage A scope, no whole-suite/full verifier or completion receipt was run.

## Scope and test-quality findings

Read the supplied task diff once, the complete implementation report, typed `change-spec.yaml`, requirements/test plan and candidate route. Inspected the changed test methods and surrounding migration/metadata implementation. Actual PR-base name-status inventory contains only the checker, test module, decisions prose and the 14-file scope/evidence package; no Trust CI loader/runtime/SQL/schema or factory implementation is included.

The four positive descriptors are independently written test fixtures, with the intended path/ID/version/kind/role/compatibility and owner/source mappings. Fresh independent positive execution covers each descriptor alone and all four together. The source lists and original-envelope negatives cover changed old bindings, runtime, secrets, owner, domain, type, old contracts, edges, old/new nodes, prefix/arbitrary source and mixed implementation changes. The existing API/OpenAPI/store-binding control remains in the implementer's reported preserved-control run. Static inspection found no unconditional metadata qualification, broad worker permission, generic numeric-SQL fallback or caller digest parameter.

The SQL fixture explicitly says synthetic, patches the registry only within each positive/negative fixture context and checks the named compatibility reason, emitted digest and `not semantic phase proof` predicate. Fresh negative execution exercises the complete 13-case migration matrix and the real CLI rejection. Comparing primary and mirror bytes and treating 004 as numeric version 4 are separate requirements; the tests distinguish them. Byte compatibility intentionally does not prove PostgreSQL semantics.

Execution-accounting check: the current module places all 26 public-envelope case labels and all 13 SQL case labels inside the actual iterable, rather than unreachable branches. The existing metadata loop contains all 12 labels. The implementation report records successful completed commands for those matrices on these exact checker/test bytes, including the corrected unchanged-source fixture that makes separation applicable through a changed unrelated legacy source. Those broader implementer observations were inspected, not reclassified as independent reviewer executions. Fresh reviewer executions below independently cover all 13 SQL negatives, seven allowed worker paths plus denied `public_extra.py`, unchanged-schema and unchanged-exact-source negatives, environment/caller/CLI refusal and the public/synthetic positives.

No blocking finding. Unprobed surfaces and Stage B dependencies are listed below; this report makes no blanket coverage or mutation-score claim.

## Exact reviewer commands and observed results

All test commands ran in the private `snapshot` directory. `TMPDIR` keeps fixture repositories under the private mode-0700 contour; bytecode writing is disabled.

Baseline:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-39d0f9e-SOORQB taskset -c 12-15 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_refuses_drift_and_incomplete_history tests.test_architecture_fitness.ArchitectureFitnessTests.test_unreviewed_public_migration_cannot_accept_runtime_digest_authority tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_worker_source_membership_is_exact_and_envelope_preserving tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_metadata_requires_changed_schema_and_exact_paired_source_bytes
```

Exit 0: `Ran 4 tests in 77.515s`, `OK`.
SQL subcases: paired_drift, mirror_drift, missing_mirror, mirror_only, primary_deleted, history_modified, history_deleted, history_gap, duplicate_version, other_005, unknown_sql, wrong_primary_path, wrong_mirror_path. Authority test executes two candidate-digest environment variables, caller `expected_digest` TypeError and actual CLI `--expected-migration-digest` rejection with `unrecognized arguments`. Worker cases cover all seven approved filenames and denied public_extra.py. Schema/source cases exercise unchanged bytes with an unrelated Trust CI source edit ensuring applicability.

M1 — registered raw-SHA256 comparison weakened only in the private checker: replaced `and digest == _REVIEWED_TRUST_CI_MIGRATIONS.get(item.path)` with `and digest is not None`. Claim: paired changed SQL bytes cannot authorize themselves even with an identical mirror.

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-39d0f9e-SOORQB taskset -c 12-15 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_refuses_drift_and_incomplete_history
```

KILLED. Exit 1: `Ran 1 test in 37.890s`, `FAILED (failures=1)`. Failing subtest `mutation='paired_drift'`, assertion `AssertionError: 'pass' == 'pass' : ()`. The original baseline rejected the same case. Restored M1 before introducing M2.

M2 — exact mirror-byte comparison weakened only in the private checker: replaced `and blobs.get(_PUBLIC_MIGRATION_MIRROR) == value` with `and _PUBLIC_MIGRATION_MIRROR in blobs`. Claim: the packaged mirror must contain identical raw bytes, not just appear in read inventory.

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-39d0f9e-SOORQB taskset -c 12-15 python3 -m unittest -f tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_refuses_drift_and_incomplete_history
```

KILLED. Exit 1: `Ran 1 test in 5.960s`, `FAILED (failures=1)`. Failing subtest `mutation='mirror_drift'`, assertion `AssertionError: 'pass' == 'pass' : ()`. Fail-fast intentionally stopped at that first failure; later mutant subcases are unexecuted. Restored M2 before introducing M3.

M3 — seven-file worker-source bound weakened only in the private checker: replaced `and new_paths - old_paths <= _PUBLIC_WORKER_SOURCES` with `and bool(new_paths - old_paths)`. Claim: unchanged worker envelope and a changed Python file cannot admit an unlisted worker source.

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-39d0f9e-SOORQB taskset -c 12-15 python3 -m unittest -f tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_worker_source_membership_is_exact_and_envelope_preserving
```

KILLED. Exit 1: `Ran 1 test in 23.045s`, `FAILED (failures=1)`. Failing subtest `filename='public_extra.py'`, assertion `AssertionError: 'pass' != 'fail'`. The seven allowed path cases precede that failure. Restored M3 with `apply_patch`; original checker hash, whole tracked-byte manifest, clean Git status and original private fingerprint were re-established.

Final restored positive controls:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-39d0f9e-SOORQB taskset -c 12-15 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_uses_named_byte_compatibility_not_phase_proof tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_only_exact_paired_public_contracts
```

Exit 0: `Ran 2 tests in 17.521s`, `OK`. This executes the synthetic reviewed-byte positive and each of the four contract mappings alone plus all four together. No production pin was installed.

## Limits and required subsequent evidence

Static-reviewed but not independently executed here: the complete 26-case public-envelope matrix, alternate webhooks lifecycle pair, 12-case preserved old-metadata matrix, all unchanged generic phase/aggregate limit controls and malformed-policy variants. Their implementation-report runs remain implementer evidence, not fresh independent execution or reused qualification receipts. Empty changed schema/source bytes and every combination of multi-contract/owner changes were not separately probed. Selected implementation mutation probes cover raw hash, mirror bytes and worker file admission only; exact tuple/source-owner and rule-envelope comparisons were inspected without additional mutation probes. No surviving selected mutant occurred; no score or universal bug-exclusion threshold is inferred.

Unexecuted actual Task1 claims: frozen real 004 byte identity/pin, PostgreSQL syntax and dollar-quoted function bodies, additivity/destructiveness, roles/grants, quotas, concurrency/admission linearization, locks, query plans, bounded cleanup, recovery, real migration apply/status compatibility and rollback with packaged 004. They require actual frozen SQL, independently reviewed source identity and real database evidence. The synthetic function/grant fixture cannot establish them.

Also unexecuted: full PR verifier, final fingerprint-bound receipts, App-owned exact-head check, signed external approvals, push/PR/merge/tag/release/deployment/production actions. None was requested or attempted by this reviewer. No secrets, private keys, credentials or `.env` were read. Any future candidate change, including actual registry pin or persisted reports, invalidates this review identity for final qualification.

The coordinator must persist this complete report after the review wave and retain Stage A labeling. Do not record final completion receipts from this report alone. Reviewer STOP.
