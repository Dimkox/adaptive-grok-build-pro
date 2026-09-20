# Implementation arms — issue #147 (declared `$id` shadowing a relative-path reference)

Bound to: branch `fix/contract-reference-identity-precedence`, base `90078959ff816068af374ad42f4bb80fdbaec866`
(= `origin/main` at implementation time). Reproduction re-run against that exact HEAD before any edit.

```
$ python3 /tmp/idprec147/repro.py                     # before the change
shadow  : CompatibilityResult(status='compatible', reasons=())            <-- false certification
control : CompatibilityResult(status='incompatible', reasons=('narrowed_constraint',))
$ python3 /tmp/idprec147/repro.py                     # after the change
shadow  : CompatibilityResult(status='incompatible', reasons=('narrowed_constraint',))
control : CompatibilityResult(status='incompatible', reasons=('narrowed_constraint',))
```

## 1. The rule as implemented

`architecture.schema_reference_target_path` gained one caller policy value,
`SCHEMA_REFERENCE_PATH_FIRST_CLASH_IS_FATAL = "declared_path_first_clash_is_fatal"`
(the constant block is `.grok-stack/adaptive_grok/architecture.py:1182-1197`, the branch is
`:1361-1369`), and `_SchemaResolver.resolve` now uses it (`:1466-1476`). The comparator resolves a
non-local `$ref` base as:

1. fold the base onto the referrer's directory and ask whether the result is a **declared contract
   path**; if yes, that record wins;
2. otherwise consult the declared-`$id` table;
3. except that a base two or more contracts collide over is refused as
   `SCHEMA_REFERENCE_AMBIGUOUS` rather than resolved, so `#146`'s collision policy stays loud at the
   comparator itself instead of being hidden by the new precedence.

`SCHEMA_REFERENCE_PATH_FIRST` and `SCHEMA_REFERENCE_ID_FIRST` are unchanged and still exported; the
fitness closure keeps calling both and unioning the answers. Every case-table row below was
measured, not reasoned:

| inventory state for the base | `id_first` (HEAD before) | `path_first_clash_is_fatal` (delivered) |
| --- | --- | --- |
| `$id` unique hit **and** fold names a declared path | claimant | **path record** (the fix) |
| `$id` ambiguous (≥2 carriers) and fold names a declared path | refuse `ambiguous` | refuse `ambiguous` (unchanged) |
| `$id` unique hit, fold names no declared path (`urn:`/IRI/relative-looking) | claimant | claimant (unchanged) |
| no `$id`, fold names a declared path | path record | path record (unchanged) |
| no `$id`, fold misses / escapes / not-a-path | that refusal | same refusal |
| fold refused `SCHEMA_REFERENCE_UNSAFE` | `UNSAFE` | `UNSAFE` |

The only behavioural difference is row 1. The model guard in §3 removes the authoring that makes row
1 reachable at all; the precedence governs what happens when such an inventory is handed to
`compare_contracts` directly (as the repro does), because the comparator must never certify a
verdict it derived from a captor.

## 2. Sites changed

| file:line | change |
| --- | --- |
| `.grok-stack/adaptive_grok/architecture.py:655-689` | new `_require_no_schema_id_path_capture()` |
| `.grok-stack/adaptive_grok/architecture.py:716` | called from `contract_inventory()` before returning |
| `.grok-stack/adaptive_grok/architecture.py:1182-1197` | precedence comment rewritten + `SCHEMA_REFERENCE_PATH_FIRST_CLASH_IS_FATAL` |
| `.grok-stack/adaptive_grok/architecture.py:1330-1341` | `schema_reference_target_path` docstring: comparator precedence claim |
| `.grok-stack/adaptive_grok/architecture.py:1361-1369` | new precedence branch with the clash refusal |
| `.grok-stack/adaptive_grok/architecture.py:1466-1476` | `_SchemaResolver.resolve` call site (was `SCHEMA_REFERENCE_ID_FIRST`) |
| `.grok-stack/adaptive_grok/architecture_fitness.py:1048-1054` | docstring only: the falsified "comparator resolves `$id` first (issue #147)" claim |
| `.grok-stack/adaptive_grok/architecture_fitness.py:1142-1151` | docstring only: the falsified "comparator … stays `$id`-first (FORBID-003…)" claim |
| `tests/test_architecture_model.py:3845-4165` | 5 new arms + 1 record helper, append-only |

