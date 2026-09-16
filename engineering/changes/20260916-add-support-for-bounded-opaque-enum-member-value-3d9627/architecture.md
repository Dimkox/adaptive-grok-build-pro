# Architecture — comparator enum-member extension

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Components

- `.grok-stack/adaptive_grok/architecture.py`: new `_valid_enum_member` beside `_valid_schema_scalar`; `_unsupported_schema`'s enum loop gains one branch (scalar → bounded-structural → reject). Budget: `resolver.consume()` per node (resolver path) or `counter[0] += 1` against `MAX_PARSED_NODES`; depth capped at `MAX_DEPTH`.
- `tests/test_architecture_model.py`: characterization matrix including five adversarial members.
- Untouched: contract files, `architecture/system.yaml`, `architecture/rules.yaml`, `_compare_schema_direction`, `_comparison_canonical_values`, const/keyword/composition/ref analysis, the deployed Trust CI side (never in this trust domain).

## Flow

contract pair → `_contract_compatibility` → `compare_contracts` → `_unsupported_schema` (per side) → now passes for object enums → direction comparison over canonical-byte sets → compatible/incompatible verdict instead of `unsupported`.

## Decisions

Members are treated as opaque VALUES, never subschemas: `$ref` keys inside a member are data (FORBID-001), matching JSON Schema's own enum semantics. Budget accounting mirrors the existing per-node pattern so a crafted giant member cannot slow analysis for free.
