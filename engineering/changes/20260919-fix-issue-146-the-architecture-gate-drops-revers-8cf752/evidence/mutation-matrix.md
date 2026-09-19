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
reverted here. **§2, §4 and §5 were re-measured on the combined bytes** — §5's first pass at 06:50–06:53, the
final pass at 07:05–07:09 (current modules: `architecture.py` 06:46:30, `architecture_fitness.py` 06:56:07),
and §9 at 07:10 — and the rows say which arms belong to which author. If the head you are reviewing differs
from §9, re-run §1 before trusting any cell.

Tree: `fix/contract-closure-id-refs`, HEAD `7d21d95ad3f2df0eb59a3dd17df74d2a04731fdd`, uncommitted follow-up.
Combined diff vs `d871ea6` as measured at 07:12 (both authors):

```
214     52      .grok-stack/adaptive_grok/architecture.py
242     17      .grok-stack/adaptive_grok/architecture_fitness.py
1256     0      tests/test_architecture_fitness.py     (16 added `def test_` methods, 0 deleted lines)
```

Of those 16 methods ten are the implementer's (six delivered at `7d21d95`, four added by this follow-up) and
six are the concurrent author's (§7). The implementer's own slice at 06:36 was `154/52`, `88/10`, `631/0`.

FORBID-001: `git diff d871ea6 -- tests/ | grep -c '^-[^-]'` = **0** — nothing deleted or weakened; the only
reversed expectation is the `expected_dependent=False` the implementer itself introduced at `7d21d95`, which
`review-test.md` demands be reversed. FORBID-002: the only files in the diff are the two modules, the test
module and `engineering/changes/…` paperwork — no contract, `architecture/system.yaml`,
`architecture/rules.yaml`, governance, policy or compatibility-mode file.

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
closure loop") is enforced where the edge is created. Measured history of that claim, both passes reported:
at 06:50 arm U7 (restore the self edge) left all twelve then-named arms *and* the 120-test module green, and
all 50 per-target closures were byte-identical with and without the filter (the BFS had already discarded the
entry), so at that moment U7 was a surviving behaviour-equivalent mutant and no test could have pinned it. The
concurrent author then extracted `_reverse_contract_dependencies` -- which makes the direct edge map a
countable unit instead of a local variable -- and added
`test_contract_dependency_closure_creates_no_self_edge`; on that shape U7 dies (§5). The implementer's own
`..._terminates_on_self_reference` pins the observable half (a self-referencing contract's closure is that
contract alone, no loop, nothing unrelated dragged in).

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
Re-run at 06:44, on the handover bytes, and a third time at 07:14Z on the §9 bytes:

```
lines: 1473  unsupported: 415    (d871ea6)
lines: 1473  unsupported: 415    (7d21d95, delivered)
lines: 1473  unsupported: 415    (combined bytes at handover)
differing lines base|delivered:        0
differing lines base|combined:         0
differing lines delivered|combined:    0
```

The comparator's own resolution *behaviour* is unchanged. What is **not** true, and was wrong in the earlier
draft of this file, is that `architecture.py` is byte-identical to `7d21d95`: it differs by `82/21` lines,
because the C2 remedy changed the reference-grammar layer the comparator resolves through —
`SCHEMA_REFERENCE_UNRESOLVED` membership, the refusal reasons inside `schema_reference_relative_path`,
`schema_reference_target_path`'s empty-base return, and the new `schema_reference_identity_path` fold. What
is unchanged is the comparator entry point and its precedence: `compare_contracts`
(`architecture.py:3375`) is not in the diff at all and the resolver still passes
`precedence=SCHEMA_REFERENCE_ID_FIRST` (`architecture.py:1409`).

The behavioural claim is measured, not asserted. Re-running the harness at 07:14Z on the §9 bytes produced
output that is **the same file** as the 06:44 run for every tree — all three 1473-line outputs share
`sha256 816d37516321b130cee9d…` — and the reason split cannot surface on this inventory for a second,
independent reason: neither `unsafe schema reference` nor `schema reference is not a repository path` occurs
anywhere in those 1473 lines in any tree (count 0 for base, 0 for the delivered bytes, 0 for §9).

