# Complete the technical #104 comparator fix — Implementation Plan

**Goal:** Analyze the current landing OpenAPI dependency closure with sound directional `anyOf` proofs, bounded `$defs` references, and conservative `date-time` metadata comparison.

**Architecture:** Extend the existing `_SchemaResolver` and schema comparator in `.grok-stack/adaptive_grok/architecture.py`. Keep resolution inventory-bound and keep compatibility three-valued: proven inclusion is compatible, a proven directional violation is incompatible, and unproven cases are unsupported.

**Tech Stack:** Python 3.11+, `unittest`, existing JSON Schema contract model.

**Spec:** `engineering/changes/20260918-fix-the-remaining-104-fitness-comparator-blind-s-4c524b/architecture.md` and `requirements.md`.

## Global Constraints

- Keep `MAX_DEPTH=64`, `MAX_PARSED_NODES=100000`, and the existing contract inventory boundary.
- Allow at most 16 branches in an `anyOf` and at most 256 candidate pair checks, charged to the shared work budget.
- Do not fetch references over a network or resolve files outside the declared inventory.
- Keep cycles, malformed pointers, ambiguous targets, unknown formats, and unprovable language inclusion unsupported.
- Do not change producer-output rules, deployed Trust CI, contract declarations, or profile facts.

---

### Task 1: Characterize the current failing dependency closure

**Files:**
- Modify: `tests/test_architecture_model.py` inside `ArchitectureModelTests`.
- Test: existing helpers `_record`, `ROOT`, and the architecture contract inventory loader.

- [ ] **Step 1: Add the failing regression test**

```python
def test_openapi_dependency_closure_accepts_existing_nullable_schemas(self):
    snapshot = ARCH.load_architecture(ROOT)
    records = ARCH.contract_inventory(ROOT, snapshot)
    failover = next(r for r in records if r.id == "CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1")
    result = ARCH.compare_contracts(
        failover, failover, "bidirectional",
        base_inventory=records, head_inventory=records,
    )
    self.assertEqual(result.status, "compatible", result.reasons)
```

- [ ] **Step 2: Run it and confirm the expected red result**

Run: `python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_openapi_dependency_closure_accepts_existing_nullable_schemas -v`

Expected: FAIL because `_openapi_schemas` returns `None` after traversing the declared status/observation `$ref` closure.

### Task 2: Add directional union tests before implementation

**Files:**
- Modify: `tests/test_architecture_model.py`.

- [ ] **Step 1: Add tests for reordered/duplicate alternatives, nullable widening/narrowing, producer and consumer directions, and ambiguous split coverage.**

Test the same union helper through public `ARCH.compare_contracts`; require compatible only when every source branch has a proved containing destination branch. Require unsupported for branch coverage that would need combining multiple overlapping alternatives.

- [ ] **Step 2: Run only those tests and confirm failures are caused by missing `anyOf` semantics.**

Run: `python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_anyof_directional_union_inclusion_is_proven tests.test_architecture_model.ArchitectureModelTests.test_anyof_ambiguous_union_coverage_fails_closed -v`

Expected: FAIL with `unsupported_schema_keyword` or a wrong compatibility result, never a test import/setup error.

### Task 3: Characterize reference and format boundaries

**Files:**
- Modify: `tests/test_architecture_model.py`.

- [ ] **Step 1: Add tests for local `#/$defs/...` pointers, relative references with pointers to exact inventory records, and exact declared `$id` URI references.**
- [ ] **Step 2: Add malformed `~` escapes, dangling pointers, unknown IDs, URI network targets, traversal, ambiguous IDs, cycles, depth exhaustion, parsed-node exhaustion, and candidate-pair budget cases.**
- [ ] **Step 3: Add `date-time` unchanged/changed-format cases and assert unrelated `prefixItems` stays unsupported.**
- [ ] **Step 4: Run the focused tests and confirm each intended unsupported edge fails for the current missing feature.**

Run: `python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_schema_resolver_supports_bounded_json_pointers tests.test_architecture_model.ArchitectureModelTests.test_schema_resolver_and_anyof_limits_fail_closed tests.test_architecture_model.ArchitectureModelTests.test_date_time_format_is_compared_as_contract_metadata tests.test_architecture_model.ArchitectureModelTests.test_unrelated_schema_keywords_remain_unsupported -v`

