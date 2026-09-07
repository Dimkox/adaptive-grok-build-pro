# Test review (re-review after proven_units repair)

Change: `20260906-inert-control-flow-shells-must-not-become-ambigu-f88955`
Route: `f88955abe6a5`
Reviewer: `test_reviewer` (read-only)
Verdict: **pass**

## Scope inspected

- `tests/test_hooks.py` (`test_benign_shell_expansion_and_read_chain_remain_soft`, existing deny methods)
- `tests/test_pre_tool_circuit_breaker.py`
- Prior test-review residual: `;;;` / separator-only shells were uncharacterized

No product code was edited.

## Separator-only shells now characterized as deny

`test_benign_shell_expansion_and_read_chain_remain_soft` now splits:

| Command | Expected |
| --- | --- |
| `true; ; true` | **allow** (inert empty unit between proven units) |
| `;;;` | **deny** `ambiguous-sensitive-shell` (`proven_units == 0`) |
| `;` | **deny** `ambiguous-sensitive-shell` (`proven_units == 0`) |

The previous residual gap is closed. Empty-command-after-unwrap is fail-closed; empty unit after a proven skip/unit remains inert.

## Allow coverage still green

Required Layer 1 allows remain in the same method: `|` `;` `()` `&&` `||` proven reads (`true; true`, `true || true`, pipes, `cd .; git status --short`, wrappers, format parens). All assert `decision == allow`.

## Existing deny suite not weakened

`test_ambiguous_dynamic_shell_composition_denies_without_classifier_match` still denies `eval` / `if/then` / `exec` / dynamic `$cmd` / alias forms with `ambiguous-sensitive-shell`. Wrapper, dispatcher, nested-shell, and authority-metacharacter denials remain. Ledger still must not serialize `git push origin feature`.

## Circuit-breaker characterization intact

| Case | Status |
| --- | --- |
| Distinct catch-all objectives (`eval` then `exec`) do not share one BLOCK | covered, green |
| Same catch-all shape (`eval` then `eval`) trips objective breaker | covered, green |
| Classified curl POST coarseness (`external-write`, no `command`) | covered, green |
| Exact retry schema 3 | covered, green |

## Verification evidence

```
python3 -m unittest tests.test_hooks tests.test_pre_tool_circuit_breaker -v
```

Result: **36 tests, OK** (29.092s). No failures.

## Residual risks (tests)

- Nested `bash -lc` with `;` and `git --no-pager log` remain unproven over-denies (accepted).
- Empty authority-shape collapse for unknown unproven shells still has no dedicated extra method beyond `;;;` / `;`.

## Verdict

**pass** — `;;;` and `;` are characterized as deny; proven-unit allows and the existing deny/breaker suite stay green.
