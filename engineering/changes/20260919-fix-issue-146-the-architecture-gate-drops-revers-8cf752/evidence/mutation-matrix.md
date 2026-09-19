# Mutation matrix for the #146 closure (measured, re-derivable)

Written because the review of `7d21d95` found the M0–M8 matrix existed only in chat (`review-test.md`
Important 6). Every number below was produced by running the stated command in a private copy of the tree;
nothing is inherited from an earlier run unless the row says so.

**Concurrent-author notice (times are UTC on the delivery host).** The implementer's own edits were complete
and green at 06:32–06:36 (`Ran 119 tests — OK`). A second writer then changed the same two modules inside
this contour: `architecture_fitness.py` at 06:38:57 (union kept; `$id`-collision handling extended with a
per-inventory `fail_closed`, an `unattributed` signal map, `_unattributable_reference_detail`, and a new
`test_contract_compatibility_bounds_duplicate_declared_id_to_certified_state` at 06:41:32) and
`architecture.py` at 06:46:30 with `architecture_fitness.py` again at 06:49:01 (the `review-code.md` C2
remedy: `SCHEMA_REFERENCE_NOT_A_PATH` split out of `SCHEMA_REFERENCE_UNSAFE`, a new
`schema_reference_identity_path` fold, and `_reverse_contract_dependencies` extracted). None of that was
reverted here. **§2, §4 and §5 were therefore re-measured at 06:44–06:53 on the combined bytes** — the
implementer's union plus the concurrent boundary — and the rows say which arms belong to which author. If the
head you are reviewing differs from §9, re-run §1 before trusting any cell.

Tree: `fix/contract-closure-id-refs`, HEAD `7d21d95ad3f2df0eb59a3dd17df74d2a04731fdd`, uncommitted follow-up
(union identity + four new arms). Implementer-side diff vs `d871ea6`:

```
154     52      .grok-stack/adaptive_grok/architecture.py         (comparator code paths unchanged: only the
                                                                  two precedence comments/docstrings)
 88     10      .grok-stack/adaptive_grok/architecture_fitness.py  (union + self-edge filter + docstrings)
631      0      tests/test_architecture_fitness.py                 (9 new test methods, 0 deleted lines)
```

FORBID-001: `git diff d871ea6 -- tests/ | grep -c '^-[^-]'` = **0** — nothing deleted or weakened; the only
reversed expectation is the `expected_dependent=False` the implementer itself introduced at `7d21d95`, which
`review-test.md` demands be reversed. FORBID-002: no contract, `architecture/system.yaml`,
`architecture/rules.yaml`, governance, policy or compatibility-mode file is in the diff.

## 1. Re-derivation method

Host has no `pytest`; every run is `python3 -m unittest`. Each arm gets its own copy of the tree
(`shutil.copytree`, excluding `.git`, `__pycache__`, `.grok-stack/runtime`), exactly one edit is applied, and
the named methods run inside that copy only, so no arm can contaminate another and the delivery worktree is
never mutated. Per-arm command:

```bash
python3 -u -m unittest -q \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_compatibility_rechecks_unchanged_declared_ref_dependents \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_compatibility_rechecks_dependents_of_every_reference_grammar \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_compatibility_ignores_reference_without_declared_target \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_compatibility_still_reports_referrer_with_undeclared_reference \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_uses_declared_path_precedence_issue_146 \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_shares_the_comparator_reference_grammar \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_compatibility_fails_closed_on_duplicate_declared_schema_id \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_keeps_base_only_reference_dependents \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_adds_head_only_reference_dependents \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_attaches_named_path_despite_ambiguous_ids \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_terminates_on_self_reference \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_compatibility_bounds_duplicate_declared_id_to_certified_state \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_reverifies_declined_relative_path_referrers \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_reference_reasons_keep_declined_paths_apart_from_non_paths \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_real_contract_closure_supersets_legacy_fold_per_target \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_keeps_parent_segment_references_inside_repository \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_contract_dependency_closure_creates_no_self_edge
```

