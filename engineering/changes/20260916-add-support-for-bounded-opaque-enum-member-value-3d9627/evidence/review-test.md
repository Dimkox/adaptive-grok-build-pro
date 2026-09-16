PASS
Re-review of the remediated head. All four previously-surviving mutation arms (a)–(d) are now killed; the
remaining items are two narrow sub-branch gaps and documentation staleness, none blocking.

# Test re-review — comparator opaque enum members (#104 wave, head 7aa4c30)

Baseline under review: `feature/comparator-opaque-enum-members` @ `7aa4c301193ef870ffbe255547042867ef2d20a7`,
worktree clean (`git status --porcelain` → 0 lines). Prior FAIL was recorded against `3831e2e`
("4 of 5 requested mutants survive"); this pass verifies closure of that exact list and hunts regressions.
Method: read-only in the real repo; every mutation in a fresh private clone
`/tmp/c104-rereview.R9KSOb/repo` (parent dir mode **0700**, detached at the reviewed SHA, tracked tree
byte-identical to the source repo per `diff -r`). The real repo was never mutated; each mutant was restored
by full-file rewrite and re-asserted (`RESTORED_OK`, `git status` 0 dirty at every checkpoint). The clone was
deleted after the run.

## 1. Mutation battery, re-run against the CURRENT tests

Baseline in the clone: `Ran 179 tests ... OK` (model 69 / fitness 106 / subset 4).

| Arm | Mutant | Result | Killed by |
| --- | --- | --- | --- |
| **a** | `_valid_enum_member` body → unconditional `return True` | **KILLED** (was SURVIVED) | `test_valid_enum_member_bounds_hold_under_direct_programmatic_documents` |
| **b** | drop `isinstance(key, str)` in the dict branch | **KILLED** (was SURVIVED) | same direct test |
| **c** | drop the helper depth check (`if depth > MAX_DEPTH: return False`) | **KILLED** (was SURVIVED) | same direct test |
| **d** | drop budget consumption (resolver `consume()` **and** counter increment/check, None guards kept) | **KILLED** (was SURVIVED) | same direct test |
| **e** | revert the enum loop to scalar-only (the original bug) | **KILLED** (was killed before too) | `test_object_valued_enum_members_are_bounded_opaque_values_not_schemas` |

So the FAIL condition is met: **5/5 of the requested arms now kill the suite**, and the killer for (a)–(d) is
the newly added direct test, not the compare-path arms — exactly the mechanism remediation item #2 asked for.
The prior diagnosis still holds structurally (the compare-path adversarial arms other than `duplicate` are
resolved by `_bounded_json_document` preflight, which is strictly stronger than the helper), but the helper's
own return paths are no longer untested.

Extra arms run for confidence (all inside the clone, all restored):

| Extra arm | Mutant | Result |
| --- | --- | --- |
| d3 | drop **only** the counter increment + `> MAX_PARSED_NODES` check | **KILLED** — direct test (budget assert) |
| d4 | drop only the `counter is None → return False` guard | **KILLED** (as `ERROR:` TypeError) — direct test |
| a′ | helper → unconditional `return False` (accept-side control) | **KILLED** — both tests |
| j | duplicate-member check removed (`if encoded is None:`) | **KILLED** — `(member='duplicate member') 'compatible' != 'unsupported'` |
| h | enum members interpreted as subschemas (`elif not _unsupported_schema(item, resolver, current)`) | **KILLED** — enum test |
| k | **narrowest FORBID-001 hazard**: helper rejects any member dict containing a `$ref`/`const` key | **KILLED** — and only at the new inert assertion (see §3) |
| z | no-op replacement (harness sanity control) | survived (suite `OK`), as required |
| d2 | drop **only** the resolver-branch `consume()` (counter branch intact) | **SURVIVED the full trio** — see §7 Minor-1 |
| m | reject single-key `{"$ref": ...}` members only (public verdict flips `compatible`→`unsupported`) | **SURVIVED the full trio** — see §7 Minor-2 |

