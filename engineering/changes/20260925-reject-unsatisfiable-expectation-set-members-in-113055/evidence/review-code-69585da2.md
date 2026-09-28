# Code review — reject unsatisfiable expectation-set members

Reviewed HEAD: `69585da2955a2ee0ba15ad7784ba04a38bf5e143`
Branch: `fix/issue-202-evidence-expectations`
Commit tree: `eef5427df9c87139753970471d660115c8137e46`
Pre-review porcelain: `?? engineering/changes/20260925-reject-unsatisfiable-expectation-set-members-in-113055/evidence/next-gap.md` (present before this review; not edited)
Post-write porcelain: that same untracked note, plus this report. HEAD and commit tree unchanged.
Reviewer write: this report only. Product files were not edited.
reviewed-tree-modified: no

Scope: plan-time rejection of unsatisfiable expectation-set members in `.grok-stack/adaptive_grok/spec.py` (`expectation_set_findings` and the AST probe binder) at the named HEAD. Issue #202 items 2 and 3 are out of scope for this contour and are not treated as defects.

## Claims

1. An exact-set member is accepted only when one resolvable `unittest.TestCase` method calls the trusted `exercise_expectation_member` with that literal and observe/mutate/undo callables.
2. A lookalike rebind of that helper is not a proof (`FORBID-001`, `test_trusted_helper_import_cannot_be_shadowed_by_a_lookalike`).
3. The ordinary test run must be what proves absent, then present, then restored. A call that the ordinary runner does not execute is not a proof.
4. A dead member with no such probe is rejected by name. Non-test evidence, another sentence's cue, and a module-level name rebind do not prove it.

## Probe record

