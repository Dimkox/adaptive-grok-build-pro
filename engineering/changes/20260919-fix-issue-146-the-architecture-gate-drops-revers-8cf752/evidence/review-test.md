FAIL

Reviewer: independent test review of `fix/contract-closure-id-refs` (delivered `7d21d95`, base
`d871ea6d5d654406281dd65626a3dce61bf933fa`). All experiments ran in private throwaway clones under
`/tmp/qw146/` (`git clone --local` at `7d21d95`, plus one `d871ea6` tree); the delivery worktree was
untouched apart from this file. No `grok_verify.py` run was performed. Host has no pytest; every run
used `python3 -m unittest`.

**Bottom line (measured):** the new arms are real and discriminating — with the fix reverted, exactly
the new arms fail and *zero* pre-existing tests fail, so the defect genuinely was invisible to the old
suite, and every mutation arm they published does fail. What fails review is the *evidence arithmetic
and traceability*: the published widening metric is not reproducible under the method its own file
states, an acceptance criterion names a test that does not exercise that criterion, one load-bearing
half of the new closure code survives an unfalsified mutation, and one documented "safe" claim about
precedence is disproven by a measured counter-example that a new test then pins as expected behaviour.

## Critical (must fix)

1. **The published widening number is definition-mixed and not reproducible.**
   `engineering/changes/20260919-fix-issue-146-the-architecture-gate-drops-revers-8cf752/change-spec.yaml:155`
   (`objective.success_metric`: "closure target->dependent pairs go 10 -> 27 with zero edges lost"),
   `change-spec.yaml:161` (`SIG-001`: "(10 -> 27 target->dependent pairs fleet-wide)"),
   `evidence/closure-fix-blast-radius.md:14` ("the closure goes from **10 to 27** target→dependent
   pairs") and `evidence/README.md:5` (restates "10 → 27 closure pairs").
   Measured with their own stated method — `FIT._contract_dependency_closure({target}, state, state)`
   over the 50-record declared inventory, identical inputs in both trees — target→dependent **pairs**
   are **22 at `d871ea6` → 27 at `7d21d95`** (+5, none lost). **10** is the *direct* reverse-edge count
   at base (direct edges are **10 → 17** at head). The claim mixes a base-side direct-edge count with a
   head-side transitive-closure count, so it overstates the widening (+17 claimed vs +5/+7 actual) and no
   auditor re-deriving it gets the same number. The qualitative content (5 recovered pairs, no edge lost,
   exactly the dependents in their table) is confirmed; only the arithmetic is wrong. Fix: restate both
   counts under one definition each.

2. **AC-002 names a test that does not test AC-002, and AC-003's stated evidence does not exist as a
   test.** `change-spec.yaml:18` lists
   `test_contract_compatibility_rechecks_unchanged_declared_ref_dependents` as evidence for AC-002
   ("reaches a target through a `file#/$defs/...` reference"). Measured: that test
   (`tests/test_architecture_fitness.py:3961`, pre-existing at base —
   `git show d871ea6:tests/test_architecture_fitness.py:3961`) writes only
   `{"$ref": "common.json"}`; it contains no fragment and no `$id` anywhere. AC-002 is in fact discharged
   solely by `test_contract_compatibility_rechecks_dependents_of_every_reference_grammar`
   (`tests/test_architecture_fitness.py:4168`, `path with JSON pointer` and
   `declared $id with JSON pointer` subtests). Separately, AC-003's second half ("the end-to-end finding
   set for a control edit is **byte-identical before and after**", `change-spec.yaml:31`) has **no test**:
   measured — nothing in the added block compares two trees, and the only place that claim exists is
   prose in `evidence/controller-verification.md:50`. Fix the traceability (and, if the byte-identical
   property matters, either drop it from the AC or put it in a test).

## Important (should fix)

3. **A surviving mutation: the `before`-inventory half of the closure union is entirely untested, and it
   is load-bearing for the new grammar.** Mutation M-S4 = one line,
   `.grok-stack/adaptive_grok/architecture_fitness.py:916`
   `for inventory in (before, after):` → `for inventory in (after,):`.
   Measured: all seven closure arms PASS and `python3 -m unittest -q tests.test_architecture_fitness` →
   `Ran 115 tests — OK`. It is not dead code: probe scenario "head commit removes the `$id` that a
   referrer's `$ref` names" (referrer byte-identical across the two commits) gives, on the delivered tree,
   `status=unsupported`, `scope=[CONTRACT-REFERRER, CONTRACT-TARGET]`,
   `findings=["CONTRACT-REFERRER: unsupported compatibility semantics", "CONTRACT-TARGET:
   changed_constraint"]`; on M-S4, `status=fail`, `scope=[CONTRACT-TARGET]`, and the referrer row is gone —
   i.e. precisely the AC-001 signal ("the dependent is inside the re-verified set and its verdict is
   reported") vanishes, and an *unverifiable* dependency is downgraded to an ordinary finding attributed to
   the wrong contract. In my probe the run still failed on the target's own row, so I did **not** observe a
   false pass (inferred: the issue's own Severity section says a silent pass needs a permissive-policy
   target whose own row tolerates the edit — `READY-BUNDLE`/`OPERATOR-HANDOFF`, both `producer_accepted_by_old`
   — which is exactly the state after the #104 line of work lands). One arm in
   `test_contract_compatibility_rechecks_dependents_of_every_reference_grammar` where the *referenced*
   contract's `$id` (or the ref) exists only at base would kill this mutant.

4. **The widened closure still does not catch a real edit, and a new test asserts that drop as correct.**
   Scenario (measured, `/tmp/qw146/probe_holes.py` on the delivered tree): `CONTRACT-CLAIMANT` declares
   `$id: "dir/target.json"`, `CONTRACT-TARGET` is declared at path `engineering/contracts/dir/target.json`,
   `CONTRACT-REFERRER` is `{"$ref": "dir/target.json"}` and is byte-identical across the diff. Narrowing
   *only the claimant* (`minLength: 1 → 9`) gives
   `scope=[CONTRACT-CLAIMANT]`, `findings=["CONTRACT-CLAIMANT: narrowed_constraint"]` — the referrer is not
   re-verified. But the comparator resolves that same ref `$id`-first, so the referrer's verdict *is* a
   function of the claimant's document: forcing the referrer through `ARCH.compare_contracts(old_referrer,
   new_referrer, "consumer_accepts_old", base_inventory, head_inventory)` — the exact call the gate makes
   for every contract inside the closure — returns **`incompatible:narrowed_constraint`**. So there exists
   a contract-compatibility edit whose dependent breakage the gate does not report, of the same class
   issue #146 was filed for. `tests/test_architecture_fitness.py:4392`
   (`assertEqual(dependent_in_scope, expected_dependent)` with `expected_dependent=False` for the
   `CONTRACT-CLAIMANT` arm) pins it as intended behaviour, and
   `evidence/closure-fix-blast-radius.md:52-55` justifies the split with "for dependency identity the safe
   answer is 're-verify the contract the path names'" — measured false as a safety argument: path-first
   *substitutes*, it does not *add*. Fix: for reverse edges take the union of both candidate targets (path
   candidate **and** `$id` candidate) — that keeps FORBID-003 intact (the closure never becomes
   id-first-exclusive and the comparator is not moved) while removing the silent hole; otherwise restate
   the claim as a known residual and name it in `release.md`/PR description so the next reviewer is not
   told it is safe.

5. **The documented blast-radius consequence has no test — prose only.** Measured:
   `grep -rn "READY-BUNDLE|M7-SHADOW|M7-TASK-EVIDENCE|M7-PREDECESSOR|M7-OPERATOR-HANDOFF" tests/` → **no
   matches**; the only `unsupported compatibility semantics` assertion in the suite
   (`tests/test_architecture_fitness.py:4564`) belongs to the pre-existing aggregate-budget test. I
   independently reproduced the underlying facts on the declared inventory: identity verdicts
   `CONTRACT-FACTORY-M7-READY-BUNDLE-V1 → unsupported:unsupported_schema_keyword` and
   `CONTRACT-FACTORY-M7-OPERATOR-HANDOFF-V1 → unsupported:unsupported_schema_keyword`, identical at base
   and head, and the recovered pairs are exactly
   `{OPERATOR-HANDOFF→READY-BUNDLE, PREDECESSOR-BRIDGES→READY-BUNDLE, PREDECESSOR-BRIDGES→TASK-EVIDENCE,
   SHADOW-OUTCOME→SHADOW-COHORT, TASK-EVIDENCE→READY-BUNDLE}`. Assessment: prose is *partly* adequate —
   the mechanism (unsupported dependent → `unsupported compatibility semantics` → run fails) is covered by
   an existing test, and the fleet consequence is a *prediction* about future PRs, not a behaviour of this
   diff. What is not adequate is that the gate's *own* newly-restored edge set on the real inventory has
   zero pinning, so finding 3's class of regression (edges silently lost) cannot be caught for the shipped
   inventory at all. One cheap test that sweeps the declared inventory and asserts the recovered pair set
   (or at minimum that `SHADOW-OUTCOME → SHADOW-COHORT` and `TASK-EVIDENCE → READY-BUNDLE` are present)
   would close both.

6. **The mutation matrix exists only in chat.** Measured: `tasks.md:7` checks off "Mutation matrix M0–M8"
   and `implementation-plan.md:20` lists it as a deliverable, but `ls` of the change package shows only
   `closure-fix-blast-radius.md`, `controller-verification.md`, `README.md`, `sequencing-and-overlap.md`;
   `grep -rn "M0|M1|M7|mutation"` finds no per-arm table. `test-plan.md` P0 explicitly requires "mutation
   run in a throwaway clone, **results in `evidence/`**", and `controller-verification.md` §4 says
   "I did not re-run all nine arms". So the strongest verification claim in this wave was never recorded
   where the next agent can re-derive it. This file is currently the only matrix artifact in the tree.

7. **Two of the seven arms are non-discriminating for #146 and should not be counted as defect coverage.**
   Measured under M1 (fix reverted):
   `test_contract_compatibility_ignores_reference_without_declared_target` and
   `test_contract_compatibility_still_reports_referrer_with_undeclared_reference` both **PASS** on the
   broken tree. That is correct behaviour for guards, but only `..._of_every_reference_grammar`,
   `..._fails_closed_on_duplicate_declared_schema_id` and
   `..._shares_the_comparator_reference_grammar` actually fail when the closure is wrong.

## Minor (nice to have)

8. Arm counts in the matrix are loose (see the table in "What I measured"): M6 was claimed as "4 arms
   fail", measured 3 methods / 5 subtest arms; M5 claimed "4 arms ERROR", measured 2 methods / 3 subtest
   errors. No arm that was claimed to fail actually passed, so this is bookkeeping, not a false claim.
9. `tests/test_architecture_fitness.py:4420-4431` (spy arm): the guard keys on
   `keywords.get("precedence", "")`, so it locks the *call convention* as well as the value — a future
   refactor that passes `precedence` positionally reddens a green behaviour. Prefer
   `assertEqual({c.kwargs["precedence"] for c in mock.call_args_list}, {PATH_FIRST})` or read the
   recorded value out of a call object.
10. T1's `path with JSON pointer` grammar is synthetic-only on this fleet (measured: the declared
    contracts use `#/…`, `path`, `urn`, `urn#frag` — no `path#frag`). Fine as grammar coverage; worth one
    word in the test-plan so a reader does not think it mirrors a shipped edge.
11. `evidence/controller-verification.md:61` says "the **seven new** arms in `ArchitectureFitnessTests`".
    Measured: six new test methods (`git diff --numstat d871ea6..HEAD -- tests/` = 422 insertions,
    **0 deletions**; added `def test_` lines = 6) and the seventh listed name predates the change
    (`tests/test_architecture_fitness.py:3961` exists at base). FORBID-001 is respected — 0 deleted or
    weakened assertions measured.

## What I measured

Runs in a clean clone at `7d21d95` (`/tmp/qw146/clone1`):

| command | output |
| --- | --- |
| `python3 -m unittest -q tests.test_architecture_fitness` | `Ran 115 tests in 75.120s` / `OK` |
| `python3 -m unittest -q tests.test_architecture_model` | `Ran 79 tests in 1.947s` / `OK` |
| 7 closure arms, individually | all PASS (M0) |
| same 7 arms in a tree with foreign untracked files (`engineering/contracts/untracked-junk-zz.json`, `architecture/untracked-note.md`, `.grok-stack/runtime/active-route.json`), run twice | 7 PASS, 7 PASS — deterministic, no repo writes |

Test-hygiene scan of the added block (`git diff d871ea6..HEAD -- tests/ | grep "^+" | grep -E
"/tmp|grok-projects|os.environ|contract_inventory|load_architecture\(|ROOT|datetime|time\.|random|hostname"`)
→ **no matches**: the new arms build their inventories in `tempfile.TemporaryDirectory` git repos
(`GitArchitectureRepo`, `tests/test_architecture_fitness.py:40-42`), read no fleet state, freeze no count or
digest from `architecture/system.yaml`, and hardcode no host path. The issue-#60/PR-#115 pattern is absent
*in the new code*; the pre-existing
`test_added_landing_contracts_have_supported_closed_semantics` (`tests/test_architecture_fitness.py:4704`)
does freeze a 14-id fleet list and remains a standing reddening risk owned by an earlier wave, not this one.

Mutation arms, each in its own fresh clone of `7d21d95` with a single mutation applied (per-arm
"failing" counts give methods / subtest arms):

| arm | mutation (one edit unless noted) | methods failing | arms failing | matches their claim? |
| --- | --- | --- | --- | --- |
| M0 | none | 0 | 0 | yes |
| M1 | `git checkout d871ea6 -- architecture.py architecture_fitness.py` (full revert) | T1, T5, T6 | 5 + 1 error; full module `Ran 115 — FAILED (failures=5, errors=1)`, **all six inside the new arms, zero pre-existing failures**; plain-relative subtest + T7 stay green | **yes** — and it is the old-suite-blindness proof their `test-plan.md` P0 demands |
| M2 | `architecture_fitness.py` `reference_base, _fragment = schema_reference_parts(reference)` → `= reference, None` | T1, T5 | 2 + 1 = 3 arms ("2" under a method convention) | yes, counting-dependent |
| M3 | closure passes `{}` instead of `paths_by_schema_id` | T1, T5, T6 | 2 + 1 + 2 | yes ("2 arms + collision") |
| M4 | `architecture.py:1191` `if len(declared) != 1:` → `== 0` (ambiguous `$id` first-wins) | T6 | 1 (only `colliding=True`) — full module `FAILED (failures=1)`, so this is a **single-test lock** | yes |
| M5 | closure `elif failure not in SCHEMA_REFERENCE_UNRESOLVED: raise` → `else: raise` | T2, T3 | 3 subtest ERRORs (`ArchitectureError: undeclared schema reference`) — claimed "4 arms ERROR", **not reproduced** | direction yes, count no |
| M6 | closure passes `frozenset()` instead of `declared_paths` | T1, T4, T7 | 5 arms (2+2+1) / 3 methods — claimed "4", **neither convention reproduces 4** | direction yes, count no |
| M7 | `precedence=SCHEMA_REFERENCE_PATH_FIRST` → `"declared_id_first"` (`architecture_fitness.py:974`) | T4, T5 | both `issue_146` subtests + the spy guard, exactly as claimed | **yes** — anti-inheritance lock verified |
| M8 | replace the shared call with the pre-fix `posixpath.normpath(join(dirname, reference))` grammar (6 lines → 4) | T1, T2, T3, T5, T6 | 8 arms; full module `FAILED (failures=6, errors=2)` | yes ("6 arms" ≈ their failure count) |
| **M-S4 (mine)** | `architecture_fitness.py:916` `for inventory in (before, after):` → `(after,)` | **none** | **0 — `Ran 115 tests — OK`** | not in their matrix; harmful, see Important 3 |

Fleet re-derivations (base tree `/tmp/qw146/base` at `d871ea6` vs `/tmp/qw146/clone1` at `7d21d95`,
identical scripts, 50 declared records both):

| measurement | `d871ea6` | `7d21d95` |
| --- | --- | --- |
| `_contract_dependency_closure({t}, state, state)` target→dependent pairs, summed over all targets | **22** | **27** (0 lost, 5 gained — gained set = their table exactly) |
| direct reverse edges (no transitivity) | **10** | **17** |
| targets with ≥1 dependent / distinct dependents | 9 / 6 | 13 / 9 |
| comparator differential, 50 contracts × 9-10 edits × 3 policies = **1473 verdict lines** | — | **0 differing lines**, `unsupported` rows 415 = 415 |

The 1473-line differential is an independently larger version of their 555-line claim: **AC-006
"no comparator verdict changes" is confirmed**, including a `drop-id` edit and `anyOf`/`oneOf`/`enum`
composition edits. Supporting code reading (measured by `git show d871ea6:...architecture.py`): the new
`schema_reference_relative_path` guard list is byte-identical to the base `_relative_path` guard list, and
the base comparator already raised `"ambiguous declared schema id"` on a duplicated `$id` and already
resolved `$id`-before-path — so the refactor moved, not changed, comparator semantics.

Residual coverage vs the issue's own checklist (`gh issue view 146`, 7 `LOST` rows published, text claims
"9 of 19"): measured 4 of the 7 rows now produce a closure edge (rows 4-7). The other three
(`earned-autonomy → m7-autonomy-bridge`, `m7-autonomy-bridge → ready-for-pr-bundle`,
`m7-autonomy-bridge → shadow-cohort`) **still have no edge**, because
`factory/contracts/jsonschema/earned-autonomy.v1.schema.json` and
`m7-autonomy-bridge.v1.schema.json` are on disk but are not declared in `architecture/system.yaml`
(`grep -n "autonomy\|earned" architecture/system.yaml` → only two `factory/src/*.py` source entries), so
the gate cannot compare them at all. Measured and inferred as above; the change package never states that
3 of the issue's rows remain uncovered, and `test-plan.md`'s manual item ("confirm each of the 9 now
yields an edge") is unrecorded.

Also checked, no defect found (measured or reasoned as noted): a `$ref` that only differs by fragment
(duplicate edges dedupe via `references: set`); `#`-only and empty refs (skipped by
`not reference.startswith("#")` and `if reference_base:`, matching the comparator); non-dict `$id` values
(both sides guard with `isinstance(schema_id, str)`); self-edges (the real
`m7-predecessor-bridges` doc refs its own `$id`, and the BFS `if dependent not in closure` guard holds);
refs inside `$defs`/nested `allOf` (the walker descends dicts and lists, and the recovered fleet edges
include `$defs`-nested refs); `../` escapes and `%`-escaped refs (closure drops, comparator raises —
asymmetric but always fail-closed where it is compared); targets under `engineering/`/`pilot/` (no path
filter exists, probes used `engineering/` paths and worked); the `%`/NFC/IRI-scheme guards (identical at
base, and no test in `tests/test_architecture_model.py` mentions `unsafe schema reference`/
`escapes inventory` — a pre-existing gap, not this wave's).

## Verdict rationale

- **Not disproven, disproven-in-part, and confirmed, respectively.** Confirmed (measured): the seven arms
  assert the *observable* signal for AC-001/AC-004/AC-005 — dependent identity in
  `applicability.scanned_scope` plus its finding row (`tests/test_architecture_fitness.py:4207`,
  `:4520`) — not helper internals; the only internals assertion
  (`assertIs(FIT.schema_reference_target_path, ARCHITECTURE.schema_reference_target_path)`) is paired with
  a spy that proves a real `$id` ref travelled through it with path-first precedence, and M7 reddens it.
  The anti-inheritance lock and the old-suite-blindness claim both reproduce exactly. Comparator semantics
  are untouched on a larger differential than they ran.
- **FAIL is driven by evidence integrity, not by a product defect.** Critical 1 and 2 are false or
  unverifiable statements in the machine-readable spec and in `evidence/` of a repository whose entire
  product is fingerprint-bound verification claims; `AGENTS.md` makes `PROJECT_STATE.json`/change-spec the
  third source of truth, so a number that cannot be re-derived is a defect wherever it lives. Critical 2
  additionally means an AC is certified by a test that does not exercise it.
- **The two real coverage gaps** (Important 3, the untested `before`-inventory union; Important 4, the
  claimant-shadowing residual that a new test enshrines) are each fixable in one test plus one paragraph,
  and Important 3 is a demonstrated silent-loss-of-signal, which is the exact failure mode this wave was
  opened to eliminate.
- Nothing here implicates FORBID-001 (0 deleted/modified test lines, measured) or FORBID-002 (no contract,
  `architecture/system.yaml`, `rules.yaml`, or policy file in the diff, measured from `git diff --stat`).
- The scheduled `grok_verify.py --mode pr` run is unaffected by this review's conclusions, but note that
  any receipt bound to the current tree fingerprint goes stale the moment the Critical 1/2 spec edits land;
  re-take `verification`/`code_review`/`test_review`/`security_review` after those paperwork fixes.

**Top three findings**

1. `10 → 27` is not reproducible under the method its own evidence file prescribes — measured 22 → 27
   closure pairs (10 → 17 direct edges); the metric in `change-spec.yaml:155`/`:161` mixes definitions and
   overstates the widening (Critical 1).
2. A one-line mutation that drops the `before` inventory from the closure union
   (`architecture_fitness.py:916`) keeps **all 115 tests green** while silently removing a dependent's
   identity and verdict for a head commit that retracts an `$id` — the base∪head half of the new closure is
   unpinned (Important 3, measured).
3. The widened closure still misses a real edit: narrowing a contract whose `$id` shadows another
   contract's declared path breaks its referrer (`incompatible:narrowed_constraint` when the referrer is
   forced through the comparator) yet never re-verifies that referrer — and
   `tests/test_architecture_fitness.py:4392` asserts that drop as intended, while
   `closure-fix-blast-radius.md:52-55` calls path-first "the safe answer" (Important 4, measured).

## Re-review on 0ab702f

RE-REVIEW VERDICT: PASS

Re-measured independently in private clones under `/tmp/qw146r/` (`git clone --local`, one process per tree;
code bytes `30a07c6`, paperwork `0ab702f` — verified `git diff 30a07c6..HEAD -- .grok-stack/ tests/` empty, so
the later commits are package-only). No `grok_verify.py` run; the delivery worktree was untouched apart from
this appended section. `Ran 125 tests in 81.921s / OK` at `30a07c6` (fitness), `Ran 79 / OK` (model).

1. **Critical 1 (mixed-unit widening metric) — CLOSED.** Every published count now carries its unit and every
   one reproduces on the delivered bytes with one method in each tree: direct one-hop **incl.** self-edges
   10 → 17, direct **cross-contract** 10 → 14, transitive 22 → 27, lost 0, gained 5 (gained set identical to
   the five named in the matrix), targets-with-dependent/dependents 9/6 → 13/9, self pairs at head = 3.
   `objective.success_metric`, `SIG-001`, `release.md:21-22`, `brief.md:24`, `architecture.md:16-17`,
   `controller-verification.md` §4b and `closure-fix-blast-radius.md:14` all state the unit they mean; the
   "gains the dependent (three) vs gains a new failure (two)" split is defined in-file. No *number* splices
   conventions any more. Residual prose (non-blocking, fix before the PR text is copied):
   (a) `closure-fix-blast-radius.md:59` still says "the closure is path-first, because … the safe answer is
   're-verify the contract the path names'" — the sentence my Important 4 disproved, now contradicting the
   same file's table and the correct `INV-003`; (b) `tasks.md:5` "closure uses `PATH_FIRST`" and
   `implementation-plan.md:14` likewise; (c) the comparator differential is quoted as 555 (`SIG-002`,
   `release.md`, `rollback.md`), 1050 (`success_metric`, `residual-risks.md:11`) and 1473 (matrix §9) with no
   line saying which grid produced which (each does state "rows/lines", and 0-differing is true — my own
   1473-line differential is the §9 one); (d) matrix §11.4's "Still open" list is stale: AC-002/AC-003,
   `INV-003`, `FORBID-003` and the `tasks.md` arm count were all fixed after it was written at 07:12.
2. **Critical 2 / my Important 3 (surviving `(after,)` mutation) — CLOSED.** Re-ran my M-S4 both ways, full
   125-test module in its own clone each: `(after, True)` only → `FAILED (failures=2)`, killed by
   `test_contract_dependency_closure_keeps_base_only_reference_dependents` **and**
   `bounds_duplicate_declared_id_to_certified_state (arm='base-only collision')`; `(before, False)` only →
   `FAILED (failures=5)`, killed by `..._adds_head_only_reference_dependents` plus duplicate-`$id
   (colliding=True)` and 3 bounds arms. Both counts and arm names match the matrix U3/U4 rows, so those rows
   are reproducible, not inherited.
3. **Critical 3 / my Important 4 (path-first substituting) — CLOSED.** `_reference_identity_candidates` now
   loops both precedences and unions the candidates; comparator still `SCHEMA_REFERENCE_ID_FIRST`
   (`architecture.py:1409`). Re-ran my original Demo B1 (`$id: "dir/target.json"` on the claimant, referrer
   byte-identical) through `_contract_compatibility` on the delivered bytes: `status=fail`,
   `scope=[CONTRACT-CLAIMANT, CONTRACT-REFERRER]`, `findings=[CONTRACT-CLAIMANT: narrowed_constraint,
   CONTRACT-REFERRER: narrowed_constraint]` — and the forced-comparator value is
   `incompatible:narrowed_constraint`, so the reported row now equals the verdict the comparator computes.
   The escape my `:4392` citation pinned is reversed (that arm now asserts `changed_contract ∈ scope` **and**
   a `CONTRACT-REFERRER:` finding). FORBID-003 holds both directions, measured: collapsing the union to
   `(PATH_FIRST,)` → `FAILED (failures=2)` (`..._issue_146 (CONTRACT-CLAIMANT)` + the spy arm, = their U1 row);
   flipping the **comparator** to `PATH_FIRST` → `FAILED (failures=1)`, killed only by
   `..._issue_146 (CONTRACT-CLAIMANT)` (model suite stays green — so the comparator half has a single-test
   lock; the cited FORBID-003 evidence does fire, but only there).
4. **Reason-split class — CLOSED.** `SCHEMA_REFERENCE_UNRESOLVED = {NOT_A_PATH, ESCAPE, UNDECLARED}`;
   `SCHEMA_REFERENCE_UNSAFE` is outside it and is recovered through `schema_reference_identity_path`. My six
   shapes (`./x.json`, `a b.json`, `c+d.json`, `c%2Bd.json`, `urn:x:u`, `../outside/e.json`) gave
   **JSON-identical** scope/status/findings between `d871ea6` and `30a07c6` — the three declined spellings and
   the percent form keep their edge, the two controls keep having none. Merging `UNSAFE` back into the deny-list
   → `FAILED (failures=4)`: the named tripwire
   `test_reference_reasons_keep_declined_paths_apart_from_non_paths` plus all three spellings of
   `..._reverifies_declined_relative_path_referrers`.
5. **Bookkeeping — CLOSED except two nice-to-haves.** Arm counts: `tasks.md:6` says six new at first
   delivery / ten from this contour / 16 versus `d871ea6` — measured exactly 6, 10, 16 added `def test_` with
   **0** deleted (109 → 125 methods) ✓; matrix §7 and `controller-verification.md` §4 carry the same
   correction. Matrix: `evidence/mutation-matrix.md` exists, states the per-arm command, the copy-per-arm
   method, and per-arm killed lists; U3/U4/U1 rows reproduced exactly as quoted above. Superset claim:
   `test_real_contract_closure_supersets_legacy_fold_per_target` is real and asserts `assertEqual(lost, [])`
   **and** `assertGreater(len(gained), 0)`; I checked its in-test fold is not a strawman — re-derived on the
   delivered tree it gives 22 pairs **set-equal** to the real `d871ea6` closure. Fleet `M7-*` targets: still
   **prose-only** — `grep -rn "READY-BUNDLE|M7-SHADOW|TASK-EVIDENCE|PREDECESSOR|OPERATOR-HANDOFF" tests/` → 0
   matches — and the package claims exactly that (matrix §11.3, `residual-risks.md:7`), so the claim is
   accurate rather than aspirational. Still open nice-to-haves: my Minor 9 (spy still reads
   `keywords.get("precedence","")`, so a positional call would redden a green behaviour) and my Minor 10
   (nothing records that `path#/$defs` is synthetic-only: measured fleet spellings are 479 bare/`$id`+fragment,
   76 `urn`, 10 plain path, 0 repository-path+fragment).
6. **Coverage hunt — no survivor found.** Seven mutants beyond my first report, each in its own clone on the
   delivered bytes: `(after,)`, `(before,)`, union→`PATH_FIRST`-only, comparator→`PATH_FIRST`,
   `UNSAFE` re-merged, BFS transitivity removed (dependents not re-enqueued), ambiguous `$id` silently
   attaching all claimants. All seven die; the last two die by exactly **one** arm each
   (`test_real_contract_closure_supersets_legacy_fold_per_target` for transitivity;
   `..._issue_146 (CONTRACT-CLAIMANT)` for comparator precedence), so those two properties are single-test
   locks that would go blind if the fleet inventory lost its chains — worth a synthetic arm, not a blocker.
   Plainly: within the budget I could not make the suite stay green with the closure wrong.

**Receipt basis.** All three delivered Criticals are closed by measurement, the reason-split and both union
halves are falsified, and the remaining items are stale sentences inside `engineering/changes/…` plus two
nice-to-haves; none misstates a measurement, an AC's evidence, or a verdict. A `test_review` receipt bound to
this tree is honest. Any further tracked write re-stales it.
