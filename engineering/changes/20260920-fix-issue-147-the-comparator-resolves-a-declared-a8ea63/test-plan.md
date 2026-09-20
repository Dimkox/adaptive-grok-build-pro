# Test plan — issue #147

## Scenarios

| P | Scenario | Evidence |
| --- | --- | --- |
| P0 | Capture case flips `compatible → incompatible (narrowed_constraint,)`; control unchanged | `tests/test_architecture_model.py::ArchitectureModelTests::test_path_naming_reference_resolves_to_the_declared_path_not_a_shadowing_id` + `repro.py` (harness §1) |
| P0 | Shipped inventory: 0 differing rows of 25,328, grid stated | `differential.py`, `diff_rows.py`; results in `implementation-arms.md` §1 |
| P0 | Non-vacuity: 9 injected capture claimants → 1,178 differing rows both directions | same harness, control mode |
| P0 | Ambiguity stays loud under path-first | `test_path_naming_reference_with_a_colliding_declared_id_still_fails_closed` |
| P1 | `$id`-only (IRI) references keep resolving | `test_reference_that_names_no_declared_path_still_resolves_through_the_id_table` |
| P1 | Guard rejects cross-path `$id`, accepts self-`$id`; shipped inventory collision-free | `test_model_rejects_a_declared_schema_id_that_is_another_contract_path`, `test_declared_inventory_carries_no_schema_id_path_collision` |
| P1 | Mutations m1–m7 with red/green expectations | `mutations.py`, recorded in `implementation-arms.md` |
| P2 | Union of #149 still load-bearing; `architecture_fitness.py` diff is docstring-only | m6/m7 + executable-AST comparison |

## Automated checks

```
python3 -m unittest -q tests.test_architecture_fitness tests.test_architecture_model \
    tests.test_governance_fitness tests.test_structure        # 238 tests OK
ruff check .grok-stack/adaptive_grok/ tests/                   # All checks passed!
git diff --check                                               # clean
git diff --numstat -- tests/                                   # additions only (322 removed=0 for the model file)
GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr
```

## Manual checks

- Confirm the only pre-existing arm that changed is the claimant-attribution subtest, and that its scope and status
  assertions are intact (FORBID-001).
- Re-derive the differential in a private clone; do not accept the reported row counts on trust — the row count and the
  grid must be quoted together.
- Verify `engineering/changes/<pkg>/evidence/measurement-harness.md` blocks run as embedded (extract and execute).

## Environment notes

No pytest here or in the runner image (plain `unittest`); `grok_verify` resolves its root from the script path, so run
it from inside this worktree; scratch lives under `/tmp/idprec147` and its content is embedded in the package, since
`/tmp` has before been cleared by a concurrent agent.