### Task 4: Implement inventory-bound pointer resolution

**Files:**
- Modify: `.grok-stack/adaptive_grok/architecture.py`, `_SchemaResolver` only.
- Tests: the red resolver tests from Task 3.

- [ ] **Step 1: Parse references without network or filesystem fallback.** Split a supported base and fragment; accept current-document pointers, relative paths to exact inventory records, and exact declared `$id` values. Decode only valid RFC 6901 `~0` and `~1` escapes.
- [ ] **Step 2: Walk the already-parsed JSON value for pointer targets.** Require a dict schema result; retain OpenAPI component-pointer behavior as the same bounded mechanism.
- [ ] **Step 3: Key cycle detection by `(record path, decoded pointer)` and charge reference parsing/walking to the shared work budget.**
- [ ] **Step 4: Run the resolver tests and then the existing multihop/dangling/cycle/budget tests.**

Expected: all valid closure references resolve; all adversarial references remain unsupported.

### Task 5: Implement schema closure validation and `date-time`

**Files:**
- Modify: `.grok-stack/adaptive_grok/architecture.py`, `_SUPPORTED_SCHEMA_KEYS` and `_unsupported_schema`.
- Tests: the red closure and format tests from Tasks 1 and 3.

- [ ] **Step 1: Add `$defs` as a bounded object map and validate every key/value recursively under existing depth and node limits.**
- [ ] **Step 2: Accept only `format: "date-time"` on string schemas; reject unknown format values.**
- [ ] **Step 3: Compare format annotations explicitly; an edit adds `changed_constraint` and never passes as compatible. Do not parse instance strings.**
- [ ] **Step 4: Run the actual dependency-closure self-comparison and metadata-only capability-edit reproduction.**

Expected: the failover OpenAPI no longer reports `unsupported_openapi_construct`; `prefixItems` remains unsupported.

### Task 6: Implement sound directional `anyOf` inclusion

**Files:**
- Modify: `.grok-stack/adaptive_grok/architecture.py`, preflight and `_compare_schema_direction` helpers.
- Tests: the red union tests from Task 2.

- [ ] **Step 1: Normalize `anyOf` alternatives as an order-independent set of canonical branches and deduplicate equivalent branches.**
- [ ] **Step 2: For consumer comparison prove `L(base) ⊆ L(head)`; for producer comparison prove `L(head) ⊆ L(base)`.**
- [ ] **Step 3: Prove coverage only when each source branch is contained by a destination branch using a tri-state branch relation. Distinguish `not included` only for supported, proven counterexamples; otherwise return unknown.**
- [ ] **Step 4: Return compatible only for a full proof; return incompatible only for a proven violation; return unsupported for ambiguous or unsupported branch relations. Charge every branch-pair check to the shared budget and cap each comparison at 16×16 pairs.**
- [ ] **Step 5: Run all union tests and existing composition tests.**

### Task 7: Verify end-to-end fitness behavior

**Files:**
- No further production file changes unless a test exposes a defect.
- Verify: `tests/test_architecture_model.py` and the architecture CLI.

- [ ] **Step 1: Run `python3 -m unittest tests.test_architecture_model -v`.**
- [ ] **Step 2: Run the capability metadata-only mutation with `python3 scripts/grok_architecture.py fitness --base 2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217 --worktree --json`; confirm failover OpenAPI is no longer unsupported.**
- [ ] **Step 3: Run the added profile enum mutation in-memory/temporary only; confirm the existing producer-output rule still reports `widened_producer_output`. Do not persist that probe.**
- [ ] **Step 4: Run `git diff --check`, then the single final `python3 scripts/grok_verify.py --mode pr`.**

### Task 8: Independent route closure

**Files:**
- Persist independent reviewer reports under this change package after all reviews.
- Runtime evidence: selected verification/code/test/security receipts.

- [ ] **Step 1: Dispatch route-selected code, test, and security reviewers after the final verifier passes.**
- [ ] **Step 2: Store reports and record exact-kind receipts for the same final tree.**
- [ ] **Step 3: Run `python3 scripts/grok_status.py --json`; require zero evidence gaps.**

The separate product choice for adding facts to v1 remains open until its producer-policy decision is recorded; this code change does not silently choose one.
