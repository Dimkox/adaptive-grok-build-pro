# Controller measurement — declared 50-record inventory, base 2f66ba6 vs merged d871ea6

Method (reproducible): `python3 <private-scratch>/probe_declared_inventory.py <repo>` — inventory from
`ARCH.load_architecture(root)` + `ARCH.contract_inventory(root, snap)` (**50 declared records**, not the 38 files
under `factory/contracts/**`), each contract compared under its **declared** compatibility policy, base = shipped
document, head = one mechanical edit of the first `anyOf` in document order.

Provenance note: the first run of this table used a working tree that still carried one of my own probe commits (a
`title` inside the attempt-status union). It was re-run after `git reset --hard d871ea6` with `git status --porcelain`
empty and no `probe-edit` string in any contract. One cell changed, in the merged code's favour — see the
`drop-branch` column. Why this file exists at all: two earlier tables of mine were built on a factory-only
inventory, and an under-declared inventory converts real verdicts into `unsupported_schema_keyword` because
`_SchemaResolver.resolve` requires every cross-file `$ref` target to be declared. Both earlier tables are superseded.

## Identity analyzability (json_schema kind)

| tree | compatible | blocked |
|---|---|---|
| `2f66ba6` (pre-#133) | 14 / 38 | 26 |
| `d871ea6` (#133 merged) | **36 / 38** | `CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1`, `CONTRACT-FACTORY-M7-READY-BUNDLE-V1` |

#133 unlocked 22 contracts, not the three `anyOf` ones. Whitelist ablation at the merged tree (remove one keyword,
full declared inventory, count contracts that flip back): `$defs` 19, `format` 10, `anyOf` 4
(`landing-attempt-status`, `landing-failover-result`, `landing-provider-observation`, and the
`landing-failover.v1.json` OpenAPI). Composition was necessary but not sufficient — the reference-grammar half
carried most of the fleet.

## Edit classes at merged main (pristine tree, declared policies = bidirectional)

| contract (first anyOf site) | identity | reorder | add `null` branch | add **novel** branch | drop branch | title edit in branch |
|---|---|---|---|---|---|---|
| attempt-status `properties/reason_code` = `string(1..128) \| null` | compatible | compatible | compatible | `unsupported_schema_comparison` | **incompatible `changed_constraint`** | `unsupported_schema_comparison` |
| failover-result `attempts/items/receipt` = `$ref \| null` | compatible | compatible | compatible | `unsupported_schema_comparison` | `unsupported_schema_comparison` | `unsupported_schema_keyword` |
| provider-observation `usage_input_units` = `integer(0..1e7) \| null` | compatible | compatible | compatible | `unsupported_schema_comparison` | **incompatible `changed_constraint`** | `unsupported_schema_comparison` |

`add null branch → compatible` is **correct**, not a hole: all three unions are already `X | null`, so the instance
set does not change. This is evidence that #133 performs real inclusion reasoning instead of canonical-byte equality.

## Soundness probe (synthetic, single-record inventory, `string`/`integer` branches)

| edit | bidirectional | producer_accepted_by_old | consumer_accepts_old |
|---|---|---|---|
| `anyOf` +branch (real widening) | incompatible `changed_constraint` | incompatible `changed_constraint` | **compatible** (spec-correct: widening is consumer-safe) |
| `oneOf` +branch | incompatible `changed_constraint` | incompatible | incompatible |
| `allOf` +branch | incompatible `changed_constraint` | incompatible | incompatible |
| any keyword −branch (narrowing) | incompatible `changed_constraint` | — | — |
| `anyOf` ⇄ `oneOf` swap, same branches | `unsupported_schema_comparison` (fail-closed) | | |
| duplicate branches `[S,S] → [S]` | `anyOf` compatible (dedup preserves the language) · `oneOf` incompatible (dedup would WIDEN it) · `allOf` incompatible | | |

Fail-closed on malformed/out-of-subset constructs (identical pair → `unsupported_schema_keyword`): `anyOf: []`,
`oneOf: []`, `allOf: []`, 17 branches, non-dict branch, `not`, `if` without `then`, `else`, `prefixItems`,
`$comment`. Numeric equality does not leak into types: `const 1 → 1.0` and `enum [2] → [2.0]` compatible, while
`type integer → number` stays `incompatible changed_type`.

## Conclusion so far

Two claims here must be read as corrected. The first version of this file stated that no false-certification case
existed against the merged comparator, and the synthetic sweep in `analysis-ai_architect.md` reported the same. Both
were wrong, and the `architect` lane found the case: `_SchemaResolver.resolve` consults the declared-`$id` table
before the declared-path table, so a record whose `$id` equals another contract's path **captures** references that
name that path, and a real consumer-breaking narrowing (`minLength 1 -> 9`) in the captured target then reports
`compatible ()` where the pre-#133 comparator reported `incompatible (narrowed_constraint)`. Reproduced independently
with a control arm (remove the claimant -> both trees report `incompatible`), so the delta is caused by #133's `$id`
lookup and not by `anyOf`. Measured reachability in the shipped inventory at `d871ea6`: 50 contracts, 41 distinct
`$id` values, none equal to a declared path, 0 references where the two tables disagree -> **latent, not live**.
Filed as issue #147. Everything else below stands: on the composition axis the comparator never reported `compatible`
for a changed instance set in any case I could produce, and unprovable edits degrade to `unsupported`.

Residual #104 incompleteness, all fail-closed rather than unsound, each still leaving a contract partly
write-once:
1. **R1** — widening a union with a *novel* alternative yields `unsupported_schema_comparison` instead of a
   producer-break verdict.
2. **R2** — narrowing a union whose dropped branch is a `$ref` (failover-result) yields
   `unsupported_schema_comparison`, while the same edit on scalar branches yields a real `incompatible`.
3. **R3** — an annotation-only edit (`title`) inside a union branch yields `unsupported_schema_keyword` in
   failover-result and `unsupported_schema_comparison` elsewhere: divergent, and both are non-verdicts.
4. **R4** — `_event_meaning` (merged main `architecture.py:3037`) still descends only `("oneOf","allOf")`, so
   descriptions reachable only through `anyOf` never enter event-meaning comparison; measured latent (no `event`
   contract currently reaches an `anyOf`), so it is a label/coverage gap, not a silent pass.

Distinct and already tracked elsewhere, therefore deliberately NOT re-filed here: annotation-vs-`compatible`
metadata behaviour (#120, PR #137) and the closure reverse-edge loss for `$id`/fragment refs (#146).

5. **R5** *(soundness, latent — issue #147)* — declared-`$id` resolution takes precedence over the declared-path
   table (`architecture.py:1239-1247`), so a path-like `$id` captures references naming another contract's path and a
   real narrowing of that target reports `compatible`. Unlike R1–R4 this is **not** fail-closed: it is a false
   certification, reachable the moment one contract declares a path-like `$id`, which nothing currently rejects.
   Measured unreachable today (41 declared `$id` values, none equal to a declared path).

## Gate-path corroboration

`scripts/grok_architecture.py fitness` probes (throwaway clones, `--pre-risk yellow`) reproduce the same shape:
`contract_compatibility` reports `unsupported compatibility semantics` for `LANDING-ATTEMPT-STATUS-V1`,
`LANDING-FAILOVER-OPENAPI-V1` and `LANDING-FAILOVER-RESULT-V1` on a title-in-branch probe, while capability-only
edits no longer produce `unsupported_openapi_construct` anywhere.
