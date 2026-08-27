# Queue dependency frontier repair: RED/GREEN evidence

Date: 2026-08-27

Approved scope: preserve the exact unresolved dependency frontier and resolve only reachable local import exports without module-name guessing. The 4,096 dependency-work budget and supported syntax remain unchanged.

## Root cause

`_operation_dependencies()` returned only a partial discovered-name set and `exhausted=True`. `_queue_adapter_names()` then guessed relevance from queue-like module-name tokens. Consequently a reachable Celery export in neutral `project.runtime` was skipped, while a declared nonqueue export in `project.jobs` and an unrelated exhausted graph were falsely promoted.

## RED

Command:

```bash
python3 -m unittest -v \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_dependency_frontier_resolves_reachable_local_exports \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_unrelated_exhausted_dependency_frontier_remains_not_applicable
```

Observed before production changes:

```text
neutral module queue export: not_applicable != unsupported
queue-adjacent module nonqueue export: unsupported != not_applicable
unrelated exhausted graph: unsupported != not_applicable
Ran 2 tests in 1.388s
FAILED (failures=3)
```

These are exact base/head repositories. The queue positive asserts scoped `unsupported`, overall failure, `new_queue`, and monotonic risk. Both nonqueue cases assert true N/A, overall pass, no trigger, and monotonic risk.

## GREEN

The bounded worklist now retains the exact unprocessed frontier. A deterministic traversal of only that remaining dependency cone identifies reachable imported aliases within the pre-existing 200,000-node AST bound. Each reachable local export is then resolved: queue or unresolved relevant exports use the shared structured unsupported result, while a declared nonqueue export remains N/A. Module-name tokens no longer substitute for frontier relevance.

```text
python3 -m unittest -v \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_dependency_frontier_resolves_reachable_local_exports \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_unrelated_exhausted_dependency_frontier_remains_not_applicable
Ran 2 tests in 1.899s
OK

python3 -m unittest -v tests.test_architecture_fitness
Ran 62 tests in 111.266s
OK

ruff check .grok-stack/adaptive_grok/architecture_fitness.py tests/test_architecture_fitness.py
All checks passed!

python3 scripts/grok_architecture.py fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --worktree --json
fitness=pass; code_budget=pass; findings=[]
```

## Full verification

```text
python3 -m unittest discover -s tests
Ran 356 tests in 226.354s
OK

ruff check .grok-stack/adaptive_grok scripts tests
All checks passed!

bandit -c bandit.yaml -q -r .grok-stack/adaptive_grok scripts
exit 0 (pre-existing nosec informational warnings only)

python3 -m compileall -q .grok-stack/adaptive_grok scripts
exit 0

python3 scripts/grok_spec.py validate \
  --change-id 20260826-m2-executable-architecture-015603 --gate --json
ok=true; criteria=7/7; errors=[]

python3 scripts/grok_architecture.py validate --json
ok=true; findings=[]

python3 scripts/grok_architecture.py drift --json
ok=true; findings=[]

python3 scripts/grok_architecture.py diagram --check --json
ok=true; mismatches=[]

python3 scripts/grok_architecture.py diff \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --worktree --json
head=worktree; artifacts=100

python3 scripts/grok_architecture.py fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --worktree --json
fitness=pass; code_budget=pass; risk=green->red
max_changed_lines=10000/10000

python3 -m unittest -v \
  tests.test_structure.StructureTests.test_readme_stack_graph_is_complete
Ran 1 test in 0.002s
OK

git diff --check
exit 0

git diff --name-only 8fff802c9f5c641b4abbf35090c4be7b9ff8ec45 \
  -- trust-ci .github/workflows
no output
```

## No-record verifier result

The first required text-mode run exposed the performance defect described below: its
fixed unittest phase timed out with exit 124. After the bounded cache repair, the
same required command passed without changing any timeout or verifier behavior:

```text
python3 scripts/grok_verify.py --mode pr --no-record
PASS git-diff-check: exit=0
PASS change-spec: 2 specs checked; exempt=False
PASS architecture: drift=pass; fitness=pass; diagrams=pass
PASS secret-scan: 0 potential secrets
PASS contract-structure: 8 contracts checked
PASS sql-safety: 0 unsafe SQL findings
PASS ruff: exit=0
PASS bandit: exit=0
PASS python-unittest: exit=0
PASS coverage: exit=0
RESULT: PASS | profiles=base,contracts,data | changed=176
elapsed=343.27 user=269.51 sys=83.89 cpu=102%
```

## Bounded performance regression and repair

The frontier repair initially made local module resolution recursive across the
actual repository diff. `_new_queue_sources()` recreated exact head/base caches for
every changed importer, and the frontier branch repeated a source lookup already
performed by `_local_queue_resolution()`. A two-importer regression observed four
exact reads of `project.runtime` instead of one. The initial full fitness run was
green but took 729.416 seconds, and the required verifier timed out.

The repair now retains one exact completed-resolution cache per diff side, reuses
the resolver's missing-module result before any root probe, and charges the existing
32-module work ceiling to each top-level analysis rather than accumulated memoized
results. The ceiling and supported syntax are unchanged.

```text
RED test_queue_local_resolution_is_reused_across_changed_importers
project.runtime head reads: 4 != 1

python3 -m unittest -v \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_local_resolution_is_reused_across_changed_importers \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_dependency_frontier_resolves_reachable_local_exports \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_unrelated_exhausted_dependency_frontier_remains_not_applicable
Ran 3 tests in 2.135s
OK
elapsed=2.35 user=1.63 sys=0.77 cpu=102%

python3 -m unittest -q tests.test_architecture_fitness
Ran 62 tests in 111.266s
OK
elapsed=111.45 user=62.32 sys=53.71 cpu=104%

python3 -m unittest discover -s tests
Ran 356 tests in 226.354s
OK
elapsed=226.60 user=152.92 sys=82.11 cpu=103%
```

Exact worktree fitness passes at `10000/10000` changed lines. Ruff, configured
Bandit, compileall, the 7/7 typed spec gate, architecture validate/drift/diagram,
README K16, diff whitespace, and protected-path checks all pass.

Commit and exact post-commit evidence are appended after commit.
