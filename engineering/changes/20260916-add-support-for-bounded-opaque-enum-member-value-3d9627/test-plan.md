# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Object-enum documents become analyzable with correct directional verdicts | `test_object_valued_enum_members_are_bounded_opaque_values_not_schemas` |
| P0 | Adversarial members stay rejected (dup, NaN, non-str key, >depth, >budget) | same test, subTest arms + patched MAX_PARSED_NODES |
| P1 | No regression in the closed subset or fitness categories | `tests.test_architecture_model`, `tests.test_architecture_fitness`, `tests.test_json_schema_subset` (177), full `grok_verify` |

Commands: `python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness tests.test_json_schema_subset`, then `python3 scripts/grok_verify.py --mode pr`.
