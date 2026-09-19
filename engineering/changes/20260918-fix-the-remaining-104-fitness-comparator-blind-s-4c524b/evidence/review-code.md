# Code review — #104

**Verdict: PASS.** The final diff corrects the JSON Schema finite-value comparison false incompatibility while preserving JSON type distinctions and conservative behavior for unsupported comparisons.

## Findings

- `_schema_value_key` gives `int` and `float` a common JSON `number` tag, relying on Python numeric equality/hash for the mathematical value. It handles `bool` first, so `true` remains distinct from `1`; the same normalization is applied recursively to arrays and objects.
- `_scalar_satisfies` now uses this key for `const` and `enum` membership. This prevents finite branch comparisons from treating `1` and `1.0` as disjoint.
- Reproduced `anyOf` schemas containing `const: 1` vs `const: 1.0` and `enum: [1]` vs `enum: [1.0]`: both are compatible in both consumer and producer directions. `true` vs numeric `1` remains incompatible.
- The prior type-gated interval fix remains present: `minimum`/`maximum` do not constrain strings, and `minLength`/`maxLength` do not constrain integers. Mixed type families with interval constraints stay `unknown`.

## Verification

- `python3 -m unittest tests.test_architecture_model` — **79 tests passed**.
- Ad hoc `compare_contracts` checks for numeric const/enum equivalence across both compatibility directions — **all compatible**; bool-vs-number — **incompatible**.
- Recursive value-key check confirms nested object/array numeric equivalence and `true`/`1` distinction.
- `git diff --check` — **passed**.

No code-review blockers found in the reviewed comparator changes.