Seventeen methods: the pre-existing plain-relative control first -- it must stay green under every arm, which
is what makes a red arm a statement about the mutation rather than about the machine -- then the ten arms this
contour delivered or added, then the six the concurrent author added for C2/C3. Rows marked *full module*
additionally ran `python3 -u -m unittest -q tests.test_architecture_fitness`.

Mutations are literal search → replace text, not line numbers, because the lines moved twice during the
concurrent edits. A copy in which the search text is not unique must be reported as `ANCHOR NOT UNIQUE`,
never counted as a pass.

## 2. Pair counts, stated under one definition each

`FIT._contract_dependency_closure({t}, state, state)` and the reverse-edge walker over the **declared**
inventory (`ARCH.load_architecture` + `ARCH.contract_inventory`, 50 records; identical inputs in all trees):

| convention | `d871ea6` (before the fix) | `7d21d95` (delivered) | combined bytes at handover (union) |
|---|---|---|---|
| transitive target→dependent pairs (BFS scope of one changed target, self excluded) | **22** | **27** | **27** |
| one-hop reference pairs (target→referrer, self references included) | **10** (0 self) | **17** (3 self) | **17** (3 self) |
| one-hop cross-contract edges (self references removed — what the closure now creates) | **10** | **14** | **14** |
| targets with ≥1 dependent / distinct dependents | 9 / 6 | 13 / 9 | 13 / 9 |
| edges lost versus `d871ea6` | — | **0** | **0** |

The gained transitive pairs are `OPERATOR-HANDOFF→READY-BUNDLE`, `PREDECESSOR-BRIDGES→READY-BUNDLE`
(transitive, via task-evidence), `PREDECESSOR-BRIDGES→TASK-EVIDENCE`, `SHADOW-OUTCOME→SHADOW-COHORT`,
`TASK-EVIDENCE→READY-BUNDLE`. The combined bytes' `transitive`, `direct`, `cross_contract` and whole
`per_target` compare **equal** to `7d21d95`'s, so the union changed no fleet number.

The string "10 → 27" splices two conventions (a base-side one-hop count against a head-side transitive count)
and reproduces under no single method. Publish **22 → 27 transitive** and **10 → 14 cross-contract one-hop
edges** (17 one-hop *references*, three of which are self references).

