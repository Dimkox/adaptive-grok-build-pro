# Audit of PR #133 (soundness-first)

Module audited: `architecture.py` at `d871ea6` (merged main; byte-identical to PR #133 head `2cbfa12`,
md5 `ae860ed8…`), loaded as a second namespace in the same process as the pre-merge module `2f66ba6`
("base"). Tree data = `<audit-worktree>` at `2f66ba6`; `#133` left
`factory/contracts/` and `architecture/` byte-identical (`git diff --stat 2f66ba6 d871ea6` → empty), so both
modules see the same documents. Inventory for every measurement = the **declared 50-record** inventory
(`load_architecture` + `contract_inventory`, per-record declared kind/version/role/compatibility), substituted
only for the edited record, passed as both `base_inventory` and `head_inventory`. All rows are measured runs,
not reasoning. Harnesses: `<private-scratch>/{real.py,d2.py,d5.py,d6.py,d8.py,d9.py,c3.py}`.

## 1. One measured false `compatible` — from the new `$id` lookup, not from `anyOf`

Same pair under both modules; only `c/y.json` narrows (`minLength 1 → 9`); the referrer's own bytes are unchanged.
`c/other.json` claims `$id: "y.json"` — an `$id` equal to another record's *path*.

| module | `resolved_paths` | graph identity | verdict |
|---|---|---|---|
| base (2f66ba6) | `c/x.json`, **`c/y.json`** | differs | `incompatible: narrowed_constraint` |
| head (d871ea6) | `c/x.json`, **`c/other.json`** | same | **`compatible`** |

Reproduce:

```python
import sys; sys.path.insert(0, "<private-scratch>"); import real; ns = real.HEAD
mk = lambda p, d: ns["ContractRecord"](id=p, kind="json_schema", path=p, version="1", role="bidirectional",
    compatibility="bidirectional", digest=ns["_sha256"](d), document=d)
X  = {"type": "object", "properties": {"p": {"$ref": "y.json"}}}
Yb, Yh = {"type": "string", "minLength": 1}, {"type": "string", "minLength": 9}
Ob = {"$id": "y.json", "type": "string", "minLength": 1}
b, h = mk("c/x.json", X), mk("c/x.json", X)
print(ns["compare_contracts"](b, h, "bidirectional",
      base_inventory=[b, mk("c/y.json", Yb), mk("c/other.json", Ob)],
      head_inventory=[h, mk("c/y.json", Yh), mk("c/other.json", Ob)]))   # compatible, ()
```

Cause: `resolve()` consults `records_by_schema_id` **before** the path table
(`architecture.py:1240-1247`, table built at `1170-1174`); the winner is added to `resolved_paths` (`1300`) and the
path-named record is then covered by neither `resolved_paths` nor `graph_identity()` (`1306-1312`). Two records
claiming one `$id` do fail closed (`ambiguous declared schema id`, `1242-1243`; measured
`unsupported_schema_keyword`), and a non-inventory record is still unreachable (`1248-1252` + kind guard).
Worse, this converts a **fail-closed into a pass**: with `c/y.json` absent from the inventory, base raises
`undeclared schema reference` → `unsupported_schema_keyword`; head resolves through the `$id` claimant → `compatible`.
Not reproducible in the current tree (no `$id`/path collisions exist among the 50 declared contracts; the only
`$id`-style refs are the intended `…$id#/$defs/handoff` form used by `m7-*`/autonomy contracts).
Cheapest hardening: reject when `reference_base` matches both an `$id` and an inventory path, or add the
path-resolved record to `resolved_paths` as well.

No other unsound `compatible` surfaced in ~120 measured pairs (tables below).

## 2. Union edits on the real landing contracts (head, declared policies)

`attempt-status $properties/reason_code/$anyOf` = `[{string,minLength:1,maxLength:128},{null}]`.

