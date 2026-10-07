# Publication projection

Complete independent report below, bound to original frozen2de723c. Only host-local repository prefix is replaced with `<repository-root>` and terminal blank lines normalized. Raw report remains reviewer-private; this is not a new completion identity or external authority.

# Independent Stage B test review

Spec compliance: Approved for the bounded checker pin delta at the exact identity below. Test quality: Approved for that scope; no blocking finding. The fixed production registry admits only the named reviewed actual bytes; the new portable identity guard and independent actual-byte positive both detect an incorrect installed pin. This is compatibility-byte proof, not SQL semantics, complete public-source qualification, a full verifier receipt or merge/launch authority.

reviewed-tree-modified: no

## Identity and private snapshot

Reviewer: selected `test_reviewer`; route `249e86df9131`; change `20261005-task-249e86`; Stage B follow-up, 2026-10-05 UTC. Candidate `<repository-root>/.review-scratch/trust-public-checker`.
HEAD before/after: `2de723c45ffb97a26d25efca2a1fdc33a03e0460`.
Git tree before/after: `e0a37c930b75f750eadf0316d52e7921c99335b6`.
Candidate fingerprint before/after: `1a89e46b591c25ca81a88ebaa24393e40a67bbcd88f2b2e7a7db68fbfbe6ad5c`.
Source Git status before/after: empty `git --no-optional-locks status --porcelain=v1 --untracked-files=all`. There was no relevant staged/unstaged/untracked overlay to reproduce.
Stage B delta base `39d0f9eb27d807e72219d613c290e785a035f151`; actual PR comparison base remains `326908bf6367b05b65b83818ee84a093c1e45872`.

Private reviewer contour `<repository-root>/.review-scratch/test-review-stage-b-IGH4oK`, owner pall, mode 0700; trusted parent `<repository-root>/.review-scratch`, owner pall, mode 0700, non-sticky. Private clone `snapshot` and its independent `.git` also mode 0700. No Git alternates; source/private checker inodes differ.

Exact snapshot commands:

```bash
mktemp -d -p <repository-root>/.review-scratch test-review-stage-b-XXXXXX
taskset -c 6-7 git clone --no-local --no-hardlinks --no-checkout <repository-root>/.review-scratch/trust-public-checker <repository-root>/.review-scratch/test-review-stage-b-IGH4oK/snapshot
git checkout --detach 2de723c45ffb97a26d25efca2a1fdc33a03e0460
```

Clone ran with explicit candidate workdir; checkout only in private snapshot. Source and private clone matched all 4,477 tracked file bytes before review and after private restoration. Manifest `407718974fc8ab2310f7c3ef31debdd1e4a90e3e7493dd897e413cabf43ef91e`: SHA256 over sorted `git ls-files -z` entries, each path followed by NUL and binary SHA256 of its file. Both final statuses are empty and both fingerprints match above. Checker SHA256 `382eb0184f7fd2196351b4f18743a2c91edfa20798e319f07ac6ffa1ac33cac6`; test module SHA256 `caffdda36c74ef4496ffd78dca79b0a2b19fb1f696b2e24b355097389b7594e8`.

Identity commands used explicit candidate workdir, `PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 taskset -c 6-7 python3`, imported `adaptive_grok.util.tree_fingerprint`, and subprocess `git rev-parse HEAD`, `git rev-parse 'HEAD^{tree}'`, `git status --porcelain=v1 --untracked-files=all` and `git ls-files -z`. No candidate tests, artifacts, receipts, checkout or deliberate metadata mutation occurred. All probes and mutations stayed in reviewer-owned scratch.

## Startup resources and review scope

