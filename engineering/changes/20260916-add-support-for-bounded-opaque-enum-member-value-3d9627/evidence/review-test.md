FAIL
PASS-with-fixes is not an allowed verdict; the blocking defects are listed under Required remediation. Core-fix behavior IS guarded; the new guard's own boundary logic is not.

# Test review — comparator opaque enum members (issue #104 wave)

Scope: `git diff fc8d9e6f11bb188ee514784d3b6f614a6da72803..3831e2e9ff269fd70a18676b6832576a28cb2689` in
`/home/pall/grok-projects/adaptive-grok-build-c104` (branch `feature/comparator-opaque-enum-members`):
new test `test_object_valued_enum_members_are_bounded_opaque_values_not_schemas` in
`tests/test_architecture_model.py`, `_valid_enum_member` + enum-loop change in
`.grok-stack/adaptive_grok/architecture.py`, and the package `test-plan.md`.
Method: read-only in the real repo; all mutations in a scratch clone
`/tmp/c104-testreview.BjF7xs/repo` (mode 0700, detached at 3831e2e, byte-identical tree).
The real repo was never mutated; every mutant file was reverted by full-file rewrite from `ORIG`.

## 1. Mutation battery — matrix

| # | Mutant (in scratch clone) | Test outcome | Killed? |
| --- | --- | --- | --- |
| a | `_valid_enum_member` body → unconditional `return True` | **OK — all arms still pass** | SURVIVED |
| b | drop `isinstance(key, str)` in the dict branch | OK | SURVIVED |
| c | drop `if depth > MAX_DEPTH: return False` (helper only) | OK | SURVIVED |
| d | drop resolver `consume()` + counter increment/budget check (keep `None` guards) | OK | SURVIVED |
| e | revert enum-loop branch to scalar-only (original bug) | FAIL `'unsupported' != 'compatible'` at the first compatible assert | **KILLED** |
| f | make duplicate legal in the enum loop (`if encoded is None:`) | FAIL `(member='duplicate member') 'compatible' != 'unsupported'` | **KILLED** |
| g | `_valid_enum_member` body → unconditional `return False` (control for accept side) | FAIL at first compatible assert | **KILLED** |
| h | no-op replace (harness sanity control) | OK | survived, as required |

4 of 5 requested mutants survive. Root cause, established empirically, not inferred:

Adversarial-arm reason probe (unmutated HEAD):

```
duplicate       status=unsupported  reasons=('unsupported_schema_keyword',)
non-finite      status=unsupported  reasons=('malformed_contract_document',)
non-string-key  status=unsupported  reasons=('malformed_contract_document',)
over-deep       status=unsupported  reasons=('malformed_contract_document',)
budget (MAX_PARSED_NODES=8) status=unsupported reasons=('malformed_contract_document',)
```

Only the duplicate arm ever reaches the enum loop; the other four arms are rejected by
`_bounded_json_document` preflight inside `compare_contracts` (`malformed_contract_document`,
architecture.py ~2561) before `_unsupported_schema`/`_valid_enum_member` run. Preflight checks the
same boundaries over the whole document (depth from doc root — strictly stronger than the helper's
member-relative depth — string keys, finite scalars, ≥ the same per-node budget charge), so no input
reachable through the public API can distinguish the helper's reject logic. The arms assert only
`status == "unsupported"`, never the reason tuple, so preflight-vs-helper is invisible to them.

Coverage confirms (full `tests.test_architecture_model` under `coverage`, `adaptive_grok/architecture.py`):
lines 1307/1309/1310/1318/1319/1324/1325/1329 HIT; every reject return MISS —
1308 (depth), 1311 (resolver budget), 1313–1317 (entire counter branch). No test anywhere causes
`_valid_enum_member` to return False.

## 2. Coverage gaps against the typed spec

- AC-001 "each node charged to the resolver/counter work budget": the **resolver branch** of
  `_valid_enum_member` executes only in its consume-success form (via the compatible and duplicate
  arms); its budget-exhausted `return False` (line 1311) is never exercised. It is reachable in
  principle (shared `work_budget` is charged again during traversal after preflight), but the only
  budget arm (patched `MAX_PARSED_NODES=8`) dies in preflight first — mutant d proves this. The
  **counter branch** (1313–1317) is exercised by nothing: every in-module call site propagates a
  non-None resolver, `compare_contracts` always supplies one, and the two direct
  `ARCH._unsupported_schema` test calls (model tests ~3232/3245) also pass a resolver. Counter-mode
  is dead for structural members in production and tests alike.
- The plan/AC-001 cites `tests/test_architecture_fitness.py` as evidence for the object-enum AC, but
  that file contains zero occurrences of `enum` — it evidences only INV-002 no-regression, never
  AC-001. `tests.test_architecture_model` is the sole enum-object evidence.
- No existing test passes a structural enum through the resolver path indirectly: the only
  object-enum documents in the whole suite are inside the new test (`"enum": [{...}]` occurs solely
  at test_architecture_model.py:2025–2026 plus the `dict(fact_*)` fixtures).
  `test_added_landing_contracts_have_supported_closed_semantics` loads the real
  `landing-backend-capability.v1` (object-enum document) but compares it as an **added** contract
  (`old is None → continue` in architecture_fitness.py ~872), so `compare_contracts` never runs on
  it — it passes identically at base fc8d9e6 (verified: base run 177 OK).
