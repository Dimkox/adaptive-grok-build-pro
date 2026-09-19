# Controller measurement — declared 50-record inventory, base 2f66ba6 vs merged d871ea6

Method (reproducible): `python3 <private-scratch>/sweep_identity.py <repo> <unit>` and its sibling scripts, now
committed as **`measurement-harness.md` in this directory** — every table below names the block (A, B, C, C-2, D, E,
F) that reproduces it. Inventory from `ARCH.load_architecture(root)` + `ARCH.contract_inventory(root, snap)`
(**50 declared records**, not the 38 files under `factory/contracts/**`), each contract compared under its
**declared** compatibility policy, base = shipped document, head = one mechanical edit of the first `anyOf` in
document order. Every comparison run uses **one process per tree**: re-importing
`adaptive_grok.architecture` after a second `sys.path.insert` returns the first tree's cached module, so a
same-process A/B compare silently compares a tree with itself (measured proof in `measurement-harness.md`,
ground rule 1).

**Two units, always named.** *json_schema unit* = the 38 declared `json_schema` records; *all-kinds unit* = all
50 declared records (38 json_schema, 9 openapi, 2 signed_payload, 1 event). Mixing them silently is how the
ablation line below was wrong for a revision.

Provenance note: the first run of this table used a working tree that still carried one of my own probe commits (a
`title` inside the attempt-status union). It was re-run after `git reset --hard d871ea6` with `git status --porcelain`
empty and no `probe-edit` string in any contract. One cell changed, in the merged code's favour — see the
`drop-branch` column. Why this file exists at all: two earlier tables of mine were built on a factory-only
inventory, and an under-declared inventory converts real verdicts into `unsupported_schema_keyword` because
`_SchemaResolver.resolve` requires every cross-file `$ref` target to be declared. Both earlier tables are superseded.

## Identity analyzability — both units (reproduced by block A)

