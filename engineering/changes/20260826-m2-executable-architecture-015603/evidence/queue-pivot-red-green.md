# Queue abstract-interpreter RED/GREEN evidence

Date: 2026-08-27

Scope: M2-A queue/installer pivot Task 1 only. This change introduces no runtime
queue, dependency, service, database, migration, external action, Trust CI
change, or GitHub Actions workflow.

## Root cause

The former `_queue_provenance()` retained one mutable value per name and replayed
all assignments in AST traversal order. Mutually exclusive branches therefore
overwrote one another rather than joining, Python-equal keys such as `True` and
`1` occupied different analyzer entries, supported container mutation and
concatenation were ignored, and signed selections fell back to mixed-value
aggregation. The same exact base/head comparison could consequently fail open or
false-trigger solely because of statement or key spelling order.

The repair moves provenance into a focused bounded abstract interpreter. Its
immutable scalar/sequence/mapping values use commutative, associative,
idempotent joins; source-order statement transfer joins alternatives; literal
keys follow Python equality; known append/extend/subscript/concatenation updates
preserve bounded element identity; and only queue/unknown operation dependencies
emit stable semantic signals.

## RED

Branch/key command:

```text
python3 -m unittest -v \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_control_flow_and_python_equal_keys_fail_closed
```

Observed before production changes:

```text
queue branch first: expected unsupported, got not_applicable
bool key then integer key: expected unsupported, got not_applicable
integer key then bool key: expected unsupported, got not_applicable
Ran 1 test in 1.038s
FAILED (failures=3)
```

Container/signed-selection command:

```text
python3 -m unittest -v \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_container_mutations_and_signed_selections
```

Observed before production changes:

```text
Celery append/extend/subscript/list-concat/tuple-concat: 5 false N/A outcomes
RQ append/extend/subscript/list-concat/tuple-concat: 5 false N/A outcomes
negative list index, tuple index, and integer mapping key: 3 false unsupported outcomes
Ran 1 test in 4.592s
FAILED (failures=13)
```

## GREEN

Exact new selectors:

```text
python3 -m unittest -v \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_control_flow_and_python_equal_keys_fail_closed \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_container_mutations_and_signed_selections
Ran 2 tests in 5.670s
OK
```

All queue-focused methods, including wildcard, package/relative adapter,
depth/module/source-root bounds, mixed files, sibling exports, and unrelated
terminal-name controls:

```text
python3 -m unittest -v tests.test_architecture_fitness -k queue
Ran 11 tests in 22.261s
OK
```

Task-wide fitness suite:

```text
python3 -m unittest -v tests.test_architecture_fitness
Ran 52 tests in 84.999s
OK
```

Representative public join-domain and bound probes:

```text
join algebra: commutative/associative/idempotent across 10 representative values
mapping join algebra: 9 representative values
statement: bounded
value: bounded
loop: bounded
```

The first repository-wide discovery run found two integration regressions after
the focused suite: a product helper named `_eval` tripped the verifier's literal
Bandit fixture, and a cache shared across unrelated changed files exhausted the
32-module adapter ceiling. Renaming the helper to `_evaluate` and scoping the
cache to each bounded dependency graph repaired the root causes. The exact two
previously failing selectors then passed:

```text
python3 -m unittest -v \
  tests.test_change_receipts.ReceiptTests.test_pre_adoption_route_base_uses_one_architecture_comparison_base \
  tests.test_verification_doctor.QualityContourTests.test_eval_only_in_tests_does_not_fail_bandit
Ran 2 tests in 21.513s
OK
```

Fresh repository-wide discovery after both repairs:

```text
python3 -m unittest discover -s tests
Ran 350 tests in 323.589s
OK
```

Static checks before final repository-wide verification:

```text
python3 -m ruff check \
  .grok-stack/adaptive_grok/queue_provenance.py \
  .grok-stack/adaptive_grok/architecture_fitness.py \
  tests/test_architecture_fitness.py
All checks passed!

python3 -m compileall -q .grok-stack/adaptive_grok
exit 0

git diff --check
exit 0
```

## Changed behavior and safety

- `background_job` and monotonic `new_queue` risk still consume the same exact
  `_QueueProvenanceResult` produced from base/head signal subtraction.
- Relevant analysis ceilings become structured unsupported evidence; ordinary
  unrelated calls remain true N/A.
- Local adapter resolution remains bounded per dependency graph, including the
  existing depth, module, AST, source-root, and repository file ceilings.
- Exact non-queue signed selections stay N/A, while ambiguous or proven queue
  calls/decorators fail closed with the changed path in applicability scope.

## Rollout and rollback

This is local source-only analysis behavior. Rollout is the ordinary reviewed
M2-A branch and pull-request process. Rollback is a source revert of the Task 1
commit before release; there is no runtime, data, service, queue, or external
state to unwind.