| edit | bidirectional | consumer_accepts_old | producer_accepted_by_old | sound? |
|---|---|---|---|---|
| reorder branches | compatible | compatible | compatible | yes (order not meaningful) |
| add duplicate `{type:null}` | compatible | compatible | compatible | yes (instance set unchanged) |
| add subsumed `{string,minLength:5,maxLength:8}` | compatible | compatible | compatible | yes (absorbed) |
| collapse `anyOf[X]` → `X` | compatible | compatible | compatible | yes |
| **add new alt `{type:integer}`** | **incompatible: changed_constraint** | compatible | incompatible: changed_constraint | **yes — widening is NOT blessed** |
| add subsuming `{type:string}` (widens) | unsupported: unsupported_schema_comparison | compatible | unsupported: unsupported_schema_comparison | fail-closed |
| drop `{type:null}` (narrows) | incompatible: changed_constraint | incompatible: changed_constraint | compatible | yes |
| branch `minLength 1→5` (narrows) | unsupported: …_comparison | unsupported: …_comparison | compatible | fail-closed |
| title added inside branch | unsupported: …_comparison | – | – | fail-closed |
| `anyOf`↔`oneOf` swap, identical branches | unsupported: …_comparison | same | same | yes (never compatible) |
| nested `anyOf` widened inside `oneOf` | incompatible: changed_constraint | – | – | yes (outer path still visited) |
| `oneOf [A,A] → [A]` / reorder | incompatible: changed_constraint | – | – | yes (no dedup leak) |
| `$ref` alt kept, referenced doc narrowed | unsupported: …_comparison | – | – | fail-closed |
| `$ref` alt replaced by its own inlined content | compatible | – | – | yes (ref is transparent) |
| `enum[1] → enum[1.5]` inside branch | incompatible: changed_constraint | – | compatible | yes (∅ ⊆ base) |
| `const 1 → 1.0` inside branch | unsupported: …_comparison (branch also carries `type`) | – | – | fail-closed |

Fail-closed battery (all `unsupported`, no crash, never `compatible`): `anyOf: []`, 17 branches
(`unsupported_schema_keyword`, cap at `1601-1609`), non-dict branch, depth 99→100 and 5^7→5^8 node fan
(`malformed_contract_document`), `format:"email"`, `format` on a non-string, pointer to non-schema data
(`#/required/0`), `$ref` into an `openapi` record. Caps: `16×16` = exactly 256 pairs → `compatible`
(reorder, correct); nested 16-wide unions → `changed_constraint`; the `pair_attempts > 256` raise (`1925-1926`)
is per-`_union_inclusion` call and surfaced as `contract_comparison_work_limit`/`unsupported`, **not** as the
parent's `unsupported_schema_comparison`.

## 3. Answers

(a) `unsupported_schema_comparison` is a **bounded-subset decision with a reason**, added at
`architecture.py:2151` (`format_state == "unknown"`) and `2164-2165` (`relation == "unknown"`). The decisive
guard is `_branch_relation`: `1770-1773` (`not _has_only_keys(…, _SCALAR_PROOF_KEYS)` → unknown) plus
`1834-1839` (mixed-type interval refusal) and the closing comment "Only constraints explicitly modeled above
participate in a proof" (`1852`). Attribution over the real edits: `{destination has non-proof keys: $ref}`
(branches that are object/`$ref` shapes), `interval/enum proof incomplete` (the `{type:string}` subsuming alt,
`lower in destination and source_lower < destination_lower` at `1846-1847`), `annotation … differs` (`1778-1780`).
Deciding the novel-branch widening soundly needs a real subtype/absorption test for object branches
(`properties`/`required`/`additionalProperties`) and for `$ref`-valued branches — i.e. per-branch structural
inclusion, not the scalar-only proof. It is not silently giving up: fitness maps the row to
`"unsupported compatibility semantics"` and forces status `unsupported` (`architecture_fitness.py:885,889`),
so architecture stays red rather than green.