Coverage of the requested remediation list from `evidence/review-response.md`: item #1 (reason tuples) partial
— see §2; item #2 (discriminating helper test) **done and measured**; item #3 (`$ref`-in-member pin) **done**;
item #4 (counts, no fitness-as-AC-001 citation, in-method import) — import **done**, counts **re-staled**, see §5/§6.

## 2. Reason-tuple verification (asserted vs actually emitted)

Measured on the **unmutated** head by re-running the test's own document builders and `compare_contracts`
(`result.reasons` is a `tuple`, so `assertEqual(result.reasons, gate)` is type-correct, not list-vs-tuple luck):

| Arm | Asserted in test | Actually emitted by the code | Verdict |
| --- | --- | --- | --- |
| duplicate member | `('unsupported_schema_keyword',)` | `('unsupported_schema_keyword',)` | matches |
| non-finite member (NaN inside a member) | `('malformed_contract_document',)` | `('malformed_contract_document',)` | matches |
| non-string key member `{1: "x"}` | `('malformed_contract_document',)` | `('malformed_contract_document',)` | matches |
| over-deep member (`MAX_DEPTH+5` wrapping) | `('malformed_contract_document',)` | `('malformed_contract_document',)` | matches |
| budget arm (`MAX_PARSED_NODES=8`) | *no reason assertion* | `('malformed_contract_document',)` | unasserted — Minor-3 |
| added `$ref`/`const` member | `status == "compatible"`, unasserted reasons | `compatible`, `()` | matches |
| widened enum (`fact_a`→`fact_a`,`fact_b`) | `compatible` | `compatible`, `()` | matches |

No assertion names a reason the code does not emit. The three arms the prior review suspected of hiding behind
preflight are now pinned as `malformed_contract_document`, which is the honest gate — the helper is *not* what
rejects them, and the assertion documents that instead of obscuring it.

## 3. FORBID-001 `$ref`-in-member inertness arm

The added member is `{"$ref": "file:///etc/passwd", "x": [{"const": {"type": "string"}}]}` inside
`"profile": {"enum": [...]}`, compared `consumer_accepts_old`.

* Behaviour at head: `status=compatible`, `reasons=()` — no resolution attempt, no keyword validation, member
  accepted as opaque data and compared byte-exactly. Confirmed independently of the test.
* **The assertion is load-bearing, proven narrowly**: mutant **k** (helper rejects a member dict merely
  *containing* a `$ref`/`const` key, everything else intact) fails the suite at exactly one place —
  `tests/test_architecture_model.py:2027  self.assertEqual(inert_result.status, "compatible")` →
  `AssertionError: 'unsupported' != 'compatible'`. Nothing else in the module catches it, so this arm — not the
  pre-existing `compatible` arms — is what pins "a schema-looking key inside a member is data".
* Stronger `$ref` shapes verified behaviorally correct but **unpinned** (Minor-2): at head, a member that is
  the exact resolver-triggering single-key form also stays inert —
  `{"$ref": "#/properties/profile"}` → `compatible`; `{"$ref": "file:///etc/passwd"}` → `compatible`;
  `{"$ref": "../../factory/contracts/jsonschema/landing-attempt-status.v1.schema.json"}` → `compatible`.
  `_unsupported_schema` only attempts resolution when `len(schema) == 1`, and the shipped member carries two
  keys, so a future change that resolves/rejects *single-key* `$ref` members stays green (mutant **m** survived
  the whole trio). One extra member in the existing inert enum closes this; it needs no new document or arm.
* Control check on the prior "removing the assertion fails" reading: deleting an assertion cannot fail, so the
  discriminating test is the mutant above — that is the evidence reported here.

## 4. `_valid_schema_scalar` huge-int change (code-review Minor #3 fix)

Direct evaluation at head: `ARCH._valid_schema_scalar(10**400)` → **True** (and `-10**400` → True);
`float("nan")` → **False**; `float("inf")` → **False**; `float("-inf")` → **False**.