`git diff --numstat`:

```
78  11  .grok-stack/adaptive_grok/architecture.py
12  5   .grok-stack/adaptive_grok/architecture_fitness.py
322 0   tests/test_architecture_model.py
```

`architecture_fitness.py` is **docstring-only**, proved by comparing the module AST with docstring
constants blanked against `git show HEAD:` of the same file:

```
architecture_fitness executable-AST identical ignoring docstrings: True
architecture.py executable-AST identical ignoring docstrings: False        # the fix itself
```

## 3. The model-level rejection

`contract_inventory()` (the only place the model's contract *documents* are read, and therefore the
only place a declared path and a declared `$id` can be compared) now refuses an `$id` that equals
another contract's declared path:

```
contract CONTRACT-CLAIMANT: ambiguous declared schema id 'engineering/contracts/dir/target.json'
declared by engineering/contracts/other/claimant.json shadows the declared path of contract
CONTRACT-TARGET
```

`ArchitectureError(code="contract")`, wording follows the comparator's own
`ambiguous declared schema id` precedent, and names the offending text plus both carrying paths. A
contract whose `$id` names **its own** path is self-identification and is skipped. Both edges of that
rule are arm-pinned (§4, arms 4–5) and both are mutation-killed (m4, m5 in §5).

This is a *model-build* rejection: it fires in `contract_inventory`, not in `_SchemaResolver`, so a
direct `compare_contracts` call over a hand-built inventory (the repro) still gets a true verdict
instead of a refusal. That is deliberate — rejecting there would have turned Done-when 1's
`incompatible ('narrowed_constraint',)` into `unsupported`.

## 4. Delivered arms (`tests/test_architecture_model.py`)

Status of each new arm run **against the pre-change tree** (`git archive HEAD` + the same test file):

| # | arm | on pre-change tree | what it pins |
| --- | --- | --- | --- |
| 1 | `test_path_naming_reference_resolves_to_the_declared_path_not_a_shadowing_id` | **FAIL** | the issue's repro: shadowing pair → `incompatible ('narrowed_constraint',)`; the control pair unchanged; the claimant is no longer the referrer's dependency (it can move freely → `compatible`); the "both tables resolve and must agree" case (target self-identifies with the base) → same true verdict |
| 2 | `test_path_naming_reference_with_a_colliding_declared_id_still_fails_closed` | pass (preservation) | `#146` collision policy unchanged: pinned `unsupported ('unsupported_schema_keyword',)` for a base two claimants collide over — the exact tuple measured on the pre-change tree |
| 3 | `test_reference_that_names_no_declared_path_still_resolves_through_the_id_table` | pass (preservation) | the `#133` feature: `urn:` IRI, `https:` IRI, **and a relative-looking `$id` whose fold names no declared path** all still resolve through the `$id` table and still report `narrowed_constraint` |
| 4 | `test_model_rejects_a_declared_schema_id_that_is_another_contract_path` | **FAIL** | §3's rejection: code, the named `$id`, both paths, the carrier's contract id — plus the self-`$id` exemption loads |
| 5 | `test_declared_inventory_carries_no_schema_id_path_collision` | pass (tripwire) | shipped inventory stays collision-free so the guard cannot be the reason a real PR fails: 50 records, 41 distinct `$id`, 0 duplicates, 0 `$id`-equals-another-path, and the `(path-naming, id-only, claimed-by-both)` split `= (10, 76, 0)` over 86 non-local `$ref` occurrences |

Arm 3's third shape is the one that separates "names a declared path" (a look-up, as the issue
requires) from "looks like a path" (a grammar test): see mutant m2.

Fleet result on the real worktree after the change:

