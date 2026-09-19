# Integration / blast-radius analysis — route `4c524b`

Anchors: baseline worktree `<audit-worktree>` @ `2f66ba6`; PR #133 head read-only at
`<private-scratch>/pr133` @ `2cbfa12f8ab6ff6f1b84c53792a0a5a0bd36b38b`; diff `git diff 2f66ba6..pr/133`. Read-only audit;
no product file modified; scratch `<private-scratch>/arch.diff`.

## Findings first

1. **#133 is not open — it is already MERGED.** `gh pr view 133` → `"state":"MERGED"`, `headRefOid 2cbfa12f8…`,
   `baseRefOid 2f66ba6…`; `origin/main` = `d871ea6` "fix(architecture): compare referenced schema enum values
   semantically (#133)"; issue #104 `state CLOSED closedAt 2026-09-19T03:58:36Z`. This audit is post-merge.
2. **No pinned digest moves** (§Q2) — verified by execution, not inference. The green external check on `2cbfa12`
   still describes the merged tree.
3. **Residual blind spot that moves rather than closes:** the comparator now accepts `<file>#/<pointer>` and declared-`$id`
   refs, but the fitness reverse-dependency closure cannot see them. `architecture_fitness.py:939`
   `_external_contract_reference_paths` understands only a plain relative path. Measured at pr/133:
   `"../jsonschema/cap.v1.schema.json#/$defs/ident"` → `'factory/contracts/jsonschema/cap.v1.schema.json#/$defs/ident'`
   and `"urn:adaptive-factory:landing-backend-capability:v1"` →
   `'factory/contracts/openapi/urn:adaptive-factory:landing-backend-capability:v1'`. Neither matches a declared contract
   path, so `by_path.get(...)` in `_contract_dependency_closure` (`:916-927`) drops the edge — editing the referenced
   target no longer re-checks the referrer. All three keywords *are* otherwise consumed (§Q5), and no declared contract
   uses these forms today, so it is newly-authorable rather than currently-triggered.
4. **`factory-postgres-exit` has no causal path from this diff; it is environmental and #128/#143 is its tracked home** (§Q3-followup).
5. **"Closes #104" holds for #104's own defect and the capability-graph symptom; the package records its own residuals** (§Q5).

## Q1 — one `unsupported` verdict → failed run (baseline; unchanged by #133)
`architecture_fitness.py:841 _contract_compatibility` sets `status="unsupported"` at `:888-889` after appending
`f"{identity}: unsupported compatibility semantics"` (`:884-885`). Rule IDs are the declared `FIT-*` policy IDs
(`used_rules`, `:866`) — `rules.yaml:132 FIT-OPENAPI-BIDIRECTIONAL`, `:141 FIT-CONSUMER-CONTRACTS`,
`:149 FIT-GOVERNANCE-HANDOFF-COMPATIBILITY`, `:157 FIT-SIGNED-PAYLOAD-EXACT`; the `CONTRACT-…` text is the finding
prefix (contract identity). Aggregation, `architecture_fitness.py:2452`:
`overall = "fail" if any(item.status in {"fail", "unsupported"} for item in results) else "pass"`.
`scripts/grok_architecture.py fitness` → `:123 return 0 if report.status == "pass" else 1` (preflight only).
`grok_verify --mode pr` runs the check unconditionally (`verification.py:1083`), summarising at `:181`
`f"drift={drift_status}; fitness={fitness.status}; diagrams={diagram_status}"` with detail
`code "architecture-fitness"`, `message f"architecture fitness status is {fitness.status}"` (`:168-176`);
`scripts/grok_verify.py:26-28` prints `FAIL architecture: drift=pass; fitness=unsupported; diagrams=pass` /
`ERROR architecture/rules.yaml: architecture fitness status is unsupported`, then `RESULT: FAIL` and exit 1
(`grok_verify.py:29-30`). Cascade: `verification.py:225-228` raises "governance requires a complete successful
architecture check" → **two** checks fail per unsupported contract.

## Q2 — digest / freeze exposure
* `architecture.py:2702 architecture_digests()` hashes documents only; `contract_inventory_digest` (`:658-671`) hashes
  identity fields + `_sha256(document)`. The keyword subset is not digest input, so no code edit can move it.
* `tests/fixtures/frozen-m2-635c9dd/manifest.json` pins per-file `sha256`+`git_blob_id` for 9 documents and
  `summary_digests`: `architecture_digest 5ab48dfa…`, `system_digest da6453d9…`, `rules_digest b47a0ed9…`,
  `schema_digest c702531d…`, `contract_inventory_digest 039feea9…`, asserted by `tests/test_structure.py:102-175`,
  which recomputes them **live** through `scripts/grok_architecture.py summary` (`:157-166`). Executed at pr/133:
  `python3 -m unittest tests.test_structure -v` → `Ran 19 tests … OK`.
* `_REVIEWED_GOVERNANCE_HANDOFF_SCHEMA_DIGEST = f3cd9126…fd71f` (`architecture.py:1069-1071`, also pinned
  `governance.py:48`); `schemas/governance-handoff-v1.schema.json` is untouched by #133 and its `_sha256` still equals
  the pin (measured) → value unchanged. But **#133 makes the hatch dead**: at pr/133 `CONTRACT-GOVERNANCE-HANDOFF-V1`
  is in-subset, so `architecture.py:2578-2594` is never reached for that pair.
* `engineering/reviews/`, `governance/`, `architecture/`, `trust-ci/config` contain no reference to
  `architecture_digest`/`schema_digest`/`rules_digest`/`contract_inventory_digest` (grepped).
* New reason `unsupported_schema_comparison` (end of `_compare_contracts_impl`) is not enumerated by any contract,
  schema, rules, governance registry or trust-ci artifact (grepped `*.json|*.yaml|schemas|governance|architecture|trust-ci`)
  → no contract bump. It does alter `fitness_results` → `architecture_evidence_digest`/`fitness_evidence_digest`, so all
  pre-merge local receipts are stale by the fingerprint rule.

## Q3 — risk tier, profiles, node scope
`--pre-risk` exists only on `scripts/grok_architecture.py:49`; under `grok_verify` pre-risk is the route level
(`verification.py:68-72`). Triggers (`architecture_fitness.py:2170-2212`) are graph events: contract *add* →
`new_contract` (`:2181-2182`) → scope `contract` (`:2449`); a comparator-only edit fires nothing because `:2177` skips
non-`node`/`runtime` kinds. `new_network_client` (`:2252-2271`) diffs import families over changed Python files — a
keyword/`resolve()` edit adds none. Profiles (`router.py:394-402`: `api`/`event`→`contracts`, `ai`→`ai`) gate only
php/bitrix/frontend in `verification.py:1104-1110`; `_python` (`:918`), `_contracts` (`:699`) and the architecture check
run identically for base, contracts and ai. Node scope does not move: `system.yaml:1798-1816
NODE-LOCAL-ROUTE-POLICY` already declares `.grok-stack/adaptive_grok` (TD-LOCAL-PREFLIGHT, `network: none`). Budgets
already own it: `rules.yaml:44-57 FIT-BOUNDED-ARCHITECTURE-CHANGE` (≤5000 AST / ≤10820 lines), `:60-73
FIT-BOUNDED-ALL-GOVERNED-CHANGE` (≤24000) — #133's comparator delta is +576/−36. `FIT-LOCAL-CANNOT-DEFINE-TRUST-CI`
(`rules.yaml:301-312`) is not implicated.

## Q4 — merge authority
AGENTS.md ("Independent merge trust", "PR-only delivery"): the only merge gate is the App-owned policy-epoch Check Run
on the exact head SHA; local `grok_verify`/reviews are preflight and "never replace the external check"; "A local
receipt is stale after any repository change." Pin measured three ways — `gh api …/branches/main/protection/required_status_checks`
→ `{"checks":[{"context":"adaptive-trust-ci/verified@06ecf1c875bc"}],"strict":true}`; `tests/test_project_state.py:14
CURRENT_CHECK = "adaptive-trust-ci/verified@06ecf1c875bc"`, `:15 CURRENT_APP_ID = 4694114`; construction at
`trust-ci/src/adaptive_trust_ci/policy.py:275-277` `f'{self.status_context}@{self.digest[:12]}'`. The deployed service
runs **the repository's own commands, hence its own copy of this comparator**, from the head checkout:
`trust-ci/config/policy.example.json:60-79 root-unittest` (`unittest discover -s tests`) and `:101-112
repository-verification` (`python3 scripts/grok_verify.py --mode pr --no-record --json`), both `required: true`.
Images are digest-pinned and operator-supplied (`trust-ci/compose.yaml:21,90,97` `${TRUST_CI_*_IMAGE:?set immutable
… name@sha256 digest}`); the repo holds no deployed policy digest — `policy.example.json:14` keeps an `aaaa…`
placeholder, consistent with AGENTS.md. Nothing under `trust-ci/runtime/` was read.

## Q5 / #133 audit — keywords consumed, tests moved
Baseline: no test rejected `anyOf` (`grep -rni anyof tests/` → empty); the three `unsupported_schema_keyword` sites
assert other keywords (`tests/test_architecture_model.py:2422 dependentRequired`, `:2030` duplicate enum member,
`:1881` handoff pair), so `anyOf` alone broke nothing — and measured alone it flips only **1 of 50** declared contracts
to in-subset (`landing-attempt-status.v1` stayed `unsupported_schema_keyword`, offending set `{('$defs',)}`; the
failover OpenAPI stayed `unsupported_openapi_construct`). #133's wider scope is therefore the right shape.
In #133 every keyword is consumed: `anyOf` traversed in `_unsupported_schema` (`for key in ("anyOf","oneOf","allOf")`)
and compared by the new anyOf branch of `_compare_schema_direction` (`_union_inclusion`, `_anyof_format_changed`);
`$defs` traversed (`definitions.values()` recursion, plus the relaxed `$ref` sibling rule
`set(schema) - {"$ref","$defs"}`) and reachable by pointer; `format` restricted to `"date-time"` on a string type
(other formats still fail closed) and compared via
`if base.get("format") != head.get("format"): reasons.add("changed_constraint")`. Pointer resolution is real
(`~0`/`~1` decode, `%` rejected, per-step budget, object-only target).
One proof gap, rescued by its caller: `_branch_relation` admits `format` in `_SCALAR_PROOF_KEYS` but never compares it,
returning `"included"` for `{"type":"string"}` → `{"type":"string","format":"date-time"}`; the enclosing
`_anyof_format_changed` format-count check converts that to `changed_constraint`, so no compatible verdict escapes.
`_schema_value_key` *widens* equality (`const:1` ≡ `1.0`, `enum:[1]` ≡ `[1.0]`) and *narrows* acceptance:
`enum:[1,1.0]` is now a duplicate → `unsupported_schema_keyword` (no declared contract has one).
> [ANNOTATION added by the controller] The baseline figure in this sentence is wrong: block A of
> `measurement-harness.md` measures **21/50** analyzable at the pre-#133 tree, not 20/50. The head half (46/50) and
> the four names listed below it are correct. The lane's own text is left byte-unchanged as issued.

Net unlock at pr/133: **46/50 declared contracts fully in-subset (baseline 20/50)**; still blocked
`CONTRACT-ADAPTIVE-DEMO-OPENAPI`, `CONTRACT-FACTORY-LANDING-OPENAPI-V1`, `CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1`,
`CONTRACT-FACTORY-M7-READY-BUNDLE-V1`.
Exactly one existing expectation was inverted:
`test_governance_handoff_exception_rejects_changed_supported_copies` →
`test_governance_handoff_changed_supported_copies_are_compared` (`unsupported/unsupported_schema_keyword` →
`incompatible`); it and `..._closed_schema_is_supported_in_self_comparison` pass at head
(`python3 -m unittest tests.test_architecture_model -k governance -k handoff -k digest` → `Ran 4 tests … OK`).
`tests/test_architecture_model.py:2223` still asserts `unsupported_openapi_construct`, and the new
`test_unrelated_schema_keywords_remain_unsupported` keeps other keywords closed.

## The failed local run (`factory-postgres-exit`)
`engineering/changes/20260918-…-4c524b/evidence/verification-attempt.md`: one full `grok_verify --mode pr`, 23 files,
profiles `base,contracts,ai`; all checks passed except `factory-postgres-exit` — 767 factory tests in 364.178 s,
2 skipped, 1 error — `PostgresFactoryTests.test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated`
(`factory/tests/test_postgres_integration.py:5603`) hit `QueryCanceled … statement timeout` in
`_validate_capability_session` during `lowered_budget_child` setup; a sibling worktree ran Ruff/spec/diff concurrently,
violating the issue-#40 timing-isolation rule. **No causal path:** the diff touches only
`architecture.py`, `tests/test_architecture_model.py`, `mistakes.md` and the package (`git diff --name-status`,
25 files) — no `factory/**`, no `architecture/*`, no contract; and `_validate_capability_session`
(`factory/src/adaptive_factory/store.py:117-122`) is a `pg_roles`/`pg_auth_members` catalog read on a connection with
`SET statement_timeout='5s'` (`store.py:253`, `:315`, `:770`) — a wall-clock ceiling on a shared server. Tracked home:
**issue #128** (OPEN) — `run_disposable_exit.py`, "the check the PR gate reports as `factory-postgres-exit`", leaks one
live disposable PostgreSQL container + volume per cancelled run (measured `docker ps`: three "Up 3 days"), i.e.
orphaned servers contending for host CPU/connections, which is what cancels a catalog read at 5 s. **PR #143** (OPEN,
base `2f66ba6`, head `d48aa5d3…`, branch `fix/issue-128-disposable-cleanup`) "Closes #128". Caveat: the package states
"No full rerun is planned for this package", so the failure remains recorded "as a failed verification result, not a
passing receipt" — never refuted on `2cbfa12` by a clean isolated re-run.

