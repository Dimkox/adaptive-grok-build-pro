# Test plan: complete the technical #104 comparator fix

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Current landing failover OpenAPI self-comparison and capability-description dependency edit | `tests/test_architecture_model.py::ArchitectureModelTests.test_openapi_dependency_closure_accepts_existing_nullable_schemas` |
| P0 | `anyOf` branch inclusion across consumer and producer directions, including reordering, duplicate branches, nullable branches, and changed constraints | `tests/test_architecture_model.py::ArchitectureModelTests.test_anyof_directional_union_inclusion_is_proven` |
| P0 | Split/overlapping destination coverage cannot produce a false compatible verdict | `tests/test_architecture_model.py::ArchitectureModelTests.test_anyof_ambiguous_union_coverage_fails_closed` |
| P0 | Irrelevant numeric/string interval keywords cannot establish false branch disjointness; mixed source types remain conservative | `tests/test_architecture_model.py::ArchitectureModelTests.test_anyof_disjointness_ignores_constraints_for_other_json_types` |
| P0 | Finite JSON Schema numeric equality treats `1` and `1.0` alike for const, enum, and branch inclusion | `tests/test_architecture_model.py::ArchitectureModelTests.test_json_schema_numeric_equality_normalizes_const_and_enum` |
| P0 | Strict `$defs` pointer resolution for local, relative-inventory, and exact `$id` references | `tests/test_architecture_model.py::ArchitectureModelTests.test_schema_resolver_supports_bounded_json_pointers` |
| P0 | Malformed pointer, unknown inventory target, path escape, ambiguous ID, cycle, depth, node, and pair-budget cases fail closed | `tests/test_architecture_model.py::ArchitectureModelTests.test_schema_resolver_and_anyof_limits_fail_closed` |
| P1 | `date-time` is accepted and compared as contract metadata; a changed format cannot pass | `tests/test_architecture_model.py::ArchitectureModelTests.test_date_time_format_is_compared_as_contract_metadata` |
| P1 | `prefixItems` remains outside the supported subset | `tests/test_architecture_model.py::ArchitectureModelTests.test_unrelated_schema_keywords_remain_unsupported` |

## Automated checks

- Red/green: add the failing characterization cases above before changing comparator behavior.
- Focused: run the named `ArchitectureModelTests` methods and the full `tests.test_architecture_model` module.
- Contract/profile: `python3 scripts/grok_architecture.py fitness --base <route-base> --worktree --json` against the capability metadata edit; assert the dependency OpenAPI no longer reports unsupported while the producer enum expansion remains incompatible under existing policy.
- Final: `python3 scripts/grok_verify.py --mode pr`, then route-selected code, test, and security reviews against the verified candidate fingerprint.

## Manual checks

- Confirm the diff changes only comparator/tests/change evidence; no schema declarations, policy rules, deployed state, or profile facts change.
- Inspect reports and `grok_status.py --json` for zero fingerprint-bound evidence gaps.
