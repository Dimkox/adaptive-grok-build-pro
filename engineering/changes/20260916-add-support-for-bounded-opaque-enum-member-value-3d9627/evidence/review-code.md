PASS

# Code review — comparator fix for object-valued enum members (#104)

- Reviewed scope: `git diff fc8d9e6f11bb188ee514784d3b6f614a6da72803..3831e2e9ff269fd70a18676b6832576a28cb2689` in
  `/home/pall/grok-projects/adaptive-grok-build-c104` (branch `feature/comparator-opaque-enum-members`).
  Exactly 13 files: `.grok-stack/adaptive_grok/architecture.py` (+45), `tests/test_architecture_model.py` (+44),
  and the change package `engineering/changes/20260916-add-support-for-bounded-opaque-enum-member-value-3d9627/`.
- Verdict: **PASS** — the committed product code is correct, fail-closed and budget-sound; findings 1–2 are
  claim-accuracy and regression-strength defects that must be recorded (finding 1 needs an edit to the issue #104
  comment); finding 5 is an environmental warning about the current dirty worktree.
- Counts: Critical 0 · Important 2 · Minor 3.

## Findings

### Important

**I-1. Issue #104 comment overclaims: the failover OpenAPI is still `unsupported_openapi_construct`, and a capability-contract edit still hard-fails fitness end-to-end in this repo.**
`factory/contracts/openapi/landing-failover.v1.json` has two file refs; only the capability one was blind to object enums.
The second response schema, `$ref: ../jsonschema/landing-attempt-status.v1.schema.json`
(`paths./v2/landing-jobs/{job_id}/attempt.get.responses.200`), is rejected because that schema uses `anyOf`
(e.g. `properties.reason_code`, `properties.artifact`, `properties.provider_evidence_digest`, `properties.observation`)
plus a nested `$ref` chain — outside the closed subset both before AND after this diff (`_SUPPORTED_SCHEMA_KEYS` has no `anyOf`;
`_unsupported_schema` at `.grok-stack/adaptive_grok/architecture.py:1349` rejects unknown keys).
Measured (scratch clone `/tmp/review-c104/mut`, HEAD comparator, capability contract edited in a clone commit adding a
`qwen-omni-intl` member): `compare_contracts(failover_base, failover_head, "bidirectional", inventories=…)` →
`unsupported ('unsupported_openapi_construct',)`; full `scripts/grok_architecture.py fitness --base fc8d9e6… --head <edited>`
→ `contract_compatibility: unsupported`, findings
`["CONTRACT-FACTORY-LANDING-BACKEND-CAPABILITY-V1: widened_producer_output", "CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1: unsupported compatibility semantics"]`, `fitness_status: fail` (5.03 s).
Failure scenario: a #105-style PR that edits `landing-backend-capability.v1` (which `_contract_dependency_closure` pulls the
failover into scope for — `.grok-stack/adaptive_grok/architecture_fitness.py:841-903`) still hard-fails architecture exactly
as before the fix. The comment's sentence "`unsupported_schema_keyword` (the capability schema) and the inherited
`unsupported_openapi_construct` (the failover OpenAPI that `$ref`s it) are gone for any edit that is genuinely compatible or
genuinely incompatible" is false for the failover contract on this repo's actual documents; the brief's
"landing-backend-capability.v1 … and, through its $ref, the failover OpenAPI … permanently unmodifiable" fix framing inherits
the same overstatement. The typed spec itself survives: AC-004's exact claim (capability consumer-widening compatible,
producer-widening `widened_producer_output` under FIT-GOVERNANCE-HANDOFF-COMPATIBILITY) reproduced verbatim (see Verification).
Fix: amend the issue #104 comment (durable GitHub evidence) and the package text, and name the remaining comparator work —
`anyOf` in `landing-attempt-status.v1` (and its `$ref` closure) — as still blocking the failover; the #104 comparator part is
partially, not fully, closed.

**I-2. The adversarial arms of the characterization test never exercise `_valid_enum_member`'s rejection logic — an accept-anything mutation survives the entire suite.**
Every hostile member shape the test feeds is rejected one layer earlier, by the document preflight
(`_SchemaResolver.preflight_current` → `_bounded_json_document`, `architecture.py:1152-1163` / `1242-1284`, which already
enforces string keys, finite floats, encodable strings and depth ≤ MAX_DEPTH), so `_valid_enum_member`
(`architecture.py:1294-1329`) never gets to decide. Evidence:
- Mutated the function body to `return True  # accept-anything` in scratch copies — `test_object_valued_enum_members_are_bounded_opaque_values_not_schemas` **passes**, and all **178** tests
  (`tests.test_architecture_model`, `tests.test_architecture_fitness`, `tests.test_json_schema_subset`) **pass** unchanged.
