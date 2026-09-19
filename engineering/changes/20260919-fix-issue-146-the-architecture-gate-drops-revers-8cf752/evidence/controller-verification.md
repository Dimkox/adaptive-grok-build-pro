# Controller verification of the #146 patch (independent re-derivation)

Everything in this file was measured by the controller in a private clone, never in the delivery worktree. The patch
was transferred as `git diff` from the delivery tree and re-applied with `git apply` onto a clean `d871ea6` clone, so
the verified bytes are the delivered bytes. No claim below is copied from the implementer's report; each was
re-derived, and the two places where my own earlier note disagreed with the measurement are called out.

## 1. Comparator semantics are untouched (AC-006)

Differential harness: `50` declared contracts (`ARCH.load_architecture` + `ARCH.contract_inventory`) × identity pair
+ `drop-prop` / `desc` / `add-required` / `add-anyOf-branch` / `add-oneOf-branch` / `add-allOf-branch` perturbations ×
policies `{bidirectional, producer_accepted_by_old, consumer_accepts_old}` = **555 verdict lines**, each line
`path|edit|policy|status|reasons`, sorted and compared between `d871ea6` and the patched tree.

```
differing lines: 0
unsupported rows: 80 before, 80 after
```

So no status, no reason tuple and no `unsupported` classification moved. The comparator keeps
`SCHEMA_REFERENCE_ID_FIRST` (`architecture.py:1348`), which is what keeps issue #147's behaviour byte-identical.

## 2. The closure now sees the dependents it could not see before (#146 itself)

`_contract_dependency_closure({target}, state, state)` on the declared inventory, identical inputs in both trees:

| target | dependents at `d871ea6` | dependents with the patch |
|---|---|---|
| `M7-SHADOW-OUTCOME-V1` | — | `M7-SHADOW-COHORT-V1` |
| `M7-TASK-EVIDENCE-V1` | — | `M7-READY-BUNDLE-V1` |
| `M7-PREDECESSOR-BRIDGES-V1` | — | `M7-READY-BUNDLE-V1`, `M7-TASK-EVIDENCE-V1` |
| `LANDING-INPUT-V1` (plain-relative control) | attempt-status, failover-openapi, failover-result | **unchanged** |
| `M7-READY-BUNDLE-V1` | — | — |

Full sweep on the patched tree: **27 target→dependent pairs**, no edge lost versus `d871ea6` (the control row is the
contradiction check that the fix did not simply narrow the closure).

## 3. End-to-end gate arms (real CLI, throwaway clones, `--pre-risk yellow`)

```
before, editing shadow-outcome.v1 (drop a property):
   CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1: removed_property
   CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1: widened_producer_output
after,  same edit:
   CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1: removed_property
   CONTRACT-FACTORY-M7-SHADOW-OUTCOME-V1: widened_producer_output
   CONTRACT-FACTORY-M7-SHADOW-COHORT-V1:  removed_property        <-- the newly re-verified dependent
   CONTRACT-FACTORY-M7-SHADOW-COHORT-V1:  widened_producer_output

control, editing landing-input.v1 (plain-relative reference): byte-identical finding set in both trees
   (6 findings: landing-input removed_property/widened_producer_output, attempt-status x2,
    failover-openapi widened_producer_output, failover-result "unsupported compatibility semantics")
```

The control also confirms the *pre-existing* `unsupported` row for `LANDING-FAILOVER-RESULT-V1` (residual R3) is not
introduced or masked by this change.

## 4. Test arms

`python3 -m unittest -q tests.test_architecture_fitness` in the patched clone → `Ran 115 tests — OK`, including the
seven new arms in `ArchitectureFitnessTests`:

```
test_contract_compatibility_rechecks_unchanged_declared_ref_dependents
test_contract_compatibility_rechecks_dependents_of_every_reference_grammar
test_contract_compatibility_ignores_reference_without_declared_target
test_contract_compatibility_still_reports_referrer_with_undeclared_reference
test_contract_dependency_closure_uses_declared_path_precedence_issue_146
test_contract_dependency_closure_shares_the_comparator_reference_grammar
test_contract_compatibility_fails_closed_on_duplicate_declared_schema_id
```

The implementer's mutation matrix (M0–M8) reports the anti-inheritance lock: forcing the closure to pass `id_first`
fails both `..._issue_146` arms and the spy guard. I did not re-run all nine arms; the two that matter most to me —
M1 (revert the fix: the `$id`/fragment arms fail while the plain-relative control stays green) and M7 (inherit the
comparator precedence: fail) — are pinned by named tests rather than by my re-run, which is the stronger artifact.

## 5. Corrections to my own earlier note

`closure-fix-blast-radius.md` first claimed "exactly one creates a new failure". That was wrong: it enumerated only
*direct* edges and ignored transitivity, and it did not have the patched closure to query. Measured here, **three**
targets gain an unanalyzable dependent — `M7-OPERATOR-HANDOFF-V1`, `M7-PREDECESSOR-BRIDGES-V1` and
`M7-TASK-EVIDENCE-V1` — and all three point at the *same* dependent, `M7-READY-BUNDLE-V1`. That collapses the risk to
one root cause and one unblocking action; see the corrected blast-radius file.
