# AI/contract audit — #104 composition subset: merged main d871ea6 (+ baseline @2f66ba6)

Method: every verdict is executed, not read. In-process runs use the **real declared inventory built by
`contract_inventory()` from `architecture/system.yaml` = 50 records** (exactly what the gate uses — larger
than the 38 `factory/contracts/**/*.json` files), passed as both inventories with only the edited record
substituted, shared work budget. Tree: clean detached worktree `<private-scratch>/wt-d87` at `d871ea6`
(`git diff --stat 2cbfa12 d871ea6` **empty** → the merged tree is PR #133's tree). Gate runs:
`python3 scripts/grok_architecture.py fitness --base d871ea6d5d6… --head <probe> --pre-risk yellow` in
`<private-scratch>/{newmain,wt-profile,wt-d87}`; harnesses `matrix2.py`, `e2e.py`, `battery.py`, `census.py`,
`residual.py`. No product file in any real worktree was modified.

## Table A — your baseline table, re-derived

| probe (full 50-record inventory, bidirectional unless noted) | your claim @d871ea6 | my measurement @d871ea6 |
|---|---|---|
| byte-equal / identity | `unsupported_schema_keyword` → compatible | **confirmed** (`SELF` compatible for all 5 landing schemas + OpenAPI) |
| anyOf branch reorder only | unsupported → compatible | **confirmed** (synthetic union reorder = compatible both modes) |
| title inside anyOf branch | unsupported → compatible (attempt-status) | **REFUTED.** `/properties/reason_code/anyOf/0` +`title` → `unsupported/unsupported_schema_comparison` both modes; and the gate agrees (Table C). Their `-> compatible` outcome exists only for `/properties/winner/anyOf/0`-style scalar branches under the **producer** mode of a *different* contract |
| title inside anyOf branch | `unsupported_schema_keyword` (failover-result) | **confirmed**, and located: it is `/properties/attempts/items/properties/receipt/anyOf/0`, whose branch 0 is a bare `{"$ref": …}` → `$ref`+sibling is barred (arch.py:1431-1437). Not a composition verdict at all |
| title inside anyOf branch | `unsupported_schema_comparison` (provider-observation) | **confirmed** (`/properties/usage_input_units/anyOf/0`) |
| drop one anyOf branch | unsupported_schema_comparison (attempt-status, failover-result) / incompatible changed_constraint (observation) | **partly refuted — it is pointer-dependent, not contract-dependent.** `reason_code`/`usage_*`/`http_status`/`reason` (scalar branches) → `incompatible/changed_constraint` (consumer) + `compatible` (producer). `artifact`/`observation`/`receipt`/`provider_evidence_digest` (`$ref`- or `pattern`-bearing branches) → `unsupported_schema_comparison`. Full grid in Table B |
| capability edited → failover OpenAPI row (own bytes unchanged) | `unsupported_openapi_construct` → compatible | **confirmed** for a metadata-only capability edit (`description`) and for SELF; for a *profile-fact* edit the row is `incompatible/widened_producer_output`, i.e. a real verdict, not silently compatible (Table C) |

Your conclusion stands and is the important one: **#104's headline symptom is fixed by the merge, the closure
is not fully analyzable, and one edit class diverges.** The divergence axis is the *shape of the union
branch* (scalar-proof tractable vs `$ref`/`pattern`/object), not the identity of the sibling contract.

## Table B — non-verdictable edits per contract at d871ea6 (every anyOf position, both policy modes)

`comp`/`incomp` = real verdict; **bold** = non-verdict. `C` = `consumer_accepts_old` (FIT-CONSUMER-CONTRACTS),
`P` = `producer_accepted_by_old` (FIT-GOVERNANCE-HANDOFF-COMPATIBILITY). capability and failover-config have
**zero** anyOf positions, and every probe on them returned a real verdict at base and head.

| contract | pointer | T1 title on union node (sibling of `anyOf`) | T2 title inside branch 0 | T3 drop branch 0 | T4 add branch | T5 tighten bound in branch 0 |
|---|---|---|---|---|---|---|
| attempt-status | `/properties/reason_code/anyOf` | C **uns/sc** P **uns/sc** | C **uns/sc** P **uns/sc** | incomp/changed_constraint · comp | comp · incomp/changed_constraint | C **uns/sc** · comp |
| attempt-status | `/properties/artifact/anyOf` (`$ref` branch) | C **uns/sc** P **uns/sc** | C **uns/keyword** P **uns/keyword** | C **uns/sc** · comp | comp · P **uns/sc** | n/a |
| attempt-status | `/properties/provider_evidence_digest/anyOf` (`pattern` branch) | C **uns/sc** P **uns/sc** | C **uns/sc** P **uns/sc** | C **uns/sc** · comp | comp · P **uns/sc** | n/a |
| attempt-status | `/properties/observation/anyOf` (`$ref` branch) | C **uns/sc** P **uns/sc** | C **uns/keyword** P **uns/keyword** | C **uns/sc** · incomp/changed_constraint | C **uns/sc** P **uns/sc** | n/a |
| provider-observation | `/properties/usage_input_units/anyOf` (+ identical `usage_output_units`, `http_status`) | C **uns/sc** P **uns/sc** | C **uns/sc** P **uns/sc** | incomp/changed_constraint · comp | comp · incomp/changed_constraint | C **uns/sc** · comp |
| failover-result | `/properties/attempts/items/properties/receipt/anyOf` (`$ref` branch) | C **uns/sc** P **uns/sc** | C **uns/keyword** P **uns/keyword** | C **uns/sc** · incomp/changed_constraint | C **uns/sc** P **uns/sc** | n/a |
| failover-result | `/properties/winner/anyOf` (`$ref` branch) | C **uns/sc** P **uns/sc** | C **uns/sc** P **uns/sc** | C **uns/sc** · comp | comp · P **uns/sc** | n/a |
| failover-result | `/properties/reason/anyOf` (scalar branch) | C **uns/sc** P **uns/sc** | C **uns/sc** P **uns/sc** | incomp/changed_constraint · comp | comp · incomp/changed_constraint | C **uns/sc** · comp |

Across the 3 anyOf-bearing landing schemas (of 14 declared `*LANDING*` contracts, of 50 declared total) the 10
union positions × 5 edit classes × 2 policy modes = **90 probed cells, 57 of which are still non-verdicts**;
`T1` (title/description as a sibling of `anyOf`) is a non-verdict at **every** union position in both
directions — the single widest residual.

## Table C — the real gate path (`scripts/grok_architecture.py fitness --pre-risk yellow`)

| probe (base=d871ea6) | `contract_compatibility` | findings verbatim |
|---|---|---|
| `00709f4` title inside `reason_code.anyOf[0]` | **`unsupported`** (`unsupported_contract_semantics`) | `CONTRACT-FACTORY-LANDING-ATTEMPT-STATUS-V1: unsupported compatibility semantics`; `CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1: unsupported compatibility semantics`; `CONTRACT-FACTORY-LANDING-FAILOVER-RESULT-V1: unsupported compatibility semantics` |
| `0284d33` capability `profile` enum 8→9 (+`qwen-omni-intl`) | **`fail`** (`applicable`) | `CONTRACT-FACTORY-LANDING-BACKEND-CAPABILITY-V1: widened_producer_output`; `CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1: widened_producer_output` |
| SELF no-op (`d871ea6`→`d871ea6`) | `not_applicable` (`contracts_unchanged`) | — |

Your 3-row list is **reproduced exactly**. Why the OpenAPI row fails although its own document compares
compatible: the row is pulled in as a *reverse dependent* by `_contract_dependency_closure`
(architecture_fitness.py:905-929, built from `_external_contract_reference_paths`), then in
`_compare_contracts_impl` the early compatible shortcut requires `canonical_graphs_match` = document equality
**AND** `base_resolver.graph_identity() == head_resolver.graph_identity()` (architecture.py:3138-3142). The
OpenAPI bytes match but its resolved `$ref` graph now hashes differently (the response `…/content/schema`
`$ref` resolves into the edited attempt-status), so the shortcut is skipped, `_compare_openapi` runs, and the
response content schemas are compared as producer output (architecture.py:2968-2977) by following the `$ref`
through `_resolve_comparison_schema` (2077-2094) into the union position that hits R1/R3 below. So yes: it is
the closure of the **changed referenced schema**, and it is the same reverse-dependency mechanism #104 was
about — now producing a correct *verdict* for the capability case (Table C row 2) and a correct *non-verdict*
only where the bounded proof genuinely stops.

## Rejection branches, exact conditions at d871ea6 (`.grok-stack/adaptive_grok/architecture.py`)

- **R1 `unsupported_schema_keyword`** — `_unsupported_schema`, lines 1431-1437: `if "$ref" in schema: if (set(schema) - {"$ref", "$defs"}) …: return True`. A `$ref` may carry no sibling annotation, so `title` inside a `$ref` branch (attempt-status `artifact`/`observation`, failover-result `receipt`) is rejected before any union logic runs. Whitelist itself: 1056, 1429-1430.
- **R2 `unsupported_schema_comparison`** — `_compare_schema_direction`, 2131-2135: `base_siblings`/`head_siblings` exclude **only** `{"anyOf","format"}`, so *any* differing key next to `anyOf` (title, description, `$defs`, `default`…) fails closed. This is R-wide by construction and explains the 100 % T1 failure rate. Note the asymmetry with `_branch_relation`, whose sibling set (1757) excludes only `anyOf` — `format` is treated inconsistently between the two levels.
- **R3** — `_branch_relation` 1750 (canonical-bytes equality is the only route to `included`) then 1778-1780: `metadata = ("$id","$schema","title","description")` / `if any(source.get(key) != destination.get(key) …): return "unknown"`. Annotation-only branch drift is therefore unprovable, and `_union_inclusion` (1888-1946, which also dedupes by `_canonical_bytes`, so annotations split branch sets) propagates `unknown` → 2164-2165 `unsupported_schema_comparison`.
- **R4** — `_branch_relation` 1770-1772 against `_SCALAR_PROOF_KEYS` (1697-1700: `type,const,enum,minimum,maximum,minLength,maxLength,format,$id,$schema,title,description`) plus 1782-1787/1851 (`pattern` present or differing → `unknown`). Object/array branches (`properties`, `items`, `required`, `additionalProperties`, `pattern`) are outside the proof vocabulary, so every `$ref`-to-object or `pattern` branch (T3/T4 cells) is a non-verdict.
- **R5** — 1846-1849: `if upper in destination and source_upper > destination_upper: return "unknown"` — a *narrowing* bound in a branch (`maxLength` 128→127, `maximum` 10000000→9999999) is a real `changed_constraint` break for a consumer but is reported as non-verdict in the consumer direction, while the producer direction correctly returns `compatible`.

## Q3 — honest end-state for issue #104

"CLOSED / COMPLETED" is **accurate for the symptom as stated in #104** (an edit to a contract in the landing
capability closure produced `unsupported` purely because `anyOf` was outside the subset) — measured: SELF and
metadata and profile-fact probes now yield verdicts on all 6 rows, 25 of 50 declared contracts moved from
un-analyzable to analyzable, and the capability-edit scenario now lands as an explicit
`widened_producer_output` finding rather than a non-verdict. It is **not** accurate as "the AI/failover
contract closure is fully analyzable". Recommended wording: *"#104 closed for the reported blocker; the
bounded `anyOf` subset is incomplete — see follow-up (composition-proof residuals R1-R5)."*

