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

## Security follow-up: exact local imports and bounded Git batching

The exact-side resolver previously normalized only `ImportFrom`, so a relevant
`import project.runtime as runtime` module alias and a local wildcard could hide a
queue export. Relative child imports also accepted an empty export name as a
declaration even when the child source did not exist. Exact module discovery then
used repeated per-path Git blob subprocesses and made the fitness suite approach
the verifier timeout.

RED evidence:

```text
test_local_module_and_wildcard_imports_resolve_queue_exports
Ran 1 test in 1.026s
FAILED (failures=2: module-alias and wildcard queue positives were N/A)

test_relative_child_import_requires_a_resolved_local_source
Ran 1 test in 2.742s
FAILED (failures=3: missing child below/at/above frontier was N/A)

test_external_imports_use_batched_local_module_inventory
Ran 1 test in 0.384s
FAILED (external_alpha/external_beta triggered per-import Git probes)

test_exact_batch_blob_reader_is_bounded_and_validates_entries
Ran 1 test in 0.219s
FAILED (AttributeError: read_diff_files was absent)
```

The repair normalizes ordinary module aliases and local wildcards into the same
reachable-operation decision, requires an exact local source before accepting a
relative child as nonqueue, and preserves per-top-level module budgets while
sharing only completed immutable resolutions. Exact Git module content is now
read from parsed regular-blob `ls-tree` metadata with one bounded, deterministic
`cat-file --batch` content process. OIDs, types, sizes, response order, delimiters,
per-file size, aggregate bytes, and requested paths are validated. Worktree reads
continue to use descriptor-relative no-follow reads.

GREEN and performance evidence:

```text
7 focused batching/frontier/import/cache tests
Ran 7 tests in 7.238s
OK

python3 -m unittest -v tests.test_architecture_fitness
Ran 67 tests in 73.874s
OK
elapsed=74.06 maxrss=66584

python3 -m unittest discover
Ran 361 tests in 180.826s
OK
elapsed=181.07 maxrss=101248

python3 scripts/grok_architecture.py fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --worktree --json
fitness=pass; background_job=pass; code_budget=pass
max_changed_lines=10000/10000; elapsed=5.33s
```

The prior post-normalization fitness run took 263.756 seconds; a root-only inventory
reduced it to 238.183 seconds, while the validated content batch reduced the final
run to 73.874 seconds without raising a timeout, source limit, AST limit, module
limit, or dependency-work limit. The first full-suite run exposed only a Bandit
B105 false positive in an internal semantic mapping; the tuple-form equivalent
then passed configured Bandit and the three affected verifier selectors before the
clean 361-test rerun.

Tracked files in this follow-up are the queue provenance/fitness implementation,
the exact diff reader, this evidence, and the focused fitness regressions. No
`trust-ci/**` or `.github/workflows/**` path changed. Exact post-commit SHA and the
required text verifier result are recorded after the product commit.

## Package-child and member-specific security rereview

The rereview found that `from project import runtime` did not inspect an exact
local `project.runtime` child when the parent package lacked that export. It also
found that queue provenance from one module export overtainted ordinary sibling
exports, cached resolutions bypassed per-importer module accounting, the exact
batch reader used Git 2.42-only `cat-file -Z`, and worktree batches did not share
the exact-side request and aggregate limits.

RED evidence, before the implementation change:

```text
4 focused selectors
Ran 4 tests in 3.615s
FAILED (failures=10)
```

The regressions cover namespace and regular packages, queue/nonqueue/missing/
ambiguous package children, mixed module-alias and wildcard exports, cold/warm
and reversed cache order at the 64-module ceiling, legacy Git batch framing,
negative and malformed metadata, real gitlink/nonblob entries, constant total
metadata-plus-content subprocess calls at 1 versus 32 paths, and exact/worktree
batch limits.

GREEN and performance evidence on the repaired worktree:

```text
4 focused security/cache selectors
Ran 4 tests in 4.479s
OK

test_exact_batch_blob_reader_is_bounded_and_validates_entries
Ran 1 test in 1.003s
OK

python3 -m unittest -v tests.test_architecture_fitness
Ran 70 tests in 77.309s
OK
elapsed=77.50 exit=0

python3 -m unittest discover -v
Ran 364 tests in 186.619s
OK
elapsed=186.87 exit=0
```

Exact worktree fitness passes with background-job fitness passing without
findings, monotonic risk `green -> red`, and the changed-code budget at
`9999/10000`. The exact batch protocol uses legacy-compatible
`git cat-file --batch`, validates deterministic OIDs and size-framed responses,
and rejects negative sizes and non-regular tree entries. Completed cache entries
avoid repeated I/O but every distinct semantic module is charged to each
top-level importer before cache reuse. Member-aware object provenance keeps
ordinary sibling exports N/A while queue exports use the single shared
fitness/risk result.

Ruff, configured Bandit, and compileall pass. The typed spec gate passes 7/7;
architecture validate, drift, and diagram check pass without findings or
mismatches; README K16 passes; diff whitespace and protected-path checks pass.
The required text-verifier, commit, and exact-SHA evidence are recorded below
after those gates complete.

## Unaliased dotted-import rereview

The rereview found that `import project.runtime` retained only the bound root
`project` and emitted `project.app`, dropping the `runtime` segment before
abstract interpretation. The same review requested removal of the magic cache
inventory sentinel and independent worktree request-count and encoded-input
limit oracles.

