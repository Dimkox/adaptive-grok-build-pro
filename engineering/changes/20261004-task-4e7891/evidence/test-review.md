# Independent test review — M8 accepted Liqvera product

Public path projection: only the host-local absolute repository prefix is replaced with `<repository-root>`; the complete original is retained in private scratch. Exact SHAs, fingerprints, repository-relative scratch paths, remaining command arguments, findings and results are unchanged.

Status: PASS with two nonblocking metadata-binding limitations. Role: route-selected test_reviewer, route 4e78915ad1ab. Reviewed 2026-10-04T23:28:21Z–23:30:55Z. No blocking findings for the accepted-product dependency correction.

## Source and isolation

Comparison base: f97966c4173fff9a3954389498568038dc57776b.
Candidate: <repository-root>/.review-scratch/m8-liqvera-accepted.
HEAD before/after: 048305111df9177e2d873cf5871e8c51a64a12e1.
Candidate tree fingerprint before/after: 7cacbd28151987019b7fabc5453f4b1843cf9119aa76bb8ced0c86437463e55d.
Candidate staged, unstaged and untracked inventory before/after: empty.
reviewed-tree-modified: no

Reviewer-owned private scratch: <repository-root>/.review-scratch/test-review-5qOqy5; trusted parent .review-scratch and scratch both mode 0700, owner pall, non-sticky. Exact local clone at scratch/candidate made with git clone --no-hardlinks --no-checkout followed by detached checkout of the above HEAD; clone fingerprint equals candidate fingerprint and clone inventory is empty. No relevant dirty bytes were omitted because candidate inventory was empty. Mutation runner lives outside clone at scratch/mutation_probe.py; it deep-copies scratch-loaded state and mutates only those private in-memory copies. Candidate/index were never edited; GIT_OPTIONAL_LOCKS=0 and PYTHONDONTWRITEBYTECODE=1 were used for probes/tests.

## Measured resources and scheduling

Private capacity.md recorded before route/diff inspection. Commands: lscpu; nproc --all; nproc; taskset -pc $$; /proc/self/cgroup and /proc/self/mountinfo reads; ancestor cpu.max/cpuset.cpus.effective reads; bounded taskset -c 0-27 child probe. Host: 14 physical cores, 28 online logical CPUs 0-27. Default process: nproc 22, affinity 0,1,8-27. Actual cgroup2 membership /user.slice/user-1000.slice/session-2050.scope, mounted /sys/fs/cgroup; exposed user/user-1000/session quotas all max 100000; root cpu.max absent; effective cpuset inherited 0-27. Child widening succeeded: nproc 28, affinity 0-27, session quota unlimited. Verified capacity 28, reviewer allocation one serial test process. No agents dispatched or full verifier run by reviewer. Final qualifying verifier remains coordinator-owned after reports persist.

## Scope and conclusions

Inspected actual base..HEAD diff and surrounding test setup, runtime-boundary assertions, state, README, START_HERE, roadmap, decisions/mistakes and active package analyses/implementation report. Product changes are seven paths: DARK_FACTORY_ROADMAP.md, PROJECT_STATE.json, README.md, START_HERE.md, decisions.md, mistakes.md, tests/test_project_state.py. Remaining changed paths are active package evidence/workflow. No runtime/schema/default-flag/VERSION edits.

New regression positively binds DONE, canonical Dimkox/liqvera, observed main, released source/tag, factory source pin, explicit owner-confirmation kind, true completed working factory-built acceptance, false independent telemetry, exact four unblocked dependencies and six remaining prerequisites, current accepted-product qualification, and historical false acceptance of the superseded different target. Existing axis test now permits only the M8 case extension; existing runtime test retains false cohort/activation/M9/publication/cost flags and default-off factory settings. This preserves the distinction between an accepted product and empirical operational authority.

Two metadata mutants survived all 19 project-state test methods: factory_version changed to 0.0.0, and source_zip_sha256 changed to 64 zeroes. These are explicit nonblocking coverage limitations: factory source SHA and released source SHA remain independently pinned by the regression, and metadata agrees with recorded controller provenance on the reviewed tree. Future drift of those two descriptive fields would not be caught by this module. No blanket mutation threshold is claimed.