```
$ python3 -m unittest -q tests.test_architecture_fitness tests.test_architecture_model tests.test_governance_fitness
Ran 219 tests in 91.134s
FAILED (failures=1)      # the pre-existing #149 arm, see §6 — left red, not edited
$ python3 -m unittest -q tests.test_structure
Ran 19 tests in 0.374s
OK
$ ruff check .grok-stack/adaptive_grok/ tests/          → All checks passed!
$ git diff --check                                     → clean
```

## 5. Mutation battery

Each mutant is a complete copy of the patched tree (`.git` excluded) with one exact string
replacement in the product code; all four modules run in each copy, so counts are comparable
tree-to-tree. `tests.test_structure::test_repository_root_holds_only_canonical_entries` is red in
every copy including the baseline (a copy artifact: no git metadata in the copy) and is green in the
real worktree; it is noise on every row, including baseline.

| mutant | patch | model | fitness | structure | governance | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | none | **OK** (84) | 1 red (§6) | copy-noise | OK | reference |
| m1 `id_first_revert` | resolve with `SCHEMA_REFERENCE_ID_FIRST` again | 1 red: **arm 1** | **OK** (125) | copy-noise | OK | **killed — and the only mutant that greens the #149 arm** |
| m2 `grammar_based` | consult `$id` only when the base is not path-like *by grammar* | 2 red: **arms 2, 3** | 1 red: §6 arm | copy-noise | OK | **killed** |
| m3 `plain_path_first` | drop the clash refusal (pure `PATH_FIRST`) | 1 red: **arm 2** | 1 red: §6 arm | copy-noise | OK | **killed** |
| m4 `no_model_guard` | `_require_no_schema_id_path_capture(records)` → `pass` | 1 red: **arm 4** | 1 red: §6 arm | copy-noise | OK | **killed** |
| m5 `guard_rejects_self_id` | remove the self-`$id` exemption | 1 error: **arm 4** | 1 red: §6 arm | copy-noise | OK | **killed** (no shipped contract self-declares, so only arm 4 sees it) |
| m6 `closure_union_path_only` | closure loops `PATH_FIRST` only | OK | 2 red: `shares_the_comparator_reference_grammar` + §6 arm | copy-noise | OK | **killed** (see §5.1) |
| m7 `closure_union_id_only` | closure loops `ID_FIRST` only (the pre-#146 shape) | OK | 3 red + 1 error: adds `attaches_named_path_despite_ambiguous_ids` | copy-noise | OK | **killed** |

m1 is the claim that makes this fix real: reverting the precedence reddens the shadowing arm, and it
is also the *only* tree in which the pre-existing `#149` arm is green again — which proves the two
arms are in direct opposition and cannot both hold on any tree (§6).

### 5.1 Is the `#149` closure union now redundant, or still load-bearing? — measured

`/tmp/idprec147/probe_union.py`, run in the `baseline` and `m6`/`m7` copies (identical comparator
code in all three; only the closure rule differs).

Reverse-dependency map for a referrer whose `$ref` base `dir/target.json` names the declared path
`engineering/contracts/dir/target.json` *and* is declared as `$id` by a claimant:

| tree | 1 claimant | 2 colliding claimants |
| --- | --- | --- |
| baseline (union) | `{CLAIMANT-0: [REFERRER], TARGET: [REFERRER]}` | `{TARGET: [REFERRER]}` + unattributed signal on `REFERRER` |
| m6 (path-only) | `{TARGET: [REFERRER]}` — **claimant edge lost** | `{TARGET: [REFERRER]}` — **signal lost** |
| m7 (`$id`-only) | `{CLAIMANT-0: [REFERRER]}` — **path edge lost** | `{}` + **run aborts** (`ambiguous declared schema id`) |

Gate scope/verdict effects in the same probe (baseline vs m6):

* claimant narrowed → baseline `scope=[CLAIMANT-0, REFERRER]`, m6 `scope=[CLAIMANT-0]`: the referrer
  silently leaves the re-verified set.
* two claimants collide, target narrowed → baseline emits
  `CONTRACT-REFERRER: unattributed reference: ambiguous declared schema id …`, m6 emits nothing.
* target narrowed, one claimant → baseline emits **`CONTRACT-REFERRER: narrowed_constraint`** (this
  is the #147 defect surfacing at the gate); before the fix that row was `compatible`.

Answer: **still load-bearing, but its stated reason changed.** The union is what keeps the
claimant→referrer edge and the collision signal; collapsing it (m6) removes both, which is a
reportable-information loss and is caught by `shares_the_comparator_reference_grammar`. What is *no
longer* true is the `#149` docstring's justification that the `$id` candidate is needed because "the
comparator computes the referrer's verdict from that claimant's document" — for a base that names a
declared path it no longer does, so the `#id` candidate is now verdict-redundant and
edge/scope/signal-load-bearing. Those two sentences are the only thing updated in
`architecture_fitness.py`; no arm, invariant or executable line there was weakened, and m7 (the
opposite substitution) is still killed by the existing arms.

## 6. One pre-existing assertion is falsified — left failing, not edited

```
FAIL: tests.test_architecture_fitness (…::test_contract_dependency_closure_uses_declared_path_precedence_issue_146)
      (changed_contract='CONTRACT-CLAIMANT')
tests/test_architecture_fitness.py:4411  self.assertTrue(any(f.startswith("CONTRACT-REFERRER:") …))
AssertionError: False is not true : ('CONTRACT-CLAIMANT: narrowed_constraint',)
```

The arm is the one already-merged `#149` delivered; its extra assertion reads
"the comparator resolves the referrer's `$ref` through the claimant's `$id`, so re-verifying the
referrer reports the claimant's narrowing instead of passing it" (docstring at
`tests/test_architecture_fitness.py:4317-4326`, assertion at `:4405-4415`). That sentence asserts
`$id`-first resolution, which is precisely the behaviour issue #147 calls a defect.

What still holds in that arm, measured: the scope assertion `== {CONTRACT-CLAIMANT,
CONTRACT-REFERRER}` **passes** (the union still re-verifies the referrer), `status == "fail"`
**passes**, and `CONTRACT-CLAIMANT: narrowed_constraint` is still reported — the gate does not pass.
Only the *attribution* changed: the referrer row is now `compatible` because the claimant is no
longer its dependency.

Per instructions the test file was not touched (`git diff --numstat -- tests/` = `322 0`), so this
arm is red on the delivered tree. The controller's options, in order of what the evidence supports:
(a) amend that one `if changed_contract == "CONTRACT-CLAIMANT":` block to assert the corrected
attribution (`CONTRACT-CLAIMANT: narrowed_constraint` reported, referrer re-verified but compatible)
and fix the two sentences of its docstring — the union invariant and every other assertion survive;
or (b) keep `#147` unfixed. m1 proves no third tree satisfies both. Related stale text a reviewer
will hit: the merged `#146` package's typed `AC-006` ("the comparator keeps declared-$id-first
resolution so issue #147 behaviour is untouched") and `INV-003`'s trailing clause ("stays
declared-$id-first there") are now falsified about the comparator; both live in
`engineering/changes/20260919-fix-issue-146-…/change-spec.yaml`, which is outside this task's write
scope, and `FORBID-003` there remains literally satisfied because it forbade the move only "in this
change".

## 7. Differential and fleet measurements (commands are in `/tmp/idprec147/`: `differential.py`,
`diff_rows.py`, `mutations.py`, `probe_union.py`)