| tree | json_schema unit (denominator 38) | all declared kinds (denominator 50) |
|---|---|---|
| `2f66ba6` (pre-#133) | **12 / 38** (26 blocked) | **21 / 50** (29 blocked) |
| `d871ea6` (#133 merged) | **36 / 38** (2 blocked) | **46 / 50** (4 blocked) |

Blocked at `d871ea6`, by name:

| record | kind | reason | carried by |
|---|---|---|---|
| `CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1` | json_schema | `unsupported_schema_keyword` | `prefixItems` (per `analysis-ai_architect.md` follow-up item 10) |
| `CONTRACT-FACTORY-M7-READY-BUNDLE-V1` | json_schema | `unsupported_schema_keyword` | urn-`$ref` cascade into `prefixItems` (same source) |
| `CONTRACT-FACTORY-LANDING-OPENAPI-V1` | openapi | `unsupported_openapi_construct` | measured: no `servers` key at root (`landing-dogfood.v1.json` root keys are `components`/`info`/`openapi`/`paths`) and 56 `$ref` occurrences; the root-`servers` shape belongs to `CONTRACT-ADAPTIVE-DEMO-OPENAPI` in the row below |
| `CONTRACT-ADAPTIVE-DEMO-OPENAPI` | openapi | `unsupported_compatibility_policy` | not a construct gap: `_compare_contracts_impl` admits `openapi` only under `bidirectional`/`exact`/`versioned_break` (`architecture.py:3105-3107`) while this record declares `producer_accepted_by_old` — blocked identically at both trees, so it is not part of the unlock delta |

#133 unlocked **24** of the 38 declared `json_schema` contracts and **25** of 50 across all kinds. Exactly **3** of
those unlocked records contain an `anyOf` (the three landing unions this audit was about), so `anyOf` was necessary for those three
and nowhere near sufficient for the other 22 — the wording is deliberately not "the three `anyOf` ones", which reads as if
no unlocked contract used `anyOf` at all.

> Superseded row: the first revision of this table (commit `d3e0d49`) stated the pre-#133 json_schema row as
> "14 / 38 | 26 blocked" and derived "#133 unlocked 22 contracts" from it. `14 + 26 = 40 ≠ 38`, so the row was
> arithmetically impossible against its own denominator; the measured base row is **12 / 38, 26 blocked**, and the
> unlock count is **24** json_schema / **25** all kinds. The same wrong base number had propagated into
> `change-spec.yaml` AC-002 (`was 14/38`), `objective.success_metric`, and `requirements.md` AC-002; all three are
> corrected in this revision. The head row (`36 / 38`) was right and is re-confirmed by block A.

## Whitelist ablation at the merged tree — both units (reproduced by block B)

Remove one keyword from `_SUPPORTED_SCHEMA_KEYS` (read at call time by `_unsupported_schema`,
`architecture.py:1429`, so no file is edited) and re-sweep identity analyzability:

* **json_schema unit** (denominator = 38 declared `json_schema`, baseline 36 analyzable): `$defs` flips back
  **23** contracts (36 → 13/38), `format` **9** (→ 27/38), `anyOf` **3** (→ 33/38).
* **all-kinds unit** (denominator = 50 declared records, baseline 46 analyzable): `$defs` flips back **24**
  contracts (46 → 22/50), `format` **10** (→ 36/50), `anyOf` **4** (→ 42/50).

Composition was necessary but not sufficient; the `$defs` half carried most of the fleet. The same command prints
the other keys for contrast: `oneOf` 6/3, `allOf` 8/6, `if` and `then` 8/6 each — but `oneOf`, `allOf`, `if` and
`then` were already whitelisted at `2f66ba6`, so those rows measure coverage, not #133's delta. Block E prints both
whitelists: 24 keys at base → 27 at head, and the delta is exactly `{'$defs', 'format', 'anyOf'}` — three keys,
where #133's own title named one.

> Superseded sub-measurement: an earlier revision of this file reported `$defs` 19 / `format` 10 / `anyOf` 4. Those
> came from sweeping the `factory/contracts/**/*.json` glob (38 files, some undeclared; kinds and policies assumed
> rather than read from `architecture/system.yaml`) while labelling it "full declared inventory". The numbers above are
> from a single script over the gate's own inventory; the direction of the conclusion is unchanged, the magnitudes were
> not.
>
> Why the mislabel survived one full review: the glob count (38 files) and the declared `json_schema` count (38
> records) are **equal but different sets** — the glob is 28 declared `json_schema` + 7 `openapi` + 1 `event` + 2
> files that are not declared at all (`earned-autonomy.v1.schema.json`, `m7-autonomy-bridge.v1.schema.json`), while
> 10 declared `json_schema` records live outside `factory/contracts/`. Printed by block E. A count that agrees by
> accident is not a provenance check.

## Disagreement with a committed agent report, recorded not smoothed

`analysis-ai_architect.md` (all-kinds figures: "25 of 50 … moved from un-analyzable to analyzable", "4/50 remain
un-analyzable at `d871ea6` (was 29/50 at `2f66ba6`)") agrees with block A exactly. `analysis-integration_architect.md`
states "46/50 declared contracts fully in-subset (**baseline 20/50**)": the head half matches, the base half is one
short of the measured **21/50**, and the four still-blocked records it names match block A. Its sentence is left
verbatim (agent reports are not rewritten); the discrepancy is recorded here and belongs to whoever next re-runs
block A on that lane's assumptions.

## Edit classes at merged main (pristine tree, declared policies = bidirectional) — reproduced by block C

The inserted branch **shape** is part of every label now; the earlier column "add novel branch" hid three different
edits behind one phrase and reported a verdict that the merged comparator does not produce.

| contract (first anyOf site, branch 0 shape) | identity | reorder | + duplicate `null` | + **novel non-subsuming scalar** | + **subsuming** branch | + **object-valued** branch | + **`$ref`-valued** branch | drop branch 0 | title edit in branch 0 | tighten numeric bound in branch 0 |
|---|---|---|---|---|---|---|---|---|---|---|
| attempt-status `properties/reason_code` = `string(1..128) \| null`; novel `integer`, subsuming `string` | compatible | compatible | compatible | **`incompatible (changed_constraint)`** | `unsupported_schema_comparison` | `unsupported_schema_comparison` | `unsupported_schema_comparison` | **`incompatible (changed_constraint)`** | `unsupported_schema_comparison` | `unsupported_schema_comparison` |
| provider-observation `usage_input_units` = `integer(0..1e7) \| null`; novel `boolean`, subsuming `integer` | compatible | compatible | compatible | **`incompatible (changed_constraint)`** | `unsupported_schema_comparison` | `unsupported_schema_comparison` | `unsupported_schema_comparison` | **`incompatible (changed_constraint)`** | `unsupported_schema_comparison` | `unsupported_schema_comparison` |
| failover-result `attempts/items/receipt` = **`$ref`** \| `null`; novel `integer`, subsuming `object` | compatible | compatible | compatible | `unsupported_schema_comparison` | `unsupported_schema_comparison` | `unsupported_schema_comparison` | `unsupported_schema_comparison` | `unsupported_schema_comparison` | `unsupported_schema_keyword` | n/a — branch 0 is a bare `$ref` with no numeric bound, so the edit leaves the document byte-identical (verified, block C) |

`add duplicate null → compatible` is **correct**, not a hole: all three unions are already `X | null`, so the
instance set does not change. Same for `add novel non-subsuming scalar → incompatible`: widening `string|null` with
`integer` really does break the producer, and the merged comparator now *says so* — this is the cell the previous
revision of this table got wrong, and it is the difference between "the proof stops" and "the proof never ran".
That the third row returns a non-verdict for the identical edit is the residual: the union still contains a
`$ref`-valued branch, which is outside `_SCALAR_PROOF_KEYS` (`architecture.py:1697-1700`), so nothing is provable
about it and the whole node fail-closes (`analysis-architect.md` §2, its own edit table, reports the same three
outcomes and was the file this table should have matched the first time).

## Soundness probe (synthetic, single-record inventory, `string`/`null`/`integer` branches) — reproduced by block D

| edit | bidirectional | producer_accepted_by_old | consumer_accepts_old |
|---|---|---|---|
| `anyOf` +branch (real widening) | `incompatible (changed_constraint)` | `incompatible (changed_constraint)` | **`compatible ()`** — spec-correct: widening is consumer-safe |
| `oneOf` +branch | `incompatible (changed_constraint)` | `incompatible (changed_constraint)` | `incompatible (changed_constraint)` |
| `allOf` +branch | `incompatible (changed_constraint)` | `incompatible (changed_constraint)` | `incompatible (changed_constraint)` |
| `anyOf` −branch (narrowing) | `incompatible (changed_constraint)` | `compatible ()` — correct, a narrower producer output is still accepted | `incompatible (changed_constraint)` |
| `oneOf` / `allOf` −branch | `incompatible (changed_constraint)` | `incompatible (changed_constraint)` | `incompatible (changed_constraint)` |
| `anyOf` ⇄ `oneOf` swap, same branches | `unsupported_schema_comparison` (fail-closed) | same | same |
| `anyOf` ⇄ `allOf` swap, same branches | `unsupported_schema_comparison` (fail-closed) | same | same |
| duplicate branches `[S,S] → [S]` | `anyOf` compatible (dedup preserves the language) · `oneOf` incompatible (dedup would WIDEN it) · `allOf` incompatible | same in all three modes | same |
| `anyOf[const 1] → anyOf[const 1.0]` | `unsupported_schema_comparison` | same | same |
| `anyOf[enum[2]] → anyOf[enum[2.0]]` | `unsupported_schema_comparison` | same | same |
| `anyOf[type integer] → anyOf[type number]` | `unsupported_schema_comparison` | `unsupported_schema_comparison` | **`compatible ()`** — correct, `integer ⊆ number` |

Fail-closed on malformed/out-of-subset constructs (identical pair → `unsupported_schema_keyword`): `anyOf: []`,
`oneOf: []`, `allOf: []`, 17 branches, non-dict branch, `not`, `if` without `then`, `else`, `prefixItems`,
`$comment`. Numeric equality does not leak into types outside unions either: `const 1 → 1.0` and `enum [2] →
[2.0]` compatible, while `type integer → number` stays `incompatible changed_type`.

> Superseded cell set: the first revision of this table carried "—" for the two single-direction columns of the
> narrowing row and had no `anyOf` ⇄ `allOf` swap row and no in-union numeric rows. All of them are measured now
> (block D), and none of the fills changed a direction.

## Conclusion so far

Two claims here must be read as corrected. The first version of this file stated that no false-certification case
existed against the merged comparator, and the synthetic sweep in `analysis-ai_architect.md` reported the same. Both
were wrong, and the `architect` lane found the case: `_SchemaResolver.resolve` consults the declared-`$id` table
before the declared-path table, so a record whose `$id` equals another contract's path **captures** references that
name that path, and a real consumer-breaking narrowing (`minLength 1 -> 9`) in the captured target then reports
`compatible ()` where the pre-#133 comparator reported `incompatible (narrowed_constraint)`. Reproduced independently
with a control arm (remove the claimant -> both trees report `incompatible`), so the delta is caused by #133's `$id`
lookup and not by `anyOf`. Measured reachability in the shipped inventory at `d871ea6`: 50 contracts, 41 distinct
`$id` values, none equal to a declared path, 0 of 86 cross-file `$ref` bases name both a declared `$id` and a
declared path -> **latent, not live** (block E). Filed as issue #147. Everything else below stands: on the
composition axis the comparator never reported `compatible` for a changed instance set in any case I could produce,
and unprovable edits degrade to `unsupported`.

Residual #104 incompleteness. CAR-1..CAR-4 are fail-closed (incompleteness, each still leaving a contract partly
write-once); CAR-5 is **not** fail-closed and is labelled as a soundness defect with its reachability measurement.

1. **CAR-1** — the union-inclusion proof stops with `unsupported_schema_comparison` whenever the added branch
   **subsumes** an existing one (`string` added over `string(1..128) \| null`) and whenever a branch is
   **object-valued** or **`$ref`-valued**; in those cases a real widening or a real narrowing of a union containing
   such a branch is not provable at all. It is *not* true that any novel alternative is a non-verdict: a novel,
   non-subsuming **scalar** alternative produces a real `incompatible (changed_constraint)` producer-break verdict
   (block C, rows 1–2).
   > Superseded residual: this list's first revision said "widening a union with a *novel* alternative yields
   > `unsupported_schema_comparison` instead of a producer-break verdict". Measured at `d871ea6`, adding
   > `{"type":"integer"}` to `landing-attempt-status/properties/reason_code` and `{"type":"boolean"}` to
   > `landing-provider-observation/properties/usage_input_units` both yield `incompatible (changed_constraint)`.
   > `analysis-architect.md` table 2 reported the correct verdict at the time; this table disagreed with it and this
   > table was the one written down. Where the two committed tables disagreed, the measured one wins.
2. **CAR-2** — narrowing a union whose dropped branch is a `$ref` (failover-result `attempts/items/receipt`) yields
   `unsupported_schema_comparison`, while the same edit on scalar branches yields a real `incompatible`.
3. **CAR-3** — an annotation-only edit (`title`) **inside** a union branch yields `unsupported_schema_keyword` in
   failover-result (where branch 0 is a bare `$ref` and `$ref`+sibling is barred, `architecture.py:1431-1437`) and
   `unsupported_schema_comparison` elsewhere: divergent, and both are non-verdicts (block C). The same class one level
   up is wider still and is *not* a separate residual number: adding `title` **beside** the `anyOf` key on the union
   node yields `unsupported_schema_comparison` in all three policy modes on all three contracts (block C-2, 9 cells,
   9 non-verdicts), because `_compare_schema_direction` exempts only `{anyOf, format}` from its sibling comparison
   (`architecture.py:2131-2135`). Both halves belong to CAR-3 so that the list stays the five items every other
   artifact in this package cites.
4. **CAR-4** — `_event_meaning` (merged main `architecture.py:3037`) still descends only `("oneOf","allOf")`, so
   descriptions reachable only through `anyOf` never enter event-meaning comparison; measured latent (no `event`
   contract currently reaches an `anyOf`), so it is a label/coverage gap, not a silent pass.
5. **CAR-5** *(soundness, latent — issue #147)* — declared-`$id` resolution takes precedence over the declared-path
   table (`architecture.py:1240-1247`, table built at `1170-1174`), so a path-like `$id` captures references naming
   another contract's path and a real narrowing of that target reports `compatible`. Unlike CAR-1..CAR-4 this is
   **not** fail-closed: it is a false certification, reachable the moment one contract declares a path-like `$id`,
   which nothing currently rejects. Measured unreachable today (41 declared `$id` values, none equal to a declared
   path, 0 of 86 `$ref` bases ambiguous — block E).

Distinct and already tracked elsewhere, therefore deliberately NOT re-filed here: annotation-vs-`compatible`
metadata behaviour (#120, PR #137) and the closure reverse-edge loss for `$id`/fragment refs (#146).

### Identifier namespace: `CAR-n` here vs `R-n` in `analysis-ai_architect.md`

This package carries two *different* five-item lists, both formerly numbered R1–R5, which made any cross-reference
ambiguous. The controller's list is renamed `CAR-1 … CAR-5` throughout this package's paperwork. The `ai_architect`
report keeps its own `R1 … R5` numbering **unrenamed** (agent evidence is not rewritten) — it is a list of
*rejection-branch mechanisms* located by line number, not this file's residual-work list. No other agent report uses
`R-n` as a list identifier: `grep -oE "\bR[1-5]\b" | wc -l` scores 0 on `analysis-repo_explorer.md`,
`analysis-architect.md`, `analysis-docs_researcher.md` and `analysis-integration_architect.md`, 17 on
`analysis-ai_architect.md`; every `R1 … R5` occurrence anywhere else in this package is this mapping section or a
note about the collision it resolves.

| this file (residual work item) | `analysis-ai_architect.md` (its rejection-branch list) |
|---|---|
| CAR-1 subsuming / object-valued / `$ref`-valued union branches unprovable | its R4 (branch shape outside `_SCALAR_PROOF_KEYS`); the subsuming case is its §3(a) "interval/enum proof incomplete" attribution, not an R-item |
| CAR-2 dropped `$ref` branch | its R4 (same mechanism, drop direction) |
| CAR-3 divergent annotation reasons, inside a branch and beside `anyOf` | its R1 (`$ref`+sibling → `unsupported_schema_keyword`), R2 (union-node siblings exempt only `{anyOf, format}`), R3 (annotation drift → `unknown`) |
| CAR-4 `_event_meaning` skips `anyOf` | — outside that list; measured in `analysis-architect.md` §5, re-listed as item 9 of `analysis-ai_architect.md`'s follow-up scope, site inventory in `analysis-repo_explorer.md` |
| CAR-5 `$id` precedence shadowing | — outside that list; found by the `architect` lane, filed as issue #147 |

## Gate-path corroboration

`scripts/grok_architecture.py fitness` probes (throwaway clones, `--pre-risk yellow`) reproduce the same shape:
`contract_compatibility` reports `unsupported compatibility semantics` for `LANDING-ATTEMPT-STATUS-V1`,
`LANDING-FAILOVER-OPENAPI-V1` and `LANDING-FAILOVER-RESULT-V1` on a title-in-branch probe, while capability-only
edits no longer produce `unsupported_openapi_construct` anywhere. Those gate runs are recorded in
`analysis-ai_architect.md` Table C, whose `00709f4`/`0284d33` identifiers are **probe commits in throwaway clones** and resolve as objects in no repository (verified with `git cat-file -t`); the in-process cells that drive them are
reproduced here by block C (title-in-branch row, all three contracts) and block A (analyzability of the same
contracts at head). The gate command itself is **not** re-run in `measurement-harness.md` — it needs throwaway
commits, so it stays attributed to the lane that executed it rather than promoted to a reproducible block.
