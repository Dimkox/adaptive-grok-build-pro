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