**Self references are references, not dependencies.** The three self pairs are contracts whose `$ref` names
their own declared `$id` (`M7-PREDECESSOR-BRIDGES-V1`, `M7-SHADOW-COHORT-V1`, `M7-SHADOW-OUTCOME-V1`).
`requirements.md` ("Self-reference through the referrer's own `$id` — must not create a self edge or a
closure loop") is enforced where the edge is created. Measured effect on any gate outcome: **none** — arm U7
(restore the self edge) leaves all 12 named arms *and* the full module green, and all 50 per-target closures
are identical with and without the filter, because the BFS had already discarded the entry. It is disclosed
as a surviving (behaviour-equivalent) mutant instead of being presented as test-covered behaviour; the
observable half of the requirement — a self-referencing contract's closure is that contract alone, no loop,
nothing unrelated dragged in — is pinned by `test_contract_dependency_closure_terminates_on_self_reference`.

**The union's fleet effect is 0 pairs today, measured.** The shadowing case does not occur in the declared
model: `duplicate declared $id values: 0`, `$id values that are also a declared path: 0`. The union is
justified by the counter-example in
`test_contract_dependency_closure_uses_declared_path_precedence_issue_146` (red under the path-only mutant
U1) and by the fact that a narrowing inside a claimant now produces a `CONTRACT-REFERRER:
narrowed_constraint` finding it could not produce before (§6) — not by a fleet number.

## 3. Undeclared files: what these counts do and do not cover

Every count above is an edge **between declared contracts**. Measured: 27 JSON files exist under
`factory/contracts/jsonschema`, 50 contracts are declared fleet-wide, and exactly 2 of those files are not
declared in `architecture/system.yaml`:

```
- factory/contracts/jsonschema/earned-autonomy.v1.schema.json      ($id urn:adaptive-factory:m8:earned-autonomy:v1)
- factory/contracts/jsonschema/m7-autonomy-bridge.v1.schema.json   ($id urn:adaptive-factory:m8:m7-autonomy-bridge:v1)
```

Their references are real — the bridge carries `{"$ref": "urn:adaptive-factory:m7:ready-for-pr-bundle:v1"}`
and `{"$ref": "urn:adaptive-factory:m7:shadow-cohort:v1"}`, and `earned-autonomy` carries
`urn:adaptive-factory:m8:m7-autonomy-bridge:v1#/$defs/handoff` — and none of it can reach the gate:

* As a **referrer**, an undeclared file is not in the inventory, so the closure never walks its document and
  cannot produce its reverse edges; the comparator never compares it either.
* As a **target**, an undeclared file is `SCHEMA_REFERENCE_UNDECLARED` under *both* tables: the closure drops
  that edge (the reason is deny-listed) and the comparator raises it, which `compare_contracts` maps to
  `unsupported`. A `$ref` to an undeclared file is never silently ignored by the comparator — it is
  invisible only as a closure edge.

Consequence for issue #146's own table: of its 7 published `LOST` rows, **4 now produce an edge** —
`ready-for-pr-bundle→shadow-task-evidence`, `ready-for-pr-bundle→operator-handoff-proposal`,
`shadow-cohort→shadow-outcome`, `shadow-task-evidence→m7-predecessor-bridges`, i.e. exactly the four whose
referrer is declared — and **3 remain uncovered**: `earned-autonomy→m7-autonomy-bridge`,
`m7-autonomy-bridge→ready-for-pr-bundle`, `m7-autonomy-bridge→shadow-cohort`, purely because their referrer
is one of the two undeclared files. The issue's "9 of 19" is not a count this change closes, and
22/27/10/14/17 must not be read as one consistent enumeration of the repository's references: they count
declared-to-declared edges only. Recovery is a declaration change in `architecture/system.yaml`, which
FORBID-002 puts outside this wave.

Supporting measurement: 565 `$ref` strings inside the 50 declared contracts, of which 479 are local
`#`-only pointers and every one of the remaining 86 names a declared contract (`unresolved under either
table: 0`). The blind spot is "documents the gate does not load", not "references the gate mis-parses".

## 4. Comparator differential (AC-006 / SIG-002)

Harness: every declared contract × `{identity, drop-prop, narrow-minLength, loosen, add-required, add-anyOf,
add-oneOf, add-enum, drop-id, rename-title}` × `{bidirectional, producer_accepted_by_old,
consumer_accepts_old}`, one sorted line `contract|edit|policy|status|reasons` per tree, pairwise diff.
Re-run at 06:44 and again on the handover bytes:

```
lines: 1473  unsupported: 415    (d871ea6)
lines: 1473  unsupported: 415    (7d21d95, delivered)
lines: 1473  unsupported: 415    (combined bytes at handover)
differing lines base|delivered:        0
differing lines base|combined:         0
differing lines delivered|combined:    0
```

The comparator's resolution code is byte-identical to `7d21d95` and still passes
`precedence=SCHEMA_REFERENCE_ID_FIRST`; the implementer's own edits to `architecture.py` were two
comments/docstrings, and the 0-line differential above is the measurement that the concurrent C2 work did not
move the comparator's precedence either.

## 5. The matrix

`Result` is the measured output of the §1 command for that arm on the **combined bytes** (06:50–06:53).
"Killed by" names the red arms, with subtest labels.

| arm | exact one-line mutation (search → replace) | result | killed by |
|---|---|---|---|
| **M0** | none (copy as-is) | `Ran 12 tests in 18.565s` / `OK`; full module `Ran 120 tests in 75.937s` / `OK` | — |
| **M1** | `architecture.py` + `architecture_fitness.py` replaced by the `d871ea6` versions (fix reverted, tests kept) | `Ran 12 tests in 18.859s` / `FAILED (failures=11, errors=1)`; full module (06:47, mid-concurrent-edit) `Ran 120 tests in 82.214s` / `FAILED (failures=11, errors=1)` — **every failure inside the new arms, zero pre-existing failures** | grammar `(declared $id)`, `(path with JSON pointer)`, `(declared $id with JSON pointer)`, `..._issue_146 (CONTRACT-CLAIMANT)`, both one-sided arms, duplicate-`$id` (both), 3 `bounds_duplicate_declared_id` arms, spy guard ERRORs |
| **M2** | `reference_base, _fragment = schema_reference_parts(reference)` → `reference_base, _fragment = reference, None` | `Ran 12 tests in 18.664s` / `FAILED (failures=3)` | grammar `(path with JSON pointer)`, `(declared $id with JSON pointer)`, spy guard |
| **M3** | `paths_by_schema_id.setdefault(schema_id, []).append(record.path)` → `pass` (the `$id` table is never built) | `Ran 12 tests in 6.241s` / `FAILED (failures=11)` | both `$id` grammar arms, `..._issue_146 (CONTRACT-CLAIMANT)`, both one-sided arms, duplicate-`$id` (both), 3 `bounds_duplicate_declared_id` arms, spy guard |
| **M4** | `architecture.py` `if len(declared) != 1:` → `if False:` (a shared `$id` silently takes the first path) | `Ran 12 tests in 19.054s` / `FAILED (failures=6)` | duplicate-`$id (colliding=True)`, `..._attaches_named_path_despite_ambiguous_ids`, 4 `bounds_duplicate_declared_id` arms |
| **M5** | `if failure in SCHEMA_REFERENCE_UNRESOLVED:` → `if False:` (any miss, including a plain undeclared `$ref`, becomes fatal) | `Ran 12 tests in 5.927s` / `FAILED (errors=6)` | `..._ignores_reference_without_declared_target`, `..._still_reports_referrer_with_undeclared_reference` (all 3 references), both one-sided arms |
| **M6** | `architecture.py` `if relative in declared_paths:` → `if False:` (a resolved relative path is never declared) | `Ran 12 tests in 18.392s` / `FAILED (failures=4, errors=1)` | pre-existing control `(changed_contract='CONTRACT-COMMON')`, grammar `(plain relative path)`, `(path with JSON pointer)`, `..._issue_146 (CONTRACT-TARGET)`, ambiguous-claimant arm ERRORs |
| **M7** | `for precedence in (SCHEMA_REFERENCE_PATH_FIRST, SCHEMA_REFERENCE_ID_FIRST):` → `("declared_id_first", SCHEMA_REFERENCE_ID_FIRST)` (closure inherits the comparator's precedence) | `Ran 12 tests in 17.556s` / `FAILED (failures=2, errors=1)` | `..._issue_146 (CONTRACT-TARGET)`, spy guard (no path-first look-up recorded), ambiguous-claimant arm ERRORs |
| **M8** | the shared `_reference_identity_candidates(...)` call replaced by the pre-fix grammar `posixpath.normpath(posixpath.join(posixpath.dirname(record.path), reference))` + `if legacy in declared_paths` (plus `import posixpath`) | `Ran 12 tests in 5.735s` / `FAILED (failures=12)` | every arm except the plain-relative control and `..._ignores_reference_without_declared_target` |
| **U1** *(finding 1)* | `for precedence in (SCHEMA_REFERENCE_PATH_FIRST, SCHEMA_REFERENCE_ID_FIRST):` → `(SCHEMA_REFERENCE_PATH_FIRST,)` — the **substituting** path-first behaviour the review measured as its Important 4 | `Ran 12 tests in 4.444s` / `FAILED (failures=2)`; on the implementer-only bytes at 06:32 the full module gave `Ran 119 tests — FAILED (failures=2)` | `..._issue_146 (CONTRACT-CLAIMANT)` (referrer no longer re-verified when the claimant narrows), spy guard (no `$id`-table look-up recorded) |
| **U3** *(finding 2)* | `for inventory, fail_closed in ((before, False), (after, True)):` → `((after, True),)` — the reviewer's M-S4, which **survived all 115 tests on `7d21d95`** | `Ran 12 tests in 6.090s` / `FAILED (failures=2)` | `..._keeps_base_only_reference_dependents` (the new arm), `bounds_duplicate_declared_id (arm='base-only collision')` |
| **U4** *(finding 2, symmetric)* | same loop → `((before, False),)` | `Ran 12 tests in 5.890s` / `FAILED (failures=5)` | `..._adds_head_only_reference_dependents` (the new arm), duplicate-`$id (colliding=True)`, 3 `bounds_duplicate_declared_id` arms |
| **U5** | `if not candidates and failures:` → `if failures:` (a miss in one table is fatal even when the other named a contract) | `Ran 12 tests in 4.352s` / `FAILED (errors=1)` | `..._attaches_named_path_despite_ambiguous_ids` — the run raises where it must not |
| **U6** | `if not candidates and failures:` → `if False and failures:` (a shared `$id` is silently dropped) | `Ran 12 tests in 4.317s` / `FAILED (failures=3)` | duplicate-`$id (colliding=True)`, 2 `bounds_duplicate_declared_id` arms |
| **U7** | `if target_id is not None and target_id != record.id:` → `if target_id is not None:` (self edge restored) | `Ran 12 tests in 6.432s` / **`OK`**; full module `Ran 120 tests in 82.878s` / `OK` | **survives — behaviour-equivalent** (§2). Its non-equivalence is confined to the published metric |
| **U8** *(concurrent author's boundary)* | `if failure == SCHEMA_REFERENCE_AMBIGUOUS and not fail_closed:` → `... and False:` (base-side collision aborts again) | `Ran 12 tests in 4.388s` / `FAILED (errors=2)` | `bounds_duplicate_declared_id (arm='base-only collision')`, `(arm='cleanup pull request with an unrelated contract edited')` |
| **U9** *(concurrent author's boundary)* | same line → `if failure == SCHEMA_REFERENCE_AMBIGUOUS:` (head-side collision never aborts) | `Ran 12 tests in 4.397s` / `FAILED (failures=3)` | duplicate-`$id (colliding=True)`, 2 `bounds_duplicate_declared_id` arms |

Sixteen of the seventeen arms die; U7 is the one disclosed survivor and §2 states why no test can kill it.
No red arm's assertion is about helper internals: every one asserts the observable gate output
(helper-level `applicability.scanned_scope` plus the finding rows).

### Confirmed by whom

* Independently reproduced by the test reviewer, on `7d21d95`: **M1** (their `Ran 115 — FAILED (failures=5,
  errors=1)`, zero pre-existing failures), **M7** ("both `issue_146` subtests + the spy guard, exactly as
  claimed"), their own **M-S4 = U3 surviving** on the delivered tree, and **their 1473-line differential at
  0 differing lines / 415 unsupported rows**. Those are corroborated twice (their run; §4/§5 above).
* Only this implementer's record, never re-run by a reviewer: M2, M3, M4, M5, M6, M8, and everything created
  after the review — U1, U4, U5, U6, U7, and U8/U9 (the last two cover the concurrent author's boundary and
  are reported here so the matrix is complete for the bytes that will actually be gated).
* The earlier implementer-only pass (06:32, `Ran 11 tests`, 119-test module) produced the same kill sets; its
  timings are superseded by the rows above.

## 6. What the two fixes changed, in observable terms

Finding 1 (union). The review's counter-example, run through the real gate (`FIT._contract_compatibility`):

```
shadowing inventory, changed=CONTRACT-TARGET
  status=fail  scope=['CONTRACT-REFERRER', 'CONTRACT-TARGET']
  findings=['CONTRACT-TARGET: narrowed_constraint']
shadowing inventory, changed=CONTRACT-CLAIMANT
  status=fail  scope=['CONTRACT-CLAIMANT', 'CONTRACT-REFERRER']
  findings=['CONTRACT-CLAIMANT: narrowed_constraint', 'CONTRACT-REFERRER: narrowed_constraint']
```

The second block is the hole closing: the comparator resolves the referrer's `$ref` through the claimant's
`$id`, so re-verifying the referrer now *reports* the claimant's narrowing instead of passing it. Under U1
(path-first by substitution) the referrer row disappears — exactly what `review-test.md` measured, and what
`..._issue_146 (CONTRACT-CLAIMANT)` now forbids.

Finding 2 (both inventories). A `$id` that exists in only one state, referrer byte-identical across the diff:

```
one-sided declared id: only in base
  status=unsupported  scope=['CONTRACT-REFERRER', 'CONTRACT-TARGET']
  findings=['CONTRACT-REFERRER: unsupported compatibility semantics', 'CONTRACT-TARGET: changed_constraint']
one-sided declared id: only in head
  status=unsupported  scope=['CONTRACT-REFERRER', 'CONTRACT-TARGET']
  findings=['CONTRACT-REFERRER: unsupported compatibility semantics', 'CONTRACT-TARGET: changed_constraint']
```

Each arm killed exactly one of U3/U4 on the implementer-only bytes, and both halves of the two-inventory walk
stay pinned on the combined bytes (U3/U4 rows above; each is additionally held by the concurrent
`bounds_duplicate_declared_id` arms).

### Which `scanned_scope` carries the signal

`FIT._contract_compatibility(...).applicability.scanned_scope` **is** the closure, and that is what the arms
assert. The report-level scope is widened afterwards by `_bind_applicability_inventory`
(`architecture_fitness.py`; `scope.update(record.id for record in diff._head_state.contracts)` for category
`contract_compatibility`), so in CLI/JSON output the scope always names the whole head inventory and cannot
carry this signal — the finding rows do. `change-spec.yaml` SIG-001 as rewritten by the controller at 06:19
is correct about the report level; read as a claim about the helper-level scope the tests use, it would be
wrong. That is why every arm here asserts a finding row as well as scope.

## 7. Counts, corrected

* `7d21d95` added **six** new test methods, not seven: `git diff --numstat d871ea6..7d21d95 -- tests/` =
  `422 0`, added `def test_` lines = 6. The seventh name in `controller-verification.md` §4,
  `test_contract_compatibility_rechecks_unchanged_declared_ref_dependents`, exists at `d871ea6`
  (`tests/test_architecture_fitness.py:3961`).
* This follow-up adds four more (`..._keeps_base_only_reference_dependents`,
  `..._adds_head_only_reference_dependents`, `..._attaches_named_path_despite_ambiguous_ids`,
  `..._terminates_on_self_reference`) → **ten** implementer methods versus `d871ea6`; the concurrent author
  added `..._bounds_duplicate_declared_id_to_certified_state` (eleven). Module total 115 → 120. Two
  delivered arms were tightened in place (`..._issue_146`, `..._shares_the_comparator_reference_grammar`).
* The stale "seven new arms"/"seven regression arms" wording still sits in `tasks.md`;
  `controller-verification.md` §4 was partially corrected by its own author at 06:19. Both are
  controller-owned and outside this implementer's contour.

## 8. Requirements cross-check

`requirements.md` "Failure and edge cases", mapped to arms:

| requirement edge case | arm |
|---|---|
| bare `#/$defs/...` local pointer is not a cross-contract edge | grammar `(plain relative path)` control + the `not reference.startswith("#")` guard |
| `$id`-referenced dependent re-verified (AC-001) | `..._of_every_reference_grammar (declared $id)`, `(declared $id with JSON pointer)` |
| `file#/$defs/...` dependent (AC-002) | same arm, `(path with JSON pointer)`, `(declared $id with JSON pointer)` |
| reference not naming a declared contract: no edge, no raise (AC-004) | `..._ignores_reference_without_declared_target`, `..._still_reports_referrer_with_undeclared_reference` |
| same `$id` on two declared contracts fails closed (AC-005) | `..._fails_closed_on_duplicate_declared_schema_id`, `..._attaches_named_path_despite_ambiguous_ids`, `..._bounds_duplicate_declared_id_to_certified_state` |
| **reference that exists only in the base or only in the head state; both inventories must map their own `$id`** | `..._keeps_base_only_reference_dependents`, `..._adds_head_only_reference_dependents` — previously **no arm at all**, and the `(after,)` half-mutant kept 115 tests green |
| self reference must not create a self edge or a closure loop | `..._terminates_on_self_reference` (observable half); the edge-creation filter itself is U7, a disclosed equivalent mutant |
| one `$id` map per inventory pass, no repeated document walks | code read: one map per inventory; the union costs one extra table lookup per non-local `$ref`, not a second document walk |

## 9. Handover state, measured

```
$ python3 -m unittest -q tests.test_architecture_fitness
Ran 120 tests in 75.937s
OK
$ python3 -m unittest -q tests.test_architecture_model
Ran 79 tests in 1.996s
OK
$ git diff --check            (no output, rc=0)
$ ruff check .grok-stack/adaptive_grok/ tests/
All checks passed!
HEAD: 7d21d95ad3f2df0eb59a3dd17df74d2a04731fdd
uncommitted delta sha256 captured 06:45 (two concurrent module writes landed after it, 06:46:30 and
06:49:01), so this hash is *not* the hash of the bytes §5 measured:
  acfa26ccef742ae3829bc6afe8a6c8b35d21ada60630023b0544387030e90973
```

No `scripts/grok_verify.py` run was attempted (the controller schedules the single gate run after the three
review reports are committed). Any fingerprint-bound receipt is stale for the current bytes; whoever commits
must re-derive §1/§4/§9 against the new head.

## 10. Open item found while working in these files (not fixed here)

`review-code.md` C2 claims the delivered strict grammar can *lose* an edge that the pre-#146 normalisation
kept, silently. Verified at the grammar level on the handover bytes, before the concurrent remedy:

```
droppable reasons: ['schema reference escapes inventory', 'undeclared schema reference', 'unsafe schema reference']
  './money.json'   new grammar raises 'unsafe schema reference'  | pre-#146 join -> c/money.json
  'my file.json'   new grammar raises 'unsafe schema reference'  | pre-#146 join -> c/my file.json
  'a+b.json'       new grammar raises 'unsafe schema reference'  | pre-#146 join -> c/a+b.json
  'urn:x:y'        new grammar raises 'unsafe schema reference'  | pre-#146 join -> c/urn:x:y
```

`SCHEMA_REFERENCE_UNSAFE` was dual-purpose: "not a path grammar at all" (correctly droppable — it is the only
reason the `$id` fix works) and "a relative path this grammar refuses" (not droppable, because the
repository's path rules accept such paths). This implementer did **not** fix C2 in this pass: the assigned
scope was the test reviewer's three findings, and by the time `review-code.md` landed the concurrent author
was editing exactly these lines (the split exists now, see §"Concurrent-author notice"). Treat C2 as owned by
whoever lands the commit and re-check it against §5's M5/M6 and U3/U4 rows before calling the grammar question
closed.

## 11. Residual risk, deliberately not fixed

1. **The comparator still resolves `$id`-before-path**, so #147's shadowing defect is untouched by design
   (FORBID-003). Visible remainder, §6's first block: when only the *path* target narrows, the referrer is
   re-verified but its own verdict stays clean, because the comparator reads the claimant. Nothing passes
   silently — the changed contract's own row fails the run — but the referrer row is not the mirror image of
   the claimant case. Fixing it means moving the comparator, which #147 owns.
2. **Union ≠ superset in one corner.** When the path table names a contract and the `$id` table is ambiguous,
   the claimants are not attached (guessing would verify the wrong one) and nothing aborts. The collision is
   now *loud* either way through the concurrent `unattributed reference: …` signal, pinned by U5/U6/U8/U9.
   Unreachable on the shipped inventory (0 duplicate `$id`s measured).
3. **Fleet-level edge sets still have no test.** The 5 recovered `M7-*` pairs and the 14-edge count rest on
   this file's sweep, not on an arm; a future change could drop them without reddening `tests/` (review
   Important 5, still open). An inventory-sweep arm asserting two named pairs
   (`SHADOW-OUTCOME→SHADOW-COHORT`, `TASK-EVIDENCE→READY-BUNDLE`) would close it, but freezing fleet state
   into a test is the pattern that has already reddened this repository once
   (`test_added_landing_contracts_have_supported_closed_semantics` holds a 14-id list), so it was left out of
   this contour on purpose.
4. **Paperwork drift the controller must absorb** (outside this implementer's contour):
   `change-spec.yaml` `objective.success_metric` still reads "10 -> 27"; `INV-003` still says a reference is
   attached "never to a record that merely declares it as `$id`", which the union deliberately contradicts
   (path candidate kept, `$id` candidate added); `FORBID-003` remains satisfied literally — the closure never
   *orders* `$id` before path, it consults both tables — but its wording invites the substitution reading
   that produced the review's Important 4; `AC-002`/`AC-003` still cite the pre-existing
   `..._rechecks_unchanged_declared_ref_dependents` as evidence for grammars it does not exercise; the AC-003
   clause "the end-to-end finding set for a control edit is byte-identical before and after" is still prose
   in `controller-verification.md` §3 rather than a test; `tasks.md` still says "seven regression arms".
5. **Two undeclared contracts (§3)** keep three of the issue's rows uncovered no matter how the closure
   resolves references. That needs a declaration change, not a code change.

## 12. Finding A (security review Important 2) — the implementer's own battery

Recorded by the author of the base-side ambiguity change, on the bytes measured at 07:0x. Per the
measurement-hygiene ruling this section carries no inventory-wide count: mutation, command, outcome.

Command: the §1 arm list, which already contains
`...test_contract_compatibility_bounds_duplicate_declared_id_to_certified_state`; one search/replace per arm
in a private copy, delivery worktree untouched. §5's U8/U9 are the same boundary re-measured by the other
author of this wave; the three rows below are the parts of finding A that neither U5/U6 nor U8/U9 reach.

| arm | exact one-line mutation (search → replace) in `architecture_fitness.py` | result | killed by |
|---|---|---|---|
| **A0** | none (control) | `Ran 11 tests in 3.227s` / `OK` | — |
| **A1** | `for inventory, fail_closed in ((before, False), (after, True)):` → `((before, True), (after, True))` (the reviewed abort-on-either-inventory restored) | `Ran 11 tests in 3.168s` / `FAILED (errors=2)` | `bounds_duplicate_declared_id_to_certified_state` — the base-only and cleanup-pull-request arms abort instead of completing |
| **A2** | `if failure == SCHEMA_REFERENCE_AMBIGUOUS and not fail_closed:` → `if failure == SCHEMA_REFERENCE_AMBIGUOUS:` (the certified state stops aborting too) | `Ran 11 tests in 3.339s` / `FAILED (failures=3)` | `bounds_duplicate_declared_id_to_certified_state` **and** the pre-existing `fails_closed_on_duplicate_declared_schema_id`, so that assertion still has teeth after finding A |
| **A3** | `if failure != SCHEMA_REFERENCE_AMBIGUOUS:` → `if failure != SCHEMA_REFERENCE_AMBIGUOUS or True:` in `_unattributable_reference_detail` (message stops naming offenders) | `Ran 11 tests in 3.157s` / `FAILED (failures=3)` | `bounds_duplicate_declared_id_to_certified_state` — abort text and row lose the colliding `$id` and both declared paths |
| **A4** | `if SCHEMA_REFERENCE_AMBIGUOUS in failures:` → `if False and SCHEMA_REFERENCE_AMBIGUOUS in failures:` (skip the base reference in silence) | `Ran 11 tests in 3.277s` / `FAILED (failures=1)` | `bounds_duplicate_declared_id_to_certified_state` — the re-verified dependent loses its attributed row, so the outcome is lost rather than explicit |
| **A5** | `        if identity in changed_ids\n` → `        if identity is not None\n` (charge the collision to every run) | `Ran 11 tests in 3.995s` / `FAILED (failures=1)` | `bounds_duplicate_declared_id_to_certified_state` — the cleanup arm's untouched referrer is named by a gate that never scheduled it |

Five of six arms die, A0 is the control. The other ten arms in the §1 list stayed green under every row above,
including the plain-relative control, both one-sided `$id` arms, the self-reference arm, the path-precedence
arm and the shared-grammar spy guard: finding A neither widens nor narrows what those arms observe.

New test method: `..._bounds_duplicate_declared_id_to_certified_state`, four subtest arms in two loops —
`head-only collision` and `collision in both states` must abort with the colliding `$id` and both declared
paths in the message; `base-only collision` must complete with the dependent re-verified and attributed;
`cleanup pull request with an unrelated contract edited` must complete without scheduling or naming the
untouched referrer.