`differential.py` loads the declared inventory with `ARCH.load_architecture` +
`ARCH.contract_inventory` (50 records) and emits one row per (suite, subject, perturbation, policy
mode), status + reason tuple:

* suites — `identity` (200), `self_edit` (1,728), `cross_edit` (23,400: each of the 13 declared
  reference targets perturbed, every one of the 50 records then re-compared against the perturbed
  inventory);
* perturbations — `dropped_property`, `description_edit`, `added_required`,
  `anyOf_novel_branch`, `anyOf_subsuming_branch`, `oneOf_*`, `allOf_*` (9 where applicable);
* policy modes — `bidirectional`, `consumer_accepts_old`, `producer_accepted_by_old`, and the fourth
  declared mode `exact` (6,332 rows each).

```
$ python3 differential.py <before/.grok-stack> before.jsonl && python3 differential.py <after/.grok-stack> after.jsonl
$ python3 diff_rows.py before.jsonl after.jsonl
rows: 25328 vs 25328
shared rows: 25328, differing rows: 0                     # zero, in every suite and every mode
```

Contradictory control (a differential that cannot fail proves nothing): the same harness with
`IDPREC_COLLIDE=1` injects, for every path-naming base, a record at an unrelated path declaring that
base as its `$id` and carrying a frozen copy of the real target's document.