> **[SUPERSEDED — annotation added by the controller at `cbc65ac`+ (the correction sits on top of that commit); the
> agent's own sentences below are quoted unchanged and were not rewritten.]** The clause "my 13 synthetic union probes
> found **no** false `compatible` … so the residual is *incompleteness*, not *unsoundness*" is refuted by a
> measurement this package itself carries: `analysis-architect.md` §1 reports a real consumer-breaking narrowing
> (`minLength 1 → 9`) in an `$id`-captured target as `compatible ()` at `d871ea6`, where the pre-#133 module reports
> `incompatible (narrowed_constraint)`, with the control arm (remove the `$id` claimant → both trees report
> `incompatible`) showing the delta comes from #133's `$id` lookup and not from `anyOf`. That case is filed as
> **issue #147** and recorded as residual **CAR-5** in `controller-declared-inventory-table.md`, and its reachability
> census is reproduced by block E of `measurement-harness.md` (41 declared `$id` values, none equal to a declared
> path, 0 of 86 `$ref` bases ambiguous → latent, not live). The 13 synthetic probes stand on their own terms — none of
> them exercises resolution order, which is a different mechanism from union inclusion — but the package's conclusion
> is now "incompleteness **plus one latent false certification**", not "incompleteness only". One cross-reference in
> the annotated passage has also drifted: this package's `requirements.md` AC-005 is the path-scrub criterion, and the
> fail-closed disclosure the agent meant is now AC-002/AC-003.

Nothing in the package overclaims past that: `brief.md` Outcome says "producing directionally sound results for
supported `anyOf` unions instead of stopping at a false unsupported verdict", which Table B/C show is only
partly true; `requirements.md` AC-005 and `review-test.md` do disclose fail-closed residue, and my 13
synthetic union probes found **no** false `compatible` (reorder/duplicate = compatible; split coverage and
inside-branch tightening = `unsupported`), so the residual is *incompleteness*, not *unsoundness*.

Follow-up scope (each check runnable by an independent verifier on a clean worktree at the head SHA):

1. `git diff --stat <pr-head> <merged-main>` empty, and `contract_inventory()` size printed by the harness equals the count of `contracts:` entries in `architecture/system.yaml` (50 today) — no verdict may be reported from a smaller inventory.
2. R2: add `"title"` as a sibling of `anyOf` at `/properties/reason_code/anyOf` in `landing-attempt-status.v1`; `compare_contracts(base, head, "consumer_accepts_old", <full inventories>)` must return `compatible` (annotation is not instance semantics), and the same edit under `producer_accepted_by_old` must return `compatible`.
3. R3: same expectation for `title`/`description` added **inside** a branch (`/properties/reason_code/anyOf/0`) and for branch reordering with annotations present; the pair must never be `unsupported_*`.
4. R1: `{"$ref": "landing-site-artifact.v1.schema.json", "title": "x"}` as an `anyOf` branch must not yield `unsupported_schema_keyword`; assert `format: date-time` alone remains the only admitted non-`date-time`-free format exception (a `date-time → "date"` change must stay `unsupported_schema_keyword` — measured).
5. R4: add/drop a branch whose target is an object schema (`/properties/artifact/anyOf`, `/properties/observation/anyOf`, `receipt/anyOf`) must yield a verdict (`incompatible/changed_constraint` for consumer-side widening asymmetry, `compatible` where inclusion is provable), not `unsupported_schema_comparison`.
6. R5: `maxLength` 128→127 and `maximum` 10000000→9999999 inside `anyOf/0` must return `incompatible/changed_constraint` for `consumer_accepts_old` (a proper-subset narrowing is decidable) and `compatible` for `producer_accepted_by_old`.
7. Gate parity: for each probe above, `grok_architecture.py fitness --base <merged-main> --head <probe-commit> --pre-risk yellow` must report `contract_compatibility.status ∈ {pass, fail}` (never `unsupported`) with the finding list naming exactly the contracts in the reverse-dependency closure, and must not list a contract whose own document and resolved graph are unchanged.
8. Non-regression: re-run the 50-contract × 6-edit battery; assert 0 flips from `compatible`/`incompatible` to `unsupported` and 0 real→real flips versus the recorded d871ea6 baseline (my run: 0 governance flips, 252 unsupported→real unlocks).
9. `_event_meaning` (3037) still traverses only `("oneOf","allOf")`: add a guard test asserting no declared `event` contract's `$ref` closure contains `anyOf` (measured today: exactly one `event` contract, `CONTRACT-FACTORY-EXECUTION-EVENT`, closure = itself, anyOf = 0 → the gap is **latent**, not live), so the day an event gains an `anyOf` the test fails loudly instead of reporting a false `compatible`.
10. `CONTRACT-ADAPTIVE-DEMO-OPENAPI` (root `servers`), `CONTRACT-FACTORY-LANDING-OPENAPI-V1` (`$ref` response objects), `CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1` (`prefixItems`) and `CONTRACT-FACTORY-M7-READY-BUNDLE-V1` (urn-`$ref` cascade into `prefixItems`) must be listed as explicitly out of scope; 4/50 contracts remain un-analyzable at d871ea6 (was 29/50 at 2f66ba6).

## Q4 — profile addition at merged main, full 50-record inventory

Enum grows 8 → 9 (`openai, anthropic, openrouter, grok, qwen, qwen-intl, grok-vision, qwen-omni` → + `qwen-omni-intl`, cloned from the `qwen-omni` fact with `profile_id`/`provider_id`/`base_url`/`model_id` changed; a differently-shaped clone gives the identical result):

| policy | verdict |
|---|---|
| `bidirectional` (the field declared in `system.yaml`) | `incompatible / ('widened_producer_output',)` |
| `producer_accepted_by_old` (FIT-GOVERNANCE-HANDOFF-COMPATIBILITY) | `incompatible / ('widened_producer_output',)` |
| `consumer_accepts_old` (FIT-CONSUMER-CONTRACTS) | `compatible / ()` |
| edited document compared to itself | `compatible / ()` |
| failover OpenAPI row, own bytes unchanged | `incompatible / ('widened_producer_output',)` |
| real gate (`0284d33`) | `contract_compatibility: fail`, 2 findings (Table C) |

**Still a declared break — not silent, and no producer-output policy was needed.** So #86/`qwen-omni-intl`
**cannot** be declared into `landing-backend-capability.v1` without a governance decision: either a v2
capability document coexisting with v1 (the `versioned_break` route the 20260916 record already named), or an
explicit policy exemption for fact registries — which this task's constraints forbid touching. What #133
changed is that the blocker is now an *arguable finding* instead of an *un-analyzable gate failure*.

## Baseline @2f66ba6 (labelled; pre-merge, same 50-record method)

anyOf occurs in the own documents of exactly 3 declared contracts (all `json_schema`, `compatibility:
bidirectional`): `landing-attempt-status.v1` ×4 (`/properties/reason_code`, `/artifact`,
`/provider_evidence_digest`, `/observation`), `landing-failover-result.v1` ×3
(`/properties/attempts/items/properties/receipt`, `/winner`, `/reason`),
`landing-provider-observation.v1` ×3 (`/properties/usage_input_units`, `/usage_output_units`, `/http_status`).
Closure totals: attempt-status 7 anyOf/6 files, failover-result 10/7, observation 3/3, failover OpenAPI 7/8
(`landing-failover.v1.json` → `$ref` → attempt-status → landing-input / site-artifact /
provider-observation → provider-evidence.v1|.v2). SELF at base: capability + failover-config compatible, the
other four `unsupported_schema_keyword`/`unsupported_openapi_construct`; **29/50** declared contracts failed
SELF. Removing `anyOf` alone from the whole inventory unlocked **only** failover-result; the other three
needed `$defs` and `format` removed too (carriers: `landing-input`, `landing-site-artifact`,
`landing-provider-evidence.v1/v2`, `landing-attempt`, `landing-evaluation`). Head admits all three keys
(1056-1084) — 4/50 remain un-analyzable.

## Refutations of the framing I was given

1. **"`anyOf` is absent" was never the sufficient cause.** Attribution matrix above: with `anyOf` removed and `$defs`/`format` left in place, `attempt-status`, `observation` and the OpenAPI row are still `unsupported`. `oneOf`/`allOf`/`if`/`then` are already whitelisted at base (1054-1055) and stripping them changed no verdict, so the "composition half" was one of three missing keys. #133 shipping three keys is right; its title/brief say one.
2. **`landing-backend-capability.v1` itself was never blind.** It was `compatible` on SELF at 2f66ba6, so "contracts in the closure of the landing backend capability cannot be edited at all" is only true of the *reverse* dependents reached through `landing-failover.v1.json`, not of the capability document.
3. **`unsupported_openapi_construct` on the failover row was not "caused by the anyOf in attempt-status"** alone: it is the whole 8-file closure, and at base `$defs`+`format` in `landing-input`/`site-artifact`/`provider-evidence` were equally sufficient to trip it. Proof by variant: removing only the attempt-status anyOf leaves the row `unsupported`; removing only `$defs`+`format` also leaves it `unsupported`.
4. **Inventory size does change verdicts — and your correction is right in general, but it does not touch these numbers.** Reproduced: a `$ref`-bearing record compared against a 1-record inventory fails `_SchemaResolver.resolve` ("undeclared schema reference") → `unsupported_schema_keyword`, while the same pair is `compatible` under the full inventory. Every figure in this report used the full 50-record declared inventory, which is also what `grok_architecture.py fitness` uses, and Table C's gate runs match my in-process cells row for row (3 rows, same reasons) — so no residual here is an artifact of a small inventory.
5. **The divergence across sibling contracts is not contract identity.** Same edit class, opposite outcomes inside one file (attempt-status: `reason_code` → verdict, `artifact`/`observation` → non-verdict). The driver is branch shape vs the scalar-proof vocabulary (R1/R4) and the sibling exclusion set (R2).
6. **The 20260916 record's residual claims are now stale in the opposite direction** — `brief.md` "What this fix does NOT unlock" and `evidence/review-code.md` I-1 assert the failover OpenAPI row is `unsupported_openapi_construct` and that a capability edit hard-fails with "unsupported compatibility semantics". At d871ea6 that row is analyzable and the capability edit yields `widened_producer_output` on two rows. Both texts need the correction, and `mistakes.md` still has **no** #104 comparator entry (grep `104` → 0 hits); pr/133's only new entry is the 2026-09-18 verifier-contention mistake, which states the #104 package has **no passing verification receipt** — that bookkeeping still needs reconciling.