(b) Hard directions tried and **not** broken: nested `anyOf` inside `oneOf`/`allOf`/`if`/`then` (outer canonical
check at `2187` still fires); `$ref`-branch equality (`_branch_relation` resolves both sides at `1740-1749` and
`_resolve_comparison_schema` returns the *target record*, so `current` is re-threaded and nested refs keep their
own scope); the format-sibling exclusion at `2131-2132` is preceded by an unconditional node-level format
comparison at `2126`, and `_anyof_format_changed` can only return `"same"` when the inlined `full` **and** `shape`
are equal (`2066-2067`) or when both format counts are zero (`2072-2074`) — measured: format added in a branch,
moved between branches, nested in a sub-union with matching counts, and as an `anyOf` sibling all came out
`changed_constraint`/`…_comparison`, never `compatible`; int/float unification inside branches matched only
true JSON-number equality (`enum[1]→enum[1.0]` compatible, `enum[1]→enum[1.5]` not).
Referrer-row behaviour on the real graph: `landing-failover.v1.json` (own bytes unchanged) reports
`incompatible: widened_producer_output` for a capability enum widening and for a `required` drop, and
`unsupported: unsupported_schema_comparison` for any `anyOf` widening inside `attempt-status`; its `compatible`
for an `anyOf` *narrowing* is the same directional rule the pre-existing plain path already used — proven by the
control edit (drop a plain enum member, no `anyOf` involved): `compatible` at head, exactly like the union
narrowing, while `failover-result` (a `$ref`-child row) fail-closes with `…_comparison`.

(c) The oneOf/allOf asymmetry is **structurally pinned**: dedup happens only in `_union_inclusion.normalize`
(`1906-1913`), reachable solely from the `anyOf` blocks (`1752-1773`, `2152-2161`), and in `normalized()` only
under `if composition == "anyOf":` (`2014-2025`); the `else` at `2026-2028` keeps `oneOf`/`allOf` positional and
duplicate-preserving, and their raw canonical-bytes equality (`2187-2189`) and positional recursion
(`2276-2288`) are untouched by the diff. Measured: `oneOf [A,A]→[A]` `incompatible`, `oneOf` reorder
`incompatible`, `anyOf` both `compatible`.

## 4. Divergences you asked me to locate

The `title`-edit divergence is **not** the `_has_only_keys` size rule: the head whitelist is 27 keys and the
largest node in all 50 declared contracts has 9 keys (measured). It is the `$ref`-sibling rule
`if "$ref" in schema: if set(schema) - {"$ref", "$defs"} …` (`1431-1437`): in `landing-failover-result.v1` the
first union branch is `"$properties/attempts/items/$properties/receipt/$anyOf/0` = a bare `$ref`, so adding
`title` yields `{"$ref": …, "title": …}` → whole-document `_unsupported_schema = True` →
`unsupported_schema_keyword`. The sibling edits at `$properties/winner/$anyOf/0` (object) and
`$properties/reason/$anyOf/0` (string) validate fine (`False`) and die later in the union proof →
`unsupported_schema_comparison`. Same edit class, two different stages — defensible as per-document construct
support, but it means a *language-preserving* annotation edit inside a `$ref` branch is indistinguishable from
an out-of-subset document, and `unsupported_schema_comparison` is reported by a comparator that in fact compared
everything and *proved nothing* — the reason name should carry which proof was missing (branch shape vs. interval
vs. annotation) so the follow-up work is targetable.

## 5. Coverage result and residuals

Fleet sweep (identity pairs, declared 50-record inventory): **25 rows went `unsupported → compatible`, 0 rows
regressed**. Attribution of the base rejections is mostly `$defs` (root `$defs` in 19 contracts) and `format`
(`date-time` strings), only 3 rows were `anyOf` — so the `$defs`/`format` admission did most of the unlocking,
and `landing-attempt-status`'s `anyOf` is genuinely needed for the #104 outcome. Still unanalyzable:
`operator-handoff-proposal.v1` (`prefixItems`), `ready-for-pr-bundle.v1`, and the `securitySchemes` `scheme`
nodes in the OpenAPI fleet. Two structural residuals worth their own work items: `_event_meaning` still
traverses only `("oneOf","allOf")` (`3037`) — measured directly: for a document whose `anyOf` branch carries a
`description`, the collected pairs are only `('$','root')`, while the same description under `oneOf` and under a
`$defs`-resolved `$ref` **is** collected; no false `compatible` follows (the union proof fail-closes: measured
`unsupported_schema_comparison`), but the event-meaning ledger is now silently narrower than the subset it
claims to cover. And object-valued union branches remain undecided in both directions, so those contracts stay
partly write-once.