```
injected capture claimants: 9 ; rows: 49016 vs 49016 ; differing rows: 1178   (all in cross_edit)
589  real target perturbed   compatible -> incompatible/unsupported   (the false certifications the fix removes)
589  claimant perturbed      incompatible/unsupported -> compatible   (the claimant is no longer the dependency)
```

so the harness does detect a resolution-precedence change, and the shipped inventory's 0 differing
rows means "nothing is shadowing here", not "the measurement is dead".

**Fleet-level effect: none.** Zero declared-contract verdicts change (0/25,328); the fitness
closure's executable code is byte-for-byte equivalent (§2's AST check); declared inventory and
architecture digests are unchanged (`tests.test_structure`, 19 tests OK, holds the frozen digests);
the one fleet red is a synthetic in-memory fixture, not a declared contract.

## 8. Deliberately left undone

* `tests/test_architecture_fitness.py` untouched, so the `#149` attribution assertion stays red
  (see §6). Not "simplified", not deleted, not marked expected-failure.
* `engineering/changes/20260919-fix-issue-146-…/change-spec.yaml` (`AC-006`, `INV-003` comparator
  clauses) not amended — outside this task's write scope; §6 records what needs the amendment.
* No `grok_verify.py --mode pr` run, no receipts, no commit, no push: those bind to a final tree and
  belong to the controller. The tree is still dirty with this report pending.
* The model guard checks **exact text equality** between a declared `$id` and another contract's
  declared path (the issue's wording). It does not reject a *relative* `$id` such as
  `"dir/target.json"` that captures a referrer after folding — `#149`'s own fixture authors exactly
  that, so rejecting it would be a policy decision beyond this budget. The precedence covers it for
  the comparator; the residual is §9.
* `architecture/rules.yaml`, `architecture/system.yaml`, all contract documents, producer-output
  semantics and every policy mode: untouched. No new or removed reason tuple on a correctly-declared
  inventory (measured §7).

## 9. Attack this first

The inverse hazard the parent named is real and **not** closed by this change, by design: with
path-first, a contract at `p/other.json` that declares `$id: "a.json"` while a *different* contract
sits at the referrer's folded `a.json` no longer reaches the claimant, so a legitimate `$id`
dependency can be de-scoped from the referrer's verdict (measured: 589 such rows flip to
`compatible` in the collision control). It is safe today only because the shipped inventory has
`(path-naming ∧ claimed-by-both) = 0` (arm 5) and because the model guard rejects the exact-text form
of the collision. Two things a reviewer should try to break, with the arms they should expect to
fire:

1. Author a *relative-looking* `$id` (the `#149` fixture's shape, which the guard deliberately does
   not reject) and look for a narrowing of the claimant that the gate now reports **only** on the
   claimant's own row — i.e. is `CONTRACT-CLAIMANT: narrowed_constraint` always a sufficient
   substitute for the referrer row, or is there a kind/policy combination (no matching
   `contract_policies` entry for the claimant's `kind`, an added or removed claimant) where the
   referrer's verdict used to be the only place the change surfaced? `role`/`kind` are inventory
   fields, so a claimant whose kind has no policy lands in `unsupported: no compatibility policy`
   rather than a finding — worth confirming that is loud enough.
2. Try to make the clash refusal over-refuse: any shape where `paths_by_schema_id[base]` has ≥2
   entries *for a base the comparator need not consult* (e.g. the referrer never reaches it) now
   yields `unsupported` where the pre-fix tree yielded a verdict. Arm 2 pins the intended case;
   m3/m2 prove it is not vacuous.