## 5. The matrix

`Result` is the measured output of the twelve-method variant of the §1 command for that arm, on the modules as
they stood at 06:49:01 (pass run 06:50–06:53). "Killed by" names the red arms, with subtest labels. The
authoritative rows for the delivered bytes are the **final pass** and the **second observer** below it, which
use the full seventeen-method §1 command.

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
| **U7** | `if target_id is not None and target_id != record.id:` → `if target_id is not None:` (self edge restored) | `Ran 12 tests in 6.432s` / **`OK`**; full module `Ran 120 tests in 82.878s` / `OK` | **survived that pass** (§2 tells why, and the final pass below kills it) |
| **U8** *(concurrent author's boundary)* | `if failure == SCHEMA_REFERENCE_AMBIGUOUS and not fail_closed:` → `... and False:` (base-side collision aborts again) | `Ran 12 tests in 4.388s` / `FAILED (errors=2)` | `bounds_duplicate_declared_id (arm='base-only collision')`, `(arm='cleanup pull request with an unrelated contract edited')` |
| **U9** *(concurrent author's boundary)* | same line → `if failure == SCHEMA_REFERENCE_AMBIGUOUS:` (head-side collision never aborts) | `Ran 12 tests in 4.397s` / `FAILED (failures=3)` | duplicate-`$id (colliding=True)`, 2 `bounds_duplicate_declared_id` arms |

Fifteen of the sixteen mutated arms die in that 12-method pass (`M0` is the unmutated control and `OK`; the
survivor is U7, discussed in §2 and killed by the final pass below). No red arm's
assertion is about helper internals: every one asserts the observable gate output (helper-level
`applicability.scanned_scope` plus the finding rows).

### Final pass: 17 named methods, 125-test module, bytes with delta sha256 `17236983a0a2…` (07:05–07:09)

The table above measured twelve methods on the 06:49:01 bytes. After the concurrent author added the C2/C3
arms, the whole matrix was re-run against the current modules (`architecture_fitness.py` 06:56:07,
`architecture.py` 06:46:30) with the seventeen-method command in §1:

| arm | result (17 named methods) | arm | result (17 named methods) |
|---|---|---|---|
| M0 | `Ran 17 tests in 6.396s` / `OK`; full module `Ran 125 tests in 95.347s` / `OK` | U3 | `Ran 17 tests in 21.777s` / `FAILED (failures=2)` |
| M1 | `Ran 17 tests in 5.784s` / `FAILED (failures=12, errors=4)` — control green, **all 16 inside new arms** | U4 | `Ran 17 tests in 21.619s` / `FAILED (failures=5)` |
| M2 | `Ran 17 tests in 6.480s` / `FAILED (failures=3)` | U5 | `Ran 17 tests in 16.758s` / `FAILED (errors=1)` |
| M3 | `Ran 17 tests in 6.421s` / `FAILED (failures=12)` | U6 | `Ran 17 tests in 12.538s` / `FAILED (failures=3)` |
| M4 | `Ran 17 tests in 6.558s` / `FAILED (failures=6)` | **U7** | `Ran 17 tests in 12.310s` / `FAILED (failures=1)`; full module `Ran 125 tests in 95.561s` / `FAILED (failures=1)` |
| M5 | `Ran 17 tests in 6.677s` / `FAILED (errors=7)` | U8 | `Ran 17 tests in 12.518s` / `FAILED (errors=2)` |
| M6 | `Ran 17 tests in 26.196s` / `FAILED (failures=7, errors=1)` | U9 | `Ran 17 tests in 12.731s` / `FAILED (failures=3)` |
| M7 | `Ran 17 tests in 22.467s` / `FAILED (failures=2, errors=1)` | M8 | `Ran 17 tests in 22.057s` / `FAILED (failures=13)` |
| U1 | `Ran 17 tests in 21.904s` / `FAILED (failures=2)` | | |

**Every arm now dies, including U7** (killed by the concurrent author's
`test_contract_dependency_closure_creates_no_self_edge`, and only by it), and M1's kill set grew to include
the four C2/C3 arms (`..._creates_no_self_edge`, `..._keeps_parent_segment_references_inside_repository`,
`test_reference_reasons_keep_declined_paths_apart_from_non_paths`,
`test_real_contract_closure_supersets_legacy_fold_per_target`) while the pre-existing plain-relative control
stayed green.

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

### Second observer: the whole battery re-measured by the evidence owner, 07:08–07:27Z

The controller asked that M0 and every arm be re-run so that no row is inherited and no control row can read
later as an unverified claim. That pass is recorded here — the file is this implementer's evidence, and an
independent measurement of the same rows is the cheapest way to make them checkable twice. It bound the
**same bytes the delivered commit carries**: sha256 over `architecture.py` + `architecture_fitness.py` +
`tests/test_architecture_fitness.py` is `030fe6cd58d19971…`, and that is the value the same three files have
**at `30a07c6` and at the current HEAD `6e79d0c`** (verified with `git show <ref>:<path>`, not with the working
tree, which was being edited concurrently). So no row below is inherited and none is bound to bytes
that were never committed. The pass copied the tree **once** into a private snapshot and mutated copies of that
snapshot, so no arm can be measured against different bytes. That matters because the 06:50 pass had copied
the live worktree per arm and three of its arms (M3, M5, M8) came back `ANCHOR NOT UNIQUE` against the
grammar the concurrent author was editing at the time. Harness and raw logs, for anyone who wants the
transcripts rather than the tables: `~/.cache/closure146-r2/mut_matrix.py` (arm definitions),
`rerun_matrix.py` (snapshot binding and the two passes), `rerun-named-125.log`, `rerun-full-125.log`,
`rerun-ashort-125.log`, `rerun-rseries-125.log`, `comparator-diff-125.log`, `edge_sets.py`. Every anchor was
re-checked for uniqueness on the committed bytes before anything was reported (`check_anchors.py`: nineteen
anchor edits across the seventeen §5 arms); the four reason-split and four A-series mutations were applied by
the same copy-and-abort routine, so each of them also matched exactly once — an anchor that did not is printed
as `ANCHOR NOT UNIQUE` and yields no verdict.

Verdict: **all seventeen named-arm rows and all seventeen full-module rows reproduced the table above
exactly** — same `Ran 17 tests` / `Ran 125 tests` counts, same `FAILED (…)` totals, M0 `OK` in both passes.
Four things this pass adds rather than confirms:

* **Full-module numbers for every arm**, not only for M0 and U7. Each arm's 125-test run carries the same
  failure total as its 17-method run **except M6**, whose full-module run is `FAILED (failures=8, errors=1)`
  because it additionally reddens the **pre-existing**
  `test_contract_compatibility_ignores_unrelated_unsupported_contracts`. So "every failure inside the new
  arms, zero pre-existing failures" is a statement about **M1**, where it holds, and must not be read as a
  property of every arm.
* An isolated, un-contended control run: `Ran 17 tests in 6.846s` / `OK` and `Ran 125 tests in 73.989s` /
  `OK`. The battery's own wall times were measured with up to 8 arms in flight on a 22-core host and are not
  comparable to single-shot timings anywhere in this file; only the counts and verdicts are.
* The reason-split table below was re-run independently at 07:27Z with the 17-method set and a green
  no-mutation control (`mZ`: `Ran 17 tests in 7.379s` / `OK`): R1 `FAILED (failures=4)` with the same three
  declined spellings plus the classification lock, R2 `FAILED (failures=3)`, R3 `FAILED (failures=4,
  errors=7)`, R4 `FAILED (failures=1)`. The only difference from the recorded rows is R3, which here also
  errors `..._keeps_base_only_reference_dependents` and `..._adds_head_only_reference_dependents` — the two
  one-sided arms the 15-method pass did not run. R5 **is** U7 and reproduced exactly (`FAILED (failures=1)`,
  killed only by `..._creates_no_self_edge`). No arm in either table survives.
* The A-series of §12 was re-run the same way at 07:23Z, and its control is green on these bytes
  (`Ran 17 tests in 6.580s` / `OK`), so §12's rows stand: A1 `FAILED (errors=2)`, A3 `FAILED (failures=3)`,
  A4 `FAILED (failures=1)`, A5 `FAILED (failures=1)`, each killed by exactly the
  `bounds_duplicate_declared_id_to_certified_state` arm §12 names. A2 is the same mutation as U9 and was not
  run twice. **No result from `mutation_battery_findingA.py` is carried into this file**: that harness's
  unmutated control died at import (`Ran 11 tests in 0.001s` / `FAILED (errors=11)`), so its six arms prove
  nothing either way; the coverage for those behaviours is the named tests in
  `tests/test_architecture_fitness.py` plus the U/A rows above with a green control.

Consequence for the bullet above: M2, M3, M4, M5, M6, M8, U1, U4, U5, U6, U7, U8, U9 and the R/A rows are now
measured twice, by two authors, on the same bytes. It is still one worktree and one host — a reviewer
re-deriving §1 somewhere else is the check that counts.

### Reason-split arms (finding C2), measured on the C2 bytes at 07:15–07:18

These arms exist because C2's remedy is a *reason split*, not a set edit: each side of the split has to stay
where it is, and the recovery has to be the thing that keeps the edge. Each arm was applied in place to a
pristine export of `7d21d95` carrying the delivered modules and tests, then reverted; the pass is fifteen
named closure/grammar methods. `mZ` (copy, no mutation) is the contradiction control:
`Ran 15 tests in 12.561s` / `OK`.

| arm | exact one-line mutation (search → replace) | result | killed by |
|---|---|---|---|
| **R1** — the C2 regression itself: `UNSAFE` droppable again | `architecture.py` `{SCHEMA_REFERENCE_NOT_A_PATH, SCHEMA_REFERENCE_ESCAPE, SCHEMA_REFERENCE_UNDECLARED}` → the same set **plus** `SCHEMA_REFERENCE_UNSAFE` | `Ran 15 tests in 6.097s` / `FAILED (failures=4)` | `..._reverifies_declined_relative_path_referrers` (one failure per declined spelling: `./common.json`, a space, a `+`) and `test_reference_reasons_keep_declined_paths_apart_from_non_paths` (the set-composition lock). This is the named-test answer to "put the reason back in the droppable set". |
| **R2** — recovery deleted, reason kept non-droppable | `architecture_fitness.py` `if identity_path is not None and identity_path in declared_paths:` → `if False and identity_path is not None and ...` | `Ran 15 tests in 5.981s` / `FAILED (failures=3)` | `..._reverifies_declined_relative_path_referrers` only: the edge is lost *silently*, which is the finding-C2 failure mode with the labels fixed. So the recovery, not the label, is what carries the property. |
| **R3** — the new reason made fatal | drop `SCHEMA_REFERENCE_NOT_A_PATH` from `SCHEMA_REFERENCE_UNRESOLVED` | `Ran 15 tests in 6.029s` / `FAILED (failures=4, errors=5)` | `..._ignores_reference_without_declared_target`, `..._still_reports_referrer_with_undeclared_reference`, `..._fails_closed_on_duplicate_declared_schema_id`, two `bounds_duplicate_declared_id` arms, `test_reference_reasons_keep_declined_paths_apart_from_non_paths`: an IRI base would abort the run instead of falling through to the declared-`$id` table, i.e. the `$id` half of issue #146 dies. This is why the fix is a split and not a narrowing of the set. |
| **R4** — scheme bases merged back into the declined class | `architecture.py` `if reference_base.startswith("/") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", reference_base):` → `if reference_base.startswith("/"):` | `Ran 15 tests in 6.781s` / `FAILED (failures=1)` | `test_reference_reasons_keep_declined_paths_apart_from_non_paths` only, and that is the honest report: on today's tests this mutant is behaviourally equivalent (the closure unions both tables, so an IRI still resolves through `$id`); only the classification lock kills it. Kept because the defect being fixed *is* a classification. |
| **R5** — self edge restored (= **U7**, re-measured here) | `architecture_fitness.py` `if target_id is not None and target_id != record.id:` → `if target_id is not None:` | `Ran 15 tests in 6.004s` / `FAILED (failures=1)` | `..._creates_no_self_edge` and nothing else — including not `..._terminates_on_self_reference`, whose closure assertion is insensitive to a self edge (§2). |

`..._keeps_parent_segment_references_inside_repository` stayed green under all five arms, as it must: it is
the control proving the recovery did not have to widen the `../`-inside-the-repository spelling the shipped
inventory already uses, so it is not a lock on the reason split.

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
  `..._terminates_on_self_reference`) → **ten** implementer methods versus `d871ea6`. The concurrent author
  added six (`..._bounds_duplicate_declared_id_to_certified_state`,
  `..._reverifies_declined_relative_path_referrers`,
  `test_reference_reasons_keep_declined_paths_apart_from_non_paths`,
  `test_real_contract_closure_supersets_legacy_fold_per_target`,
  `..._keeps_parent_segment_references_inside_repository`, `..._creates_no_self_edge`) → **16** added
  `def test_` lines versus `d871ea6` with **0** deleted, and the module went 115 → 125 tests. Two delivered
  arms were tightened in place (`..._issue_146`, `..._shares_the_comparator_reference_grammar`).
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
$ date -u +%FT%TZ                 2026-09-19T07:10:24Z
$ python3 -m unittest -q tests.test_architecture_fitness
Ran 125 tests in 89.299s
OK
$ python3 -m unittest -q tests.test_architecture_model
Ran 79 tests in 2.360s
OK
$ git diff --check            (no output, rc=0)
$ ruff check .grok-stack/adaptive_grok/ tests/
All checks passed!   (rc=0)
HEAD: 7d21d95ad3f2df0eb59a3dd17df74d2a04731fdd
git diff | sha256sum: a45b3b6f99e21381e38a74016f5f2d724c12fd2a947462280846fc84b17f22f2
   module bytes behind it: architecture.py 06:46:30, architecture_fitness.py 06:56:07, tests 07:03:57
closure pair counts on those bytes: 27 transitive / 17 one-hop references (3 self) / 14 cross-contract,
   pair sets equal to 7d21d95's; duplicate declared $id: 0; $id that is also a declared path: 0
comparator differential on those bytes: 1473 lines, 0 differing vs d871ea6 and vs 7d21d95, 415 unsupported
```

The delta hash also covers the controller's paperwork edits, so it moves even when the modules do not; the
module mtimes above are the part that matters for §5. The product bytes above were committed as
`30a07c6bb43f76b4b60cfd05700777e771024c10` at 07:13:28 by the controller (this implementer made no commit);
`git diff 30a07c6 -- .grok-stack/ tests/` is empty, so §5's final pass and §9 describe that head exactly.
This file's re-measurements landed after that commit and are still uncommitted. No `scripts/grok_verify.py`
run was attempted (the controller schedules the single gate run after the three review reports are
committed). Any receipt bound to `7d21d95` is stale for `30a07c6` and must be re-derived against it, together
with §1/§4/§9.


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
was already editing exactly those lines.

**Status on the handover bytes: C2 is fixed by that concurrent author**, by the remedy the review prescribed —
`SCHEMA_REFERENCE_NOT_A_PATH` split out of `SCHEMA_REFERENCE_UNSAFE`, the droppable set narrowed to
`{NOT_A_PATH, ESCAPE, UNDECLARED}`, and `schema_reference_identity_path` recovering the declined relative
folds — with four arms: `..._reverifies_declined_relative_path_referrers`,
`test_reference_reasons_keep_declined_paths_apart_from_non_paths`,
`test_real_contract_closure_supersets_legacy_fold_per_target`,
`..._keeps_parent_segment_references_inside_repository`. §5's final pass re-measured this matrix on those
bytes (M5/M6/M8/U3/U4 all still die). The block above is kept because it is the independent confirmation that
the hole was real before the remedy, and because a reader who lands a later tree should re-check the same four
spellings rather than assume the split survived.

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
3. **Which fleet numbers no arm names.** `test_real_contract_closure_supersets_legacy_fold_per_target` (the
   concurrent author's) now locks the *structural* property — for every declared contract the closure
   supersedes the pre-#146 `posixpath` relation re-derived inside the test — which covers release.md's
   "any lost closure edge" No-go and INV-002 without freezing a count. Measured exactly, on the §9 bytes, that
   arm asserts `assertEqual(lost, [])` and `assertGreater(len(gained), 0)` (the second is its own vacuity
   guard), so **lost=0 is repository coverage** and the gained figure is not: re-deriving the arm's own
   comparison on this tree gives 22 legacy → 27 shipped pairs, lost 0, gained 5, the five being
   `OPERATOR-HANDOFF→READY-BUNDLE`, `PREDECESSOR-BRIDGES→READY-BUNDLE`, `PREDECESSOR-BRIDGES→TASK-EVIDENCE`,
   `SHADOW-OUTCOME→SHADOW-COHORT`, `TASK-EVIDENCE→READY-BUNDLE`. What still rests on this file's sweep
   alone is the positive set: the 22→27 / 10→14 numbers and the five recovered `M7-*` pairs are asserted by no
   arm, so a change that kept the superset property while dropping the new `$id` edges would not redden
   `tests/` (review Important 5, open in that narrower form). Freezing fleet identities into assertions is the
   pattern that has already reddened this repository once
   (`test_added_landing_contracts_have_supported_closed_semantics` holds a 14-id list), so it was left out of
   this contour deliberately rather than by omission.
4. **Paperwork the controller still has to absorb** (outside this implementer's contour; re-checked 07:12 on
   the bytes the controller had just edited): the "10 -> 27" metric is **already fixed** — `change-spec.yaml`
   `objective.success_metric` now reads "22 -> 27 with 0 edges lost and 5 gained", SIG-001 points at findings,
   and `release.md`/`brief.md` carry 22→27 and 14 cross-contract. Still open: `INV-003` says a reference
   naming a declared path is attached "never to a record that merely declares it as `$id`", which the union
   deliberately contradicts (path candidate kept, `$id` candidate added); `FORBID-003` remains satisfied
   literally — the closure never *orders* `$id` before path, it consults both tables — but its wording invites
   the substitution reading that produced the review's Important 4; `AC-002`/`AC-003` still cite the
   pre-existing `..._rechecks_unchanged_declared_ref_dependents` as evidence for grammars it does not
   exercise; the AC-003 clause "the end-to-end finding set for a control edit is byte-identical before and
   after" is still prose in `controller-verification.md` §3 rather than a test; `tasks.md:6` still says "the
   seven regression arms" (six at delivery, sixteen versus `d871ea6` now).
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

**Addendum, 07:23Z.** Re-run on the §9 bytes with the 17-method §1 set and a green control (`A0`:
`Ran 17 tests in 6.580s` / `OK`): A1 `FAILED (errors=2)`, A3 `FAILED (failures=3)`, A4 `FAILED (failures=1)`,
A5 `FAILED (failures=1)`, each killed by the same `bounds_duplicate_declared_id_to_certified_state` subtest
named above; A2 is the U9 mutation and is reported once, in §5. The eleven-method counts in the table are that
author's own pass and are superseded by these. Separately, and as a warning to whoever re-runs this battery: a
second harness for the same finding (`mutation_battery_findingA.py`) reported `Ran 11 tests in 0.001s` /
`FAILED (errors=11)` for **its unmutated control**, i.e. it died at import, so all six of its arms proved
nothing. No number from it is written anywhere in this package. An A-series row is worth recording only behind a
green A0; where it is red, the valid coverage for those behaviours is the named tests in
`tests/test_architecture_fitness.py` (`bounds_duplicate_declared_id_to_certified_state`,
`attaches_named_path_despite_ambiguous_ids`, `terminates_on_self_reference`,
`keeps_base_only_reference_dependents`, `adds_head_only_reference_dependents`) plus the U/A matrix above.
