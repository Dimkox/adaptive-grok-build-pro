# Implementation plan — issue #146

## Vertical task

Make the gate's contract dependency closure resolve exactly the reference grammar the comparator resolves, without
changing any comparator verdict.

## Order of execution

1. Reproduce with a control that must flip: an `$id`-referenced pair (fails today), a `file#/$defs/...` pair (fails
   today), a plain-relative pair (works today, and must keep working).
2. Lift the reference grammar out of `_SchemaResolver` into three shared functions; leave resolution *policy* at the
   call site by passing an explicit `precedence` — `SCHEMA_REFERENCE_ID_FIRST` for the comparator (byte-identical, so
   issue #147 is neither fixed nor worsened here) and `SCHEMA_REFERENCE_PATH_FIRST` for the closure.
3. Rebuild `_external_contract_reference_paths` on the shared functions with per-inventory `$id`→paths and
   declared-path tables; make its drop policy a deny-list (`SCHEMA_REFERENCE_UNRESOLVED`) so a future reason cannot
   silently discard an edge.
4. Ambiguity fails closed with the comparator's own `ambiguous declared schema id` error, only when a reference
   actually names the colliding `$id`.
5. Tests M0–M8 mutation matrix; differential proof that comparator output is unchanged.

## Explicitly not doing

- Changing comparator precedence or fixing #147.
- Editing any contract, `architecture/system.yaml`, `architecture/rules.yaml`, compatibility mode or policy.
- Weakening any existing assertion; none needed (full root discovery stayed green).