- FORBID-001 ("never resolve $ref inside a member / validate keywords"): guarded only indirectly —
  a subschema-interpretation mutant is killed because `profile_id`/`media_kinds` are not supported
  schema keywords (`_has_only_keys` would reject the fact dicts). No arm contains a `$ref`-shaped
  member (e.g. `{"$ref": "#/nope"}`, which as opaque data must stay accepted byte-exactly), so the
  $ref-inert half of FORBID-001 is unpinned.
- `counter is None → return False` (1314) and non-JSON Python values on the counter path (e.g. NaN
  member reaching `_canonical_bytes(allow_nan=False)` would raise `ValueError` instead of returning
  unsupported) have no test.

## 3. Duplicate-member arm

It genuinely reaches the dup check, not an earlier rejection: unmutated reason is
`unsupported_schema_keyword` (helper accepted both members, then `encoded in enum_values` fired),
and mutant f (dup check removed) flips that exact arm to `compatible` → killed with
`(member='duplicate member')` in the failure label. Both copies being canonical-equal is precisely
why it survives preflight and the per-item budget: this is the only adversarial arm that executes
`_valid_enum_member`'s accept path on structural members.

## 4. Hermeticity and style

- New test: pure in-memory data, `self.subTest`, no `os.environ`, no network, no filesystem, no
  subprocess; `mock.patch.object(ARCH, "MAX_PARSED_NODES", 8)` is a context manager, restored, and
  the module reads the global at call time so the patch is effective. Deterministic; passes in
  0.003s standalone; full model module green with it (68/68).
- Style deviation: `from unittest import mock` inside the method (line 2034) duplicates the
  file-level `from unittest import mock` (line 15) used bare by all ~14 other `mock.patch` sites in
  the file. Redundant, inconsistent — cosmetic, not correctness.
- Runs (scratch clone at 3831e2e; identical tree content, so identical to the repo):
  all modules OK, no failures anywhere.

## 5. Exact counts & test-plan honesty

| Set | Ran | Result |
| --- | --- | --- |
| `tests.test_architecture_model` | 68 | OK |
| `tests.test_architecture_fitness` | 106 | OK |
| `tests.test_json_schema_subset` | 4 | OK |
| plan trio combined | **178** | OK |
| same trio at base fc8d9e6 | **177** | OK |
| `tests.test_landing_architecture_boundaries` (3rd ls-found arch module) | 4 | OK |
| model+fitness+landing-boundaries | 178 | OK |
| `tests.test_change_spec` | 30 | OK |

- Plan commands exist and are reproducible verbatim (unittest trio + `scripts/grok_verify.py` exists;
  grok_verify intentionally not executed here — it writes receipts and is the parent's step).
- The "177 architecture/contract tests" claim is stale-by-one against HEAD: it reproduces exactly at
  base, 178 on the branch (the new test is +1). Minor honesty defect in `test-plan.md` and the
  change-spec `success_metric`, both of which should say 178@head (or label 177 as base).
- P1 evidence "no regression" is true and re-verified green on this head.

## Required remediation (to flip this PASS)

1. Assert the reason tuples in the adversarial arms (`unsupported_schema_keyword` for duplicate;
   `malformed_contract_document` for the preflight-rejected four) so future preflight relaxation
   cannot silently convert an arm into a helper-level pass — and vice versa, so the arm's actual
   guard is pinned.
2. Add at least one discriminating test of the new code's reject paths, per the file's established
   direct-private-helper convention (`ARCH._bounded_json_document`, `ARCH._unsupported_schema` are
   already called directly): e.g. unit asserts on `ARCH._valid_enum_member` for `{1: "x"}` → False,
   over-relative-depth member → False, counter-budget exhaustion → False (with `resolver=None`),
   and/or a compare_contracts budget scenario chosen so preflight passes and member accounting trips
   line 1311. Without this, mutants a–d stay alive and AC-001's budget clause plus AC-003's
   member-boundary clause are unguarded.
3. Either add a `$ref`-in-member opaque-data arm (FORBID-001 pin) or delete nothing — one subTest.
4. Update `test-plan.md`/`change-spec.yaml` counts to 178-on-head, and stop citing
   `tests.test_architecture_fitness` as AC-001 evidence (0 enum content there); it is INV-002
   evidence only. Drop the redundant in-method `mock` import.

## Limits / notes

- Review pinned to 3831e2e as instructed. During the review the worktree moved: HEAD is now
  a490428 ("scratch: edit capability contract") plus an uncommitted modification to
  `factory/contracts/jsonschema/landing-backend-capability.v1.schema.json`. Neither touches
  `architecture.py` or tests, so all findings above remain valid for the reviewed diff — but that
  commit + dirty file edit the exact contract the wave's INV-001/FORBID-002 forbid touching; flagged
  to the parent as a possible out-of-wave collision needing ruling, not adjudicated here.
- Counts are unittest `Ran N`; passing subTests are counted within their parent method (1 method = 1
  test), identical convention for the base-177 and head-178 numbers.
- Statement coverage cannot see branch outcomes; that limitation is closed here by the mutation
  battery itself (a–d survivors are the branch-level proof).
- Only reachable public entry analyzed: `compare_contracts`. The counter-mode `_unsupported_schema`
  entry has zero production callers today; if it is intentionally kept, it needs its own tests (rem.
  #2), otherwise it is untested dead weight the plan claims coverage for.
