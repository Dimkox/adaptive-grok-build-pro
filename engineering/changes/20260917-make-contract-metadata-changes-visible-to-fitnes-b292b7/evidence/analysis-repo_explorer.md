# Repo explorer — issue #120

## Reproduction

Inspected exact routed base `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217` in a disposable detached worktree. Ran `python3 scripts/grok_architecture.py --root <worktree> fitness --base <base> --worktree --json` after independently resetting and mutating only `factory/contracts/jsonschema/landing-failover-config.v1.schema.json` for each case.

| Mutation | Changed path detected | Compatibility applicability | Fitness | Findings |
|---|---|---|---|---|
| Add root `description` | yes | `applicable` | pass | none |
| Add root `title` | yes | `applicable` | pass | none |
| Add optional `properties.investigator_extra: {"type":"string"}` | yes | `applicable` | fail | `CONTRACT-FACTORY-LANDING-FAILOVER-CONFIG-V1: widened_producer_output` |

Thus the metadata cases are not skipped or outside the declared contract inventory. Exact base and worktree gate match the issue's reported behavior.

## Comparator findings

- `architecture.py::_SUPPORTED_SCHEMA_KEYS` accepts both `title` and `description`; `_unsupported_schema()` also checks that their values are strings.
- `_compare_schema_direction()` checks `$id`, `$schema`, constraints, properties, and other wire-shape keywords, but never reads `title` or `description`.
- `_compare_contracts_impl()` notices canonical document bytes differ, proceeds through the declared `bidirectional` structural comparison, then returns `compatible` because no wire-shape reason was collected.
- Structural checks remain effective in the control case. The defect is missing semantic visibility for accepted document metadata, not a skipped or weakened structural validator.
- Scope confirmed here is registered `json_schema`. `_event_meaning()` separately includes nested event-schema `description`; OpenAPI metadata behavior was not measured and should not be generalized from this reproduction.

## Minimal recommendation

For supported `json_schema` documents, compare accepted `title` and `description` metadata as an explicit, bounded document-meaning dimension, including nested schema locations. When changed, return a distinct compatibility reason such as `changed_documentation` (or equivalently explicit changed-document-metadata finding) so fitness is reviewable; preserve all existing structural comparisons and their reason codes. Do not silently treat the edit as a wire-shape break: the distinct reason makes the nature of the change clear while preventing a clean `pass` with zero findings.

Add regression cases for root and nested `description`/`title` changes on the same registered bidirectional JSON Schema, asserting the new distinct reason; retain the optional-property structural control and assert its existing `widened_producer_output` result. Also retain a clean unchanged-contract case to show compatibility remains `not_applicable` only when appropriate. Keep OpenAPI/event expansions out of this fix unless their own behavior is separately characterized.
