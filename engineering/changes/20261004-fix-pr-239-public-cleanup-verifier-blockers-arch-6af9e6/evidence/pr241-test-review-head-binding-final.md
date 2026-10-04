# Independent test review — committed-head bindings addendum

PASS for the focused7c6098d→a83d4e5 addendum. The four original failing cases pass under Core-style inherited PYTHONPATH, and the package-marker mutation is killed specifically by the new test-count assertion.

## Identity and isolation

- HEAD before/after: `a83d4e5c28b097bcc00147bd255c55d07701e595`.
- Fingerprint before/after: `0c45d11b0ac62e37978d69ffb111fd3fa010ffc9cfa95f7a9e7d862f2d9999fc`.
- Candidate and exact private clone remained clean.
- Scratch relative to candidate: `../adaptive-grok-build-pro/.review-scratch/test-review-core-final-Mlp1Hq/`.
- Scratch parent/contour reviewer-owned0700, nonsticky and locally ignored.
- Startup capacity recorded before inspection at `2026-10-04T18:21:22Z`:14 physical/28 logical; child widening verified28, cpuset0-27, no finite quota observed. Allocation CPUs6-11/max6 workers; invocation bounds175s.
- reviewed-tree-modified: no

## Executed claims

- Committed-HEAD root inventory accepts exactly the nine restored compatibility names while retaining the closed-set equality check.
- All three synthetic focused fixtures execute their own five tests under the inherited Core import path.
- Removing one fixture’s package marker causes unintended execution of152 real binding tests; even with those tests green, the new count assertion rejects the result.
- The five-file delta contains only tests and notes. Production runner/environment, selector, QG, receipts, legacy launchers and handoff bytes are unchanged.

## Commands/results

From the private clone, with GIT_OPTIONAL_LOCKS=0, PYTHONDONTWRITEBYTECODE=1, private TMPDIR:

```bash
PYTHONPATH="$PWD:$PWD/tests:$PWD/.grok-stack" GROK_TEST_WORKERS=6 \
taskset -c 6-11 timeout 175s python3 -B -m unittest -q \
 tests.test_structure.StructureTests.test_repository_root_holds_only_canonical_entries \
 tests.test_verification_scope.FocusedPythonExecutionTests.test_admitted_inventory_never_executes_full_suite_discovery \
 tests.test_verification_scope.FocusedPythonEmptyTargetTests.test_the_replaced_runner_is_named_by_the_caller_not_assumed \
 tests.test_verification_scope.VerifyDocsStateScopeEndToEndTests.test_verify_selects_and_runs_the_focused_profile_for_a_docs_only_successor
```

```text
Ran 4 tests in0.868s
OK
```

Mutation, using the same Core-style PYTHONPATH and CPU/time bounds:

```bash
TMPDIR=/tmp/core-fixture-review-uohdF5 \
PYTHONPATH="$PWD:$PWD/tests:$PWD/.grok-stack" GROK_TEST_WORKERS=6 \
taskset -c 6-11 timeout 175s python3 -B ../fixture_marker_mutation.py
```

```text
M1-one-fixture-package-marker-removed: KILLED
tests=1 failures=1 errors=0 markers_removed=1
focused runner passed its unintended152 real tests;
new Ran5 assertion rejected it
```

The temporary-output directory was freshly created and verified reviewer-owned0700. Only temporary test output used that contour; the Git snapshot stayed inside project scratch.

Read-only checks included:

```text
git diff --stat 7c6098d..HEAD
git diff 7c6098d..HEAD
git diff --check 7c6098d..HEAD
git rev-parse HEAD
git status --porcelain=v1
```

Inspected the complete five-file/34-line delta and surrounding tests. AST comparison observed:

```text
closed_root_inventory: exactly9 explicit legacy names added; no removals
```

An explicit git diff --exit-code over production, launcher, installer, handoff and architecture paths returned0. Whitespace check passed.

Before/after fingerprint command:

```bash
GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys,pathlib;sys.path.insert(0,".grok-stack");from adaptive_grok.util import tree_fingerprint;print(tree_fingerprint(pathlib.Path.cwd()))'
```

## Limits

The first mutation attempt under project-contained TMPDIR failed before the required count boundary and is INCONCLUSIVE. Repeating only that probe in the trusted temporary-output contour produced the valid kill above. The mutant’s unintended152-test execution is diagnostic evidence, not fresh qualification of the unmutated candidate.

Earlier full reviews/addenda remain historical for unchanged source; the failed7c6098d full gate remains failed. No unmutated whole-module/full-verifier rerun, production behavior rerun, PostgreSQL, external check/approval validation, GitHub write or thread resolution occurred. Fresh report-containing full verification and external exact-head gates remain coordinator-owned.