Read-only inspection completed: `git rev-parse HEAD`, `git branch --show-current`, `git status --porcelain=v1`, `git rev-parse 'HEAD^{tree}'`, `git diff-tree --no-commit-id --name-status -r HEAD`, `git show --stat --format=fuller HEAD`, and the HEAD~1 diff of the schema, template, skills, `decisions.md`, and `mistakes.md`. Candidate sources read in place. Installed CPython 3.12 `unittest.case._callTestMethod` was read at `/usr/lib/python3.12/unittest/case.py` (this tree's `adaptive_grok` bytecode is `cpython-312`).

Executable mutation probes were not run. A compound shell was denied as `ambiguous-sensitive-shell`. The follow-up probe command was circuit-broken as the same objective and was not retried. Writing the probe outside the repository was also blocked, so no mode-0700 scratch copy exists. Scratch safety was not established. Every runtime suite result and every scratch mutant below is **unexecuted**. The acceptance defects in findings 1–3 are properties of the AST walker as written; they do not depend on a suite exit code.

| Claim | Probe | Result |
| --- | --- | --- |
| Dead member without a counted call is named and rejected | Source walk of `expectation_set_findings` | Holds in source; suite re-run unexecuted |
| Module-body `exercise_expectation_member = pass_only` is not trusted | `_module_shadowed_names` sees that `Assign` | Holds in source; suite re-run unexecuted |
| `if` / `try` / import-time `global` rebind of the same name is not trusted | Same walker | **Survived (defect).** Not scanned |
| `alias.exercise_expectation_member = lookalike` is not trusted | Name-store filter | **Survived (defect).** Attribute store is ignored |
| Call after `return`, `async def` test, `@unittest.skip`, `@unittest.expectedFailure` is not a proof | Body scan and decorator handling | **Survived (defect).** Call text is enough |
| Four positional arguments do not count as observe/mutate/undo | `complete_call` versus the helper signature | **Survived (defect).** `len(args) >= 4` counts |
| Shadow-subtraction mutant and `complete_call = True` mutant | Scratch copy | **Unexecuted** (scratch blocked) |

## What holds

- Exact-set findings are errors in both draft and gate profiles, for `acceptance_criteria`, `invariants`, and `forbidden_outcomes`. A member is emitted with `!r`, the criterion id, and the missing mutation/undo text. Receipt, attestation, and production-signal evidence never add members.
- Cues are applied per brace group sentence. `.` `!` `?` and newlines split sentences outside braces. A single all-uppercase `{TITLE}` / `{X}` is dropped; `{A, B}` is not. Empty, numeric, and JSON groups do not become members.
- A module-body assignment or function definition that stores the imported helper name removes it from the trusted set. A nested `def` inside the test method is not treated as a call. The selector must be `Class::method` (or `Class.method`) with a `test` prefix and a direct `unittest.TestCase` base.
- The helper itself checks absent, then present, then full restoration, and refuses a string observation. Criterion keys stay `id`, `statement`, and `evidence`, matching `trust-ci/holdout.example/change_spec_validate.py` (`set(item) != {"id", "statement", "evidence"}`). The schema edit is a description only.
- A synthetic local toggle is an accepted proof in this contour. Binding the probe to a real detector is issue #202 item 2 and is not required here.

## Findings

### 1. Blocking — lookalike rebinds still count as the trusted helper

`_module_shadowed_names` only records module-body function/class names and `Name` stores on `Assign`, `AnnAssign`, `AugAssign`, `NamedExpr`, `For`, and `With`. It does not walk `If`, `Try`, `While`, or `Match`, and it never records an `Attribute` store.

```847:874:.grok-stack/adaptive_grok/spec.py
def _module_shadowed_names(module: ast.Module) -> set[str]:
    shadowed: set[str] = set()
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadowed.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.For, ast.With)):
            shadowed.update(
                child.id
                for child in ast.walk(node)
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store)
            )
    return shadowed
```

So both of these keep the trusted binding, and the later call is still classified as `exercise_expectation_member` from `adaptive_grok.spec`:

- `from adaptive_grok.spec import exercise_expectation_member` followed by `if True:` (or `try:`) assigning a no-op lambda to that name. This is the existing shadow fixture with the assignment moved into an unexamined statement.
- `import adaptive_grok.spec as spec`, then `spec.exercise_expectation_member = lambda *args, **kwargs: None` in the module body or as an earlier statement in the test method. The alias stays in `modules` because the store is an attribute, not a `Name`. The call matcher then trusts `spec.exercise_expectation_member(...)`.

The same hole applies to an import-time helper that does `global exercise_expectation_member` and assigns a lookalike: the store is inside a function, so the module scan never sees it. `test_trusted_helper_import_cannot_be_shadowed_by_a_lookalike` only covers a straight module-body name assignment, which this walker does reject.

`FORBID-001` says a lookalike helper must not prove liveness. These forms are lookalikes, the test method is still a collected `TestCase` method, and the no-op call does not fail that method. `expectation_set_findings` then has nothing to report.

### 2. Blocking — the binder treats an unexecuted call as a proof

`_literal_probe_members` accepts every direct expression-statement call in the method body. It does not stop at `return` or `raise`, and it does not read decorators. `_selector_function` also returns `async def` methods.

```909:977:.grok-stack/adaptive_grok/spec.py
        if not is_test_case or not method_name.startswith("test"):
            return None
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name:
                return child
    ...
    for statement in function.body:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
```

Consequences for a member that nothing in the product can produce:

- A real keyword call placed after `return` is still added to the member set. The ordinary runner executes only the `return`, and the test passes.
- `async def test_...` on `unittest.TestCase` is accepted. Calling an async function does not run its body. Installed Python 3.12 `TestCase._callTestMethod` is `if method() is not None:` and does not await a coroutine (`/usr/lib/python3.12/unittest/case.py`, lines 588–591). The same method on 3.14 only warns. The test is reported passed and the helper never runs. `IsolatedAsyncioTestCase`, the base that would run it, is not recognized, because the base check requires the attribute name `TestCase`.
- `@unittest.skip` or `@unittest.expectedFailure` on a method whose body contains the helper call is ignored. Skip does not run the proof. `expectedFailure` turns the helper's `AssertionError` into a passing result.

The architecture for this change says validation only binds the call and the ordinary suite proves the transition. These selectors satisfy the binder while the ordinary suite does not run that transition. The nested-function rejection shows the repair already treats "the call text exists" as insufficient; unreachable, skipped, expected-failure, and unawaited calls are the same gap.

### 3. Blocking — positional arity is treated as observe/mutate/undo

The helper is keyword-only after `member`:

```79:85:.grok-stack/adaptive_grok/spec.py
def exercise_expectation_member(
    member: str,
    *,
    observe: Callable[[], Iterable[str]],
    mutate: Callable[[], object],
    undo: Callable[[], object],
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
```

The binder instead uses:

```974:977:.grok-stack/adaptive_grok/spec.py
        keyword_names = {keyword.arg for keyword in node.keywords}
        complete_call = len(node.args) >= 4 or {"observe", "mutate", "undo"}.issubset(keyword_names)
        if complete_call and isinstance(member_node, ast.Constant) and isinstance(member_node.value, str):
            members.add(member_node.value)
```

`exercise_expectation_member("css-link-count", lambda: set(), lambda: None, lambda: None)` has four positional arguments and no observe/mutate/undo keywords. It cannot match this signature, but `len(node.args) >= 4` records the member as proved. AC-002 says the spec becomes valid only when the selector passes those callables. This call makes the exact-set criterion valid. No test in `tests/test_spec_expectation_sets.py` uses an incomplete or positional call, so deleting the keyword check (`complete_call = True`) is not locked by the suite. That mutant was not executed here.

### Residual, not the verdict

- A real call nested in `with`, `if`, or `try` inside the method is ignored. That false-rejects some probes the ordinary runner would execute, including a `subTest` wrapper. It does not admit a dead member.
- A `TestCase` subclass reached only through a project base class is not recognized. `import adaptive_grok.spec` without an alias is not a trusted module binding.
- Any non-emptiness cue in the same sentence waives the upper-bound finding, even when "at least one" refers to something other than the set.
- `SIG-001` in `change-spec.yaml` is `change_spec_gate_findings_with_reason_executable_mutation_undo_probe`. `release.md` and `requirements.md` still name `change_spec_gate_findings_with_reason_liveness_proof`. The verifier text is the human sentence, not that metric id.
- The probe reader `stat`s then `read_text`s. It is not the `O_NOFOLLOW` descriptor read used by `_contract_digest`. A symlink is rejected at the check, but the open is not atomic with that check.
- `release.md` says no existing package declares a brace set. This review did not re-run the 98-package census. Unexecuted, not charged.

## Verdict

The repair does reject a dead member that has no counted call, and it does close the narrow fixtures from the previous fail (cross-entry token assembly, a missing selector, a module-body name lookalike, a nested uncalled function, and a cross-sentence cue). It does not enforce the obligation those fixtures were meant to stand for. A no-op rebind the shadow scan cannot see, or a call the ordinary `unittest` runner does not run, still makes an unsatisfiable exact-set member validate.

VERDICT: FAIL