Differential probe against the base expression (`isinstance(v,(int,float)) and not bool and math.isfinite(v)`)
over `10**400, -10**400, 0, 1, -5, 2**53, nan, inf, -inf, 0.0, -0.0, 1.5, 1e308, True, False, None, '', 'x', [], {}, 10**6`:
the **only** divergent inputs are the two huge ints, where base **raised `OverflowError`** and head returns True.
Every float, bool, None, str and container verdict is identical → no float validation was loosened anywhere.
Confirmed the fix removes a real crash, not a hypothetical one: at base
`_unsupported_schema({"type":"number","const":10**400})` and `{"enum":[10**400]}` both raised
`OverflowError: int too large to convert to float`; both now return without raising.

Existing suites re-run as instructed: `tests.test_json_schema_subset` → `Ran 4 ... OK`, including
`test_scalar_union_pattern_length_enum_const_and_bounds_are_enforced`; the full trio → `Ran 179 ... OK`.
Accuracy note for the next reader: that subset test drives `tests/json_schema_subset.SubsetValidator`, a
separate test-side validator, and never enters `_valid_schema_scalar` — so it cannot regress from this change
and is not evidence for it. The analyzer-side call sites (line 1430 `const`, line 1450 enum items, line 1333
recursion) are covered by the model/fitness modules, which are green.

## 5. Counts and hermeticity

| Set | Ran | Result |
| --- | --- | --- |
| `tests.test_architecture_model` | 69 | OK |
| `tests.test_architecture_fitness` | 106 | OK |
| `tests.test_json_schema_subset` | 4 | OK |
| **plan trio at 7aa4c30** | **179** | OK |
| plan trio at 3831e2e (pre-remediation) | 178 | OK |
| plan trio at base fc8d9e6 | 177 | OK |

`python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness tests.test_json_schema_subset`
→ `Ran 179 tests in 72.1s / OK` (single command, verbatim from `test-plan.md`).

**178-at-head / 177-at-base verdict: half right, half wrong.** 177@base reproduces exactly; 178@head does **not**
— head is 179, because remediation commit `becd8f0` added a test method and the count was not re-synced.
`tasks.md` now claims "178 at head; 177 pre-change" (off by one at head), while `test-plan.md`'s P1 row and the
`change-spec.yaml` `success_metric` (which says the suites are green "on the frozen head") still read **177** —
i.e. the count fix touched only one of the three places that carry the number. See Minor-4.

Hermeticity: the in-method `from unittest import mock` is **gone** — `grep -n "import mock\|from unittest"`
returns only the file-level line 15, so the mock helper is imported once. The new/changed region
(lines 1999–2070) contains no `os.environ`, no `urllib`/`requests`/`http.client`/`socket`, no filesystem or
subprocess access — pure in-memory data. `mock.patch.object(ARCH, "MAX_PARSED_NODES", …)` is a context manager,
restored, and demonstrably effective (arms d3/d4 killed through it). `tests.test_architecture_model` +
`tests.test_json_schema_subset` pass under a scrubbed environment (`env -i PATH=/usr/bin:/bin HOME=/tmp/…`,
73 OK), and the model module is deterministic across three consecutive runs (69 OK, 1.8s). The only
`os.*`/`subprocess` uses in that file are pre-existing tempdir/symlink/mkfifo fixtures outside the changed
region, and its `urllib`/`socket`/`subprocess` hits are string literals in a forbidden-dependency assertion.
`tests.test_architecture_fitness` is untouched by this branch (its `SENTINEL` env use is pre-existing).
`ruff check` on both changed files → `All checks passed!`; repo-wide ruff reports 23 errors at head **and 23 at
base fc8d9e6** (pilot/, factory/tests/, delivery/, trust-ci/), so the branch adds no lint debt and `tasks.md`'s
"ruff clean" holds for the wave's own files.

## 6. Scope guard

`git diff fc8d9e6..HEAD --name-only` → 16 paths: `.grok-stack/adaptive_grok/architecture.py`,
`tests/test_architecture_model.py`, and 14 files under this change package. **Zero** `factory/contracts/**`
entries, **zero** `architecture/rules.yaml`, **zero** `architecture/system.yaml`.