- Reason-code probe of the test's arms: `non-finite`, `non-string key`, `over-deep` and the `mock.patch.object(ARCH, "MAX_PARSED_NODES", 8)`
  budget arm all return `unsupported('malformed_contract_document')` (preflight); only `duplicate member` reaches the enum loop
  (`unsupported('unsupported_schema_keyword')`) — and duplication is caught by the pre-existing canonical-bytes set, not by the
  new function. Via the public API, `_valid_enum_member` is behaviorally indistinguishable from `return True`: preflight guarantees
  a superset of its invariants for every document it can hand to it (`resolve()` at `architecture.py:1225-1228` preflights $ref
  targets on first use, so even the ref path cannot bypass it). The `counter is not None` branch
  (`architecture.py:1311-1317`) has **no production caller** — every `_unsupported_schema` call site passes a resolver.
Failure scenario: a future refactor drops or loosens preflight coverage (e.g. a new entry that validates resolved refs only
lazily, or registers non-preflighted inventory documents), and the "second line of defense" silently accepts hostile members —
no test notices; additionally the test's own comment "no adversarial member shape escapes the closed boundaries" attributes the
guarantee to the wrong layer, giving future readers false confidence that these arms pin `_valid_enum_member`.
Fix: add a direct unit probe of `_valid_enum_member` (and/or of `_unsupported_schema` with `resolver=None` + counter) on the
hostile shapes — that is the only way its depth/budget/reject branches get coverage — or state in the test that preflight is
the operative gate and the function is defense-in-depth.

### Minor

**M-1. New internal raise path for oversized integers (contained).** `math.isfinite(10**4000)` raises `OverflowError`
(`int too large to convert to float`), so `_valid_schema_scalar` raises inside `_valid_enum_member` for a huge-int member value;
the pattern pre-exists for `const`/scalar enums. Nothing escapes: the outer `compare_contracts` wrapper
(`architecture.py:2712-2727`) catches `OverflowError` → `unsupported('malformed_contract_document')`; a hostile-document probe
with `{"x": 10**4000}` member confirmed the returned verdict, no exception (JSON files legitimately admit arbitrary-precision
ints via `json.load`, so this is reachable from parsed contract content). Not exploitable via the fitness runner; noted because
`_valid_enum_member` is documented as "returns False" but does have a raising input class for callers outside the wrapper.

**M-2. Test-count claim off by one.** `tasks.md` ("Full architecture/contract suites green (177)") and the change-spec
`success_metric` say 177; measured at HEAD: `Ran 178 tests … OK` for the three named suites. The new test is the 178th and was
likely not counted. Docs-only nit.

**M-3. Conservative double-charge of enum members.** The enum loop consumes one budget node per member
(`architecture.py:1441-1445`) and `_valid_enum_member` immediately re-charges the member's root node
(`architecture.py:1307-1310`). Direction of error is safe (stricter bound), and preflight already charged ~2 nodes per dict
entry for the same subtree, so the new recursion can never out-run the budget the document passed preflight with; noted for
budget-arithmetic readers only.

## Verified (and how)

1. **Correctness of `_valid_enum_member` / no hostile escapes** — read `architecture.py:1242-1500, 2421-2794` end to end;
   probed 11 hostile in-memory enum members through the public `compare_contracts` (`tuple` member, int key, mixed int+str keys
   (the `json.dumps(sort_keys=True)` `TypeError` bait), `NaN`, `Infinity`, `10**4000`, lone surrogate `"\ud800"`, cyclic dict,
   depth-200 dict, `set`, bool key): **all** returned `unsupported`, zero exceptions escaped. The mixed-key `TypeError` cannot
   reach `_canonical_bytes`: `_bounded_json_document` requires `isinstance(key, str)` at every level before any enum analysis;
   and both `_canonical_bytes` call sites in the enum loop receive only `_valid_enum_member`-accepted values. The preflight
   wrapper's `except (…, UnicodeError, RecursionError, TypeError, ValueError, OverflowError)` is the belt-and-braces second
   layer, so even a direct `_unsupported_schema` misuse cannot crash the fitness runner via `compare_contracts`.