Remeasured and recorded before repository inspection: `/tmp/trust-checker-stage-b-test-review-capacity-391647.md`, timestamp `2026-10-05T04:38:03.960432+00:00`. Commands: `lscpu -e=CPU,CORE,ONLINE`; `nproc --all`; `nproc`; `taskset -pc 391647`; reads of online CPUs, `/proc/self/cgroup`, cgroup mountinfo and all applicable ancestor `cpuset.cpus.effective`/`cpu.max`; bounded child-only `taskset` probes over verified IDs 0-27 and 6-7 with affinity, membership and limits rechecked.
Observed 14 physical cores / 28 online logical CPUs 0-27. Initial nproc22, affinity0,1,8-27; actual cgroup-v2 mount `/sys/fs/cgroup`, membership `/user.slice/user-1000.slice/session-2050.scope`. Session/user1000/user.slice quotas all `max 100000`, root no finite quota; effective inherited cpuset0-27. Widening child succeeds with nproc28/affinity0-27/same cgroup and limits; reviewer child succeeds with nproc2/affinity6,7/same limits. Verified capacity28, reviewer allocation exactly two CPUs6-7, one serial test process, no worker pool or subagents. Snapshot validation, baseline and mutation runs were serialized.

Read supplied Stage B delta, complete raw pin implementer report, current registry/test source, requirements and pin provenance, and complete attributed source data review. Whole-base inventory/context retains the isolated checker contour: no Trust CI runtime/loader/SQL/schema, factory implementation, architecture rule or selector changes. Product delta since Stage A is the fixed literal registry/provenance comment plus the nine-line portable identity test; migration and contract mechanisms are unchanged. Historical Stage A reports stay explicitly attributed to their old identity, not treated as fresh Stage B qualification.

Actual artifact anchor: immutable commit `bacb5346a95d25166e1f7c597b3f91bd5935c234`, historically reviewed source fingerprint `1410ef8f89b3cb621c40be1ccb0ae8af4860a813d14af4dd2b09b4244bf68145`. Reviewer freshly read only fixed-commit SQL objects with `git --no-optional-locks show bacb5346a95d25166e1f7c597b3f91bd5935c234:<exact-path>`, explicit public-source repository cwd. No mutable public HEAD was interpreted as authority. Raw `trust-ci/sql/004_public_admission.sql` and packaged `trust-ci/src/adaptive_trust_ci/resources/004_public_admission.sql` each length 24,559 and raw SHA256 `610b8fa6b759c69578bc18b007484db1c4e19cba5f613c7bd482e68badac646e`; equality and hashes matched before/after. All six primary/mirror001–003 blobs match the checker fixture baseline. Attributed D1/D2 PostgreSQL review evidence was read, not rerun or promoted to broad SQL approval.

## Independent commands and actual observations

Reviewer probe `<repository-root>/.review-scratch/test-review-stage-b-IGH4oK/pin_probe.py`, SHA256 `1cee3713f99190bb3e79d1370da6e1f4d8523067f4645ba660db4435edb8fccb`. It imports the private checker test module as a module, explicitly selects only `StageBPinReview.test_real_bytes_use_unpatched_current_registry`, extracts actual immutable bytes through fixed-commit Git reads, verifies historical byte equality, creates a separate disposable migration fixture under the private TMPDIR, and calls the installed checker. It does not patch the production registry, accept caller digests, parse/execute SQL or run imported helper tests by discovery. It compares the registry before/after and asserts pass, the named byte-compatibility reason, disclosed digest and `not semantic phase proof` predicate.

All test commands below used explicit workdir `<repository-root>/.review-scratch/test-review-stage-b-IGH4oK/snapshot`, no parallel execution.

1. Actual-byte baseline:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-stage-b-IGH4oK taskset -c 6-7 python3 <repository-root>/.review-scratch/test-review-stage-b-IGH4oK/pin_probe.py StageBPinReview.test_real_bytes_use_unpatched_current_registry
```

Exit0; `Ran 1 test in 2.125s`, `OK`, no skips. Diagnostic installed registry contains the single actual fixed digest. `actual_result`: status pass, reason `reviewed_trust_ci_migration_byte_compatibility`, findings[], predicate includes exact raw SHA256 and `not semantic phase proof`. This fresh positive uses actual reviewed bytes and the installed registry without a private registry patch.

2. Portable identity baseline:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-stage-b-IGH4oK taskset -c 6-7 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_migration_registry_is_only_the_fixed_independently_reviewed_identity
```