## Does #133 close #104?
Yes for #104's stated defect (object-valued enum members freezing fact-identity contracts) and for the symptom this
package named (capability-contract edit → `unsupported_openapi_construct` through the failover OpenAPI). Named
> [ANNOTATION added by the controller] "the package" here and below means route `4c524b83df59`'s change package
> (`engineering/changes/20260918-…-4c524b/`), whose `review-test.md` / `review-security.md` /
> `verification-attempt.md` are quoted; this audit package holds its own reviewer reports under the same names.

residuals, quoted from the package: review-test.md — "One non-blocking precision gap remains in the concurrent nested
`date-time` plus length-constraint case: the test accepts either `incompatible` or `unsupported` for both directions…
could be tightened to protect its classification."; review-security.md — "The private pointer resolver uses
`str.isdigit()` before `int()`… raises `ValueError`. The public `compare_contracts` boundary catches `ValueError` and
returns `unsupported`… I found no security bypass or fail-open compatibility path from it.";
verification-attempt.md — the failed `factory-postgres-exit`. Not recorded by the package (this analysis): the
fragment/`$id` closure gap (Finding 3), the now-dead reviewed-handoff escape hatch (Q2), the 4 contracts still outside
the subset, and `release.md`/`rollback.md` being empty section headers whose only stated recovery path is `brief.md`
Constraints, "source-only analyzer change with revert rollback".