2. **Enum-loop rejection properties preserved** — empty-enum, non-list-enum and dup-by-canonical-bytes rows untouched
   (`architecture.py:1436-1453`); the diff only adds the `elif _valid_enum_member(...)` acceptance between the scalar check and
   the `encoded = None` rejection, so the scalar path is byte-identical; the dup arm measured
   `unsupported('unsupported_schema_keyword')`. The reject-all (`return False` = old behavior) mutation **fails** the test's
   first positive assertion (`compatible` expected, `unsupported` got) — acceptance is genuinely pinned.
3. **Budget consistency** — single `work_budget` list shared by both resolvers (`_compare_contracts_impl`,
   `architecture.py:2536-2560`) and by preflight/validation/comparison; exhaustion in `_valid_enum_member` returns `False`
   (→ unsupported), mirroring `_unsupported_schema`'s `True`; preflight charges strictly more per node than the new recursion,
   so no document passes preflight and then "blows" the new recursion in the other direction; existing tight-budget tests in
   `test_architecture_model.py` (≈3225-3265) pass. `mock.patch.object(ARCH, "MAX_PARSED_NODES", 8)` confirmed effective because
   `_valid_enum_member:1316` and `_SchemaResolver.consume:1150` read the module global at call time (arm then fails closed).
4. **Test suite** — pristine HEAD: `python3 -m unittest tests.test_architecture_model` → 68 OK; three suites → **178 OK**;
   `ruff check` on both changed Python files → All checks passed.
5. **Package vs diff** — `git diff --name-only`: no changes to `architecture/rules.yaml`, `architecture/system.yaml`, or any
   contract → INV-001 and FORBID-002 hold for the commit; `_compare_schema_direction`/`_comparison_canonical_values` untouched
   as `architecture.md` states. Package `route.json` matches `.grok-stack/runtime/active-route.json` in every substantive field
   (route_id `3d9627514c31`, base_commit `fc8d9e6…`, agents, evidence); it differs only in lifecycle fields
   (`status routed→implementing`, added `change_id`/`updated_at`) — expected drift of a routed-snapshot.
6. **#104 quoted verdict matrix** — reproduced against the real `landing-backend-capability.v1.schema.json` (8 members ×
   21-key objects under `properties.profile.enum`), adding a `qwen-omni-intl` fact in memory only:
   BASE comparator (`git archive fc8d9e6` module): every policy × every pair → `unsupported('unsupported_schema_keyword')`
   (premise confirmed); HEAD: `same` → compatible; widen → compatible under `consumer_accepts_old`, `incompatible
   ('widened_producer_output')` under `producer_accepted_by_old`, `incompatible ('narrowed_enum')` on narrowing;
   bidirectional widen → `widened_producer_output`. Matches the comment except the failover claim of I-1. The rules binding
   quoted in the comment matches `architecture/rules.yaml` `contract_policies` verbatim.
7. **Performance** — real-repo `python3 scripts/grok_architecture.py fitness --base fc8d9e6… --head 3831e2e… --pre-risk yellow`:
   **4.99 s** wall, `fitness_status: pass` (unchanged pair; contract_compatibility `not_applicable/contracts_unchanged`).
   Edited-contract pair in the /tmp clone: **5.03 s** — per-node `consume()` on the now-analyzable 8→9-fact enum adds nothing
   measurable; per-triple `compare_contracts` on the real document ≈ 8–10 ms. No pathological blowup.

## Limits / environment

- Review is read-only against commit `3831e2e`; all timing comparisons used explicit SHAs or `/tmp` clones (`0700`), never the
  repo. Repo writes: only this report; gitignored `__pycache__` entries may have been refreshed by test runs.
- **The live worktree is no longer clean**: `factory/contracts/jsonschema/landing-backend-capability.v1.schema.json` shows a
  133+/159− re-serialization (key-order rewrite, not content change) and
  `engineering/changes/…/evidence/review-test.md` appeared (14:22:37 UTC) from a concurrent test-review agent — neither is part
  of the reviewed commit, and the tree was clean at review start. **That contract rewrite must not be committed into this
  wave** (INV-001/FORBID-002); it must be ruled on by whoever produced it.
- Not verified: CI/Trust-CI behavior, receipts freshness, and the `grok_verify` gate (route forbids a reviewer from writing
  receipts); the "177" suites run happened under this review, but the full `grok_verify --mode pr` is the implementer's step.
- Findings I-1/I-2 do not invalidate the commit's product code; I-1 requires an edit to the issue #104 comment text (and,
  for the wave's stated outcome, a named follow-up for the `anyOf` blind spot), I-2 an added direct unit probe or corrected
  test commentary.