* `git diff fc8d9e6..HEAD -- factory/contracts/` → empty (0 lines).
* Byte-identity confirmed three ways (base blob, head blob, worktree hash) for the two contracts the wave is
  forbidden to touch: `landing-backend-capability.v1.schema.json` `7e4f9a58…` at all three;
  `landing-attempt-status.v1.schema.json` `302f0c42…` at all three.
* The stray scratch commit is gone from history reachable by this head: `git merge-base --is-ancestor a490428
  HEAD` → false. The `reset --hard` reported in `review-response.md` **stuck**, and the tree is clean.

## 7. Remaining findings

Important: none. Nothing blocking; the FAIL criteria from the previous round are met and no regression was found.

* **Minor-1 (measurement gap, one-line fix).** Arm **d2** — deleting only the resolver-branch
  `if not resolver.consume(): return False` — survives all 179 tests, because every direct call in the new test
  passes `resolver=None`. The new test therefore pins the counter branch (which has no production caller) and
  leaves the *live* production branch of the same budget clause unasserted, so AC-001's "each node charged to the
  **resolver**/counter work budget" is only half guarded. Impact today is low and I verified why: for any
  document reachable from `compare_contracts`, `preflight_current()` (`_bounded_json_document`) already charges
  the shared `work_budget` for every node — ≥2 per dict entry — before the enum walk runs, so the helper's own
  resolver charge can never be the one that trips. It is defense-in-depth, not an observable bug. Fix, verified
  discriminating in the clone:
  `self.assertFalse(ARCH._valid_enum_member({"a": 1}, ARCH._SchemaResolver(rec, None, [ARCH.MAX_PARSED_NODES]), None))`
  — head returns `False`, mutant d2 returns `True`.
* **Minor-2 (FORBID-001 half-shape).** Arm **m**: a member that is the single-key form
  `{"$ref": "…"}` — the exact shape `_unsupported_schema` would try to resolve — is accepted at head but is in
  no test, so rejecting or resolving it flips a public verdict with a green suite. Add one such member to the
  existing `inert` enum (all three variants were measured `compatible`/`()` at head, so the addition passes).
* **Minor-3 (incomplete application of prior item #1).** The `MAX_PARSED_NODES=8` arm still asserts only
  `result.status`, no reason tuple, and it sits outside the `adversarial` tuple. Measured actual reason:
  `('malformed_contract_document',)` — the arm is caught by preflight, not by member accounting; asserting that
  makes it self-documenting instead of implying the helper rejected it.
* **Minor-4 (documentation accuracy, repeat class).** Head count is 179, not the claimed 178, and
  `test-plan.md`/`change-spec.yaml` still say 177 for a head run. Same stale-by-one defect the previous round
  flagged, re-introduced by the fix commit; the `178 at head; 177 pre-change` wording in `tasks.md` and the
  matching claim in `review-response.md` should become `179 at 7aa4c30; 178 at 3831e2e; 177 at base`.
* **Minor-5 (cosmetic).** `_valid_schema_scalar`'s new `if isinstance(value, bool): return False` is
  unreachable — bools are already returned True by the line above. Harmless, but it reads as if bool handling
  changed when it did not. Out of scope for this wave, and worth naming so the next reader does not re-chase it:
  the same `math.isfinite`-on-huge-int `OverflowError` the fix removed still exists at line 1470
  (`_NUMBER_KEYWORDS`, e.g. `{"minimum": 10**400}` → raises) — verified identical at base, so it is pre-existing,
  not introduced here.

## Limits

* Statement/branch inference comes only from the mutation battery itself, not from coverage percentages.
* Only the reachable public entry (`compare_contracts`) plus direct private-helper calls were analyzed; the
  counter-mode `_unsupported_schema` entry still has no production caller (unchanged from the prior round).
* `scripts/grok_verify.py --mode pr` was deliberately not executed — it writes receipts and belongs to the
  parent's evidence step.