RED evidence:

```text
test_mixed_local_module_exports_are_member_specific
test_exact_batch_blob_reader_is_bounded_and_validates_entries
Ran 2 tests in 2.402s
FAILED (failures=1: dotted queue was not_applicable instead of unsupported)
```

The repair carries a distinct full access prefix while retaining the import
binding root for dependency matching. The interpreter constructs nested object
provenance for unaliased dotted imports, so `project.runtime.app` is queue-derived
without tainting `project.runtime.form`; existing aliased and wildcard semantics
remain unchanged. `_QueueResolutionCache` now explicitly contains module
inventory, source paths, and prefetched/completed resolutions; no sentinel key
remains.

GREEN and performance evidence:

```text
2 focused dotted-import and independent batch-limit selectors
Ran 2 tests in 2.399s
OK

python3 -m unittest -v -k queue tests.test_architecture_fitness
Ran 23 tests in 30.522s
OK

python3 -m unittest -v tests.test_architecture_fitness
Ran 70 tests in 76.746s
OK
elapsed=76.93 exit=0

python3 -m unittest discover -v
Ran 364 tests in 188.994s
OK
elapsed=189.24 exit=0
```

Exact worktree fitness passes with background-job findings empty, monotonic risk
`green -> red`, and code budget preserved at `9999/10000`. Ruff, configured
Bandit, compileall, typed spec 7/7, architecture validate/drift/diagram, README
K16, diff whitespace, protected paths, and exact change separation all pass.
Text-verifier, commit, and exact-SHA evidence follow after the final gates.

## Count-only cap and dotted sibling rereview

The test rereview found that the prior count-cap input also exceeded the default
encoded-byte ceiling. The code rereview found an order-dependent namespace
overwrite: `import project.runtime` followed by ordinary `import project.forms`
replaced the shared `project` object and hid the queue-derived runtime member.

RED evidence:

```text
test_exact_batch_blob_reader_is_bounded_and_validates_entries
Ran 1 test in 0.962s
FAILED (missing patchable MAX_BATCH_INPUT_BYTES boundary)

test_mixed_local_module_exports_are_member_specific
Ran 1 test in 2.252s
FAILED (dotted sibling queue-first was not_applicable)
```

The batch-input ceiling is now the named, unchanged 65,536-byte constant. The
count-only test raises that ceiling above the real `MAX_CHANGED_PATHS + 1`
request and proves no worktree read occurs; the separate under-count input still
exceeds the default byte ceiling and independently proves the other branch.
Unaliased dotted imports now augment existing object members at their shared
package root instead of replacing the root. Both import orders preserve runtime
queue provenance, while both ordinary sibling operations remain N/A.

GREEN evidence:

```text
2 focused cap and sibling selectors
Ran 2 tests in 3.388s
OK

python3 -m unittest -v -k queue tests.test_architecture_fitness
Ran 23 tests in 30.347s
OK

python3 -m unittest -q tests.test_architecture_fitness
Ran 70 tests in 79.142s
OK
elapsed=79.33 exit=0

python3 -m unittest discover -q
Ran 364 tests in 186.996s
OK
elapsed=187.23 exit=0
```

Exact worktree fitness passes with background-job findings empty, monotonic risk
`green -> red`, and the changed-code budget at `10000/10000`. Ruff, configured
Bandit, compileall, typed spec 7/7, architecture validate/drift/diagram, README
K16, diff whitespace, protected paths, and exact separation all pass. The text
verifier, commit, and exact-SHA evidence follow after final gates.

## Recursive dotted-branch rereview

The rereview found that shallow package-root augmentation still replaced a
colliding intermediate branch: queue `project.services.runtime` disappeared when
ordinary `project.services.forms` was imported afterward. It also required the
merge traversal itself to consume existing bounded-analysis capacity.

RED evidence:

```text
test_mixed_local_module_exports_are_member_specific
test_queue_alias_work_is_bounded_before_branch_closure
Ran 2 tests in 3.717s
FAILED (failures=2: deep queue-first was N/A; low-limit merge did not stop)
```

Object augmentation now recurses only through colliding object branches,
preserves disjoint descendants, and conservatively joins conflicting leaves.
Every rebuilt object charges its complete entry count through the existing value
limit, so depth/width cannot bypass the established bound. Both import orders,
ordinary sibling controls, duplicate queue/nonqueue leaves, aliases, and direct
siblings remain covered.

GREEN evidence:

```text
2 focused depth and bound selectors
Ran 2 tests in 3.746s
OK

python3 -m unittest -q -k queue tests.test_architecture_fitness
Ran 23 tests in 30.558s
OK

python3 -m unittest -q tests.test_architecture_fitness
Ran 70 tests in 79.900s
OK
elapsed=80.08 exit=0

python3 -m unittest discover -q
Ran 364 tests in 187.109s
OK
elapsed=187.35 exit=0
```

Exact worktree fitness passes with background findings empty, risk monotonic
`green -> red`, and code budget `10000/10000`. Ruff, configured Bandit,
compileall, typed spec 7/7, architecture validate/drift/diagram, README K16,
diff whitespace, protected paths, and exact separation all pass. The final
verifier, commit, and exact-SHA evidence follow after final gates.
