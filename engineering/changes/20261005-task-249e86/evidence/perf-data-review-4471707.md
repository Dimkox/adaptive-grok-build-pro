# Affected data review — frozen 4471707

Coordinator projection: complete out-of-band report, public path prefix substituted only; original absolute paths retained in the controller record. This is bounded source review at the stated identity, not a fresh final receipt.

Bounded data review: PASS for the optimization’s affected migration-test scope, with actual historical SQL hash validation unexecuted.

Candidate: <project-root>/.review-scratch/trust-public-checker
HEAD before/after: 4471707447570b0bc020e3764aa4066f6a008672
Fingerprint before/after: d6232a5eb10c276f47a02b1d53c7b668de41d25e473b0d1eab25ee9b967bcd7d
Exact reviewed delta: 5886e734b170307c6026f98c026f5e1a0e6ae834..4471707447570b0bc020e3764aa4066f6a008672
Inventory: tests/test_architecture_fitness.py, decisions.md; production and migrations unchanged.
reviewed-tree-modified: no

Private scratch: <private-review-scratch>/data-review.2JOlz8/repo
Trusted parent and scratch permissions: 0700.
Snapshot reproduced using cp -a .review-scratch/trust-public-checker <private-review-scratch>/data-review.2JOlz8/repo; source Git status empty.
Capacity recorded in adjacent capacity.md: 14 physical cores, 28 logical CPUs, process allows 22; child CPUs 10–11 expose two CPUs. Visible cgroup ancestors report unlimited quota. Review used taskset -c 10,11.

Observed claims:
- _migration_safety derives commit inventory through _repository_paths(... diff.head_sha ...); _MigrationAnalysis.read invokes read_diff_files, whose commit branch reads the exact diff.head_sha. It does not depend on the final fixture’s working-tree SQL bytes.
- _frozen_fixture_diff explicitly asserts base SHA, head SHA and captured snapshot architecture digest. Preparation preserves each snapshot before later fixtures mutate the working tree.
- All 13 negative cases remain present and construct actual changed/deleted paths. history_gap commits a gapped predecessor; primary_deleted and mirror_only commit previously admitted bytes before the adverse change. Their comparison bases remain attached to their prepared cases.
- Paired/raw drift, mirror drift, missing mirror, history modification/deletion, duplicate version, other 005, unknown SQL and wrong primary/mirror paths retain their distinct fixture changes.
- Fixed production registry mappings/hashes for 004 and 005 are unchanged by this delta. The optimization privately patches synthetic digest values without modifying fixed membership.

Exact representative execution:
taskset -c 10,11 python3 -B -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_synthetic_forward_registry_keeps_membership_separate_from_digest_keys
Observed: Ran 1 test in 3.933s, OK. This executes the admitted synthetic 004/005 forward positive and unknown006 negative with an injected registry digest. The first positive is evaluated after the final unknown006 fixture was prepared, directly exercising independence from current fixture worktree state.

Mutation probe:
taskset -c 10,11 python3 -B <private-review-scratch>/data-review.2JOlz8/probe.py
The private probe replaces _repository_paths with inventory from the fixture repository’s actual current HEAD rather than the requested diff head. Result: KILLED. The forward positive becomes unsupported with migration phase cannot be derived: trust-ci/sql/006_public_pending_bootstrap.sql. This demonstrates the representative positive catches last-fixture inventory contamination.
An initial mutant used literal HEAD, which the exact-SHA API rejected; that preliminary result was invalid as contamination evidence. The corrected probe resolves HEAD with git rev-parse HEAD and obtains the meaningful kill above.

Unexecuted claims:
- The full 13-negative matrix was statically reviewed, not executed, under the requested representative-only bound.
- PostgreSQL behavior, whole matrix, full verifier, external Trust CI and approvals were outside this review.
- Actual historical 004/005 byte hashes could not be independently checked: git show bacb5346a95d25166e1f7c597b3f91bd5935c234:trust-ci/sql/004_public_admission.sql and corresponding 005 lookup at 1f48c4ccc84192780395b18957ba8c9779e30f00 report missing paths. Empty-pipeline hashes are rejected as evidence. Only unchanged fixed registry identities are established here.

No migration semantic change or approval authority is claimed.