## Executed commands and observations

All commands below run in scratch/candidate unless candidate is explicitly named.

1. git rev-parse HEAD; git status --porcelain=v1; git diff f97966c4173fff9a3954389498568038dc57776b..HEAD --stat; targeted git diff and sed/rg inspections. HEAD matched; inventory empty; 21 paths including seven product paths plus active package.
2. GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; from pathlib import Path; sys.path.insert(0,".grok-stack"); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))' on candidate before/after and clone: all output 7cacbd28151987019b7fabc5453f4b1843cf9119aa76bb8ced0c86437463e55d.
3. GIT_OPTIONAL_LOCKS=0 git clone --no-hardlinks --no-checkout <repository-root>/.review-scratch/m8-liqvera-accepted <repository-root>/.review-scratch/test-review-5qOqy5/candidate; git -C <scratch>/candidate checkout --detach 048305111df9177e2d873cf5871e8c51a64a12e1. Success.
4. GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-27 python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package tests.test_workflow_sources tests.test_repo_router. PASS: Ran 153 tests in 55.887s, OK. This is fresh reviewer observation, distinct from historical implementer timing 15.657s.
5. GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-27 python3 <repository-root>/.review-scratch/test-review-5qOqy5/mutation_probe.py. Exit 0, results below. The harness initializes ProjectStateTests.setUpClass(), deep-copies its state for each mutant, invokes the changed regression or existing runtime qualification test on an instance with mutated state, and reports assertion failures as killed. For survivors it invokes every one of the 19 project-state methods with that mutated state: both yielded failures=[].
6. GIT_OPTIONAL_LOCKS=0 git diff --check f97966c4173fff9a3954389498568038dc57776b..HEAD. PASS/no output.
7. Final candidate git rev-parse HEAD, git status --porcelain=v1 and fingerprint command: unchanged exact HEAD/fingerprint and empty inventory.

## Bounded mutation results

Each case targets private copied PROJECT_STATE. Changed-regression target: test_m8_completed_liqvera_case_unblocks_only_accepted_product_dependencies. Global qualification target: test_runtime_observations_are_source_bound_without_promoting_qualification.

- Remove milestones.M8.completed_product_case: KILLED; completed_product_case not found. Independently reproduces missing-case RED.
- completed_product_case.status = notdone: KILLED; 'notdone' != 'DONE'.
- completed_product_case.repository = Dimkox/other: KILLED; canonical repository assertion.
- completed_product_case.release_source_sha = 40 zeroes: KILLED; released source SHA assertion.
- completed_product_case.factory_source_sha = 40 zeroes: KILLED; factory source SHA assertion.
- acceptance.independent_runtime_telemetry = true: KILLED; True is not false.
- acceptance.completed_working_factory_built_product = false: KILLED; False is not true.
- operational_qualification.m8_activation = true: KILLED; True is not false.
- operational_qualification.m8_qualifying_cohort = true: KILLED; True is not false.
- operational_qualification.m9_general_operational_qualification = true: KILLED; True is not false.
- completed_product_case.factory_version = 0.0.0: SURVIVED, including all 19 module methods.
- completed_product_case.source_zip_sha256 = 64 zeroes: SURVIVED, including all 19 module methods.

No inconclusive probes; mutations are state-level rather than runtime implementations because runtime behavior is unchanged. All mutations were discarded as in-memory copies.

## Unexecuted claims and delivery limits

External Liqvera availability, public source/release metadata and ZIP hash were not independently fetched by this reviewer: read-only prior controller analysis provides provenance, while owner acceptance is supplied directly by the user. No real provider/runtime calls, 30-task empirical cohort, full cost accounting, signed environment/recovery authority, production publication, external Trust CI or approval validation were attempted. Those remain absent/unestablished or externally gated; local test success grants none of them.

Static consistency of explanatory prose and field-to-evidence pointers was inspected, not exhaustively mutation-tested; direct bindings for every descriptive release field, every prose sentence and every dependency-evidence pointer are not claimed. Final scope selector/receipt, route-selected companion code review, report-containing frozen verification and external exact-head Trust CI remain the coordinator's delivery steps.