Exit0; `Ran 1 test in 0.000s`, `OK`, no skips. Exact one-entry dictionary assertion prevents absent/extra/wrong installed identities; it does not claim to validate SQL semantics.

3. M1, private installed-pin mutation: replaced only the registry's fixed digest literal with 64 zeroes through `apply_patch`, leaving raw artifact bytes, mirror bytes, test expectations and the Stage A mechanism unchanged. This is a new Stage B identity mutation; none of the three Stage A guard-removal mutants was repeated. Claim probed: actual-byte acceptance depends on the installed independently reviewed identity, and the new portable test observes that dependency.

Repeated exact command1 above. Exit1; `Ran 1 test in 2.130s`, `FAILED (failures=1)`. Actual artifact hash and mirrors still match; diagnostic installed registry is zeroes; checker returns unsupported, reason `unsupported_migration_semantics`, finding `FIT-TRUST-CI-SQL-HISTORY: unreviewed Trust CI migration bytes or missing exact mirror: trust-ci/sql/004_public_admission.sql`. Assertion `'unsupported' != 'pass'`. M1 KILLED by the non-vacuous actual-byte positive.

4. Same M1, distinguishing portable guard from synthetic mechanism control:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=<repository-root>/.review-scratch/test-review-stage-b-IGH4oK taskset -c 6-7 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_public_migration_registry_is_only_the_fixed_independently_reviewed_identity tests.test_architecture_fitness.ArchitectureFitnessTests.test_reviewed_public_migration_uses_named_byte_compatibility_not_phase_proof
```

Exit1; `Ran 2 tests in 2.090s`, `FAILED (failures=1)`, no skips. Portable identity test fails showing installed zeroes versus exact expected610b...; M1 KILLED by that guard. The synthetic test PASSES under the incorrect installed pin because its expressly synthetic fixture temporarily patches the registry to its own fixture digest. For that single synthetic control M1 SURVIVED, by design: it tests the mechanism, not the production pin. This is an explicit test limitation, addressed by the new identity guard and independent actual-byte positive, not hidden or counted as a universal mutation score. No selected mutation was inconclusive.

Restored only the private registry literal with `apply_patch`, then rechecked original checker hash, all tracked bytes, clean status, HEAD and canonical fingerprint for both source/private snapshot. No original candidate bytes changed; no new baseline rerun was necessary after exact restoration.

## Declined-to-judge and unexecuted claims

No SQL semantics, schema/grant correctness, migration apply/status behavior, quota fairness, admission concurrency, lock/query plans, large-volume work, cleanup, persistent replay-history hold recovery, rollback/forward recovery, old broad-UPDATE API retirement or complete public architecture/Task5 binding qualification was executed or approved here. Those require their separately scoped source/PG/runtime evidence. The fixed byte pin does not transform the source data review's scoped D1/D2 approval into blanket safety or deployment authority.

Did not rerun the implementer's eight portable/bounds/history controls, actual drift matrix, Stage A matrices or Stage A mutations. Their supplied results remain attributed implementer/historical evidence. Static inspection of unchanged guard logic does not establish new executable verification. Additional missing/extra/wrong-path registry mutants and combined edits to checker plus expected test literals were not executed; the one selected identity mutant establishes sensitivity only within its stated scope.

No full verifier, repository-wide/PG matrix, agent spawning, receipt, operational grant, push/PR/merge/tag/release/deployment/external write, secrets, `.env`, credentials or private-key access. The coordinator owns report persistence, freeze/final full qualification, external exact-head App check and any required approvals. Persisting reports or any further candidate change requires fresh final identity-bound evidence.

Reviewer STOP. Complete report remains in reviewer-owned private scratch for out-of-band coordinator persistence.
