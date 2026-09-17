PASS

# Test review round 3 — feat/record-omni-activation @ 3c379ca

Verdict: **PASS** for this records wave — the added loop really runs, really fails when the
property it claims to pin is falsified (11/11 targeted mutants killed), and the suite is green
(15 / 120 / 759 OK). It is **a partial** close of re-review finding 4's test leg: the omni
systemctl-block half is closed with real new detection power; the omni state↔dossier equality
half is verified still open (silent in the full 759-test suite), and the timestamp pin is weaker
than the package prose claims (it binds neither the systemd property name nor the unit).

All work happened in `/tmp` copies (`git archive HEAD | tar -x`, then `git init` + one `snapshot`
commit so `test_structure`'s `git ls-tree` check could pass). The worktree was never written to
(`git status --porcelain` empty before and after; verified below). `scripts/grok_verify.py` was
not run. No GitHub, service, or credential access.

## Execution

### 1. It runs — and it is not dead code

Target lines (`tests/test_project_state.py`, HEAD copy): new loop = **760–769**; pre-existing
loop = 747–759; the `adaptive_factory` import that breaks isolated runs = **770**.

SubTest-entry probe (monkeypatches `unittest.TestCase.subTest`, runs the one method):

```
$ python3 /tmp/r3-subtest-probe.py /tmp/r3-base
SUBTESTS ENTERED (in order):
   test_runtime_observations_are_source_bound_without_promoting_qualification {'role': 'primary'}
   ... {'role': 'secondary'}        # pre-existing loop
   ... {'role': 'primary'}
   ... {'role': 'secondary'}
   ... {'role': 'omni'}             # NEW loop: all three cases execute
total subTest entries: 5  (pre-existing loop=2, new loop=3, so 5 expected)
run: OK failures 0 errors 0
```

`-v` output of the method in a git-ful copy with `factory/src` importable (the loop passes):

```
$ PYTHONPATH=/tmp/r3-base/factory/src python3 -m unittest -v \
    tests.test_project_state.ProjectStateTests.test_runtime_observations_are_source_bound_without_promoting_qualification
... ok
Ran 1 test in 0.071s
OK
```

**Not runnable in isolation without a path side effect** — same as on `main` (verified on an
archive of `2f66ba6`, where the import sits at line 760; at HEAD it is line 770):

```
$ python3 -m unittest tests.test_project_state.ProjectStateTests.test_runtime_observations_...
  File ".../tests/test_project_state.py", line 770, in test_runtime_observations_are_source_bound...
    from adaptive_factory.landing_http import HttpLandingProfile
ModuleNotFoundError: No module named 'adaptive_factory'
FAILED (errors=1)
```

Order dependence demonstrated (the module's only `sys.path.insert(0, ROOT/"factory"/"src")` is
inside `test_m4_roadmap_matches_typed_state_machine_and_local_scope` at 796–798, which the
loader's alphabetical sort runs *before* `test_runtime_observations_…`):

```
runtime-first, then other methods  -> Ran 2 tests  FAILED (errors=1)
test_m4_roadmap first, then runtime -> Ran 2 tests  OK
```

Crucially the new loop sits **before** that import, so it is not gated by it — proof by mutant,
isolated, no `PYTHONPATH`:

```
$ cd /tmp/r3-M1c && python3 -m unittest -v tests.test_project_state.ProjectStateTests.test_runtime_observations_...
  ... (role='omni') ... FAIL          # line 769, the new loop
... ERROR                             # line 770, unrelated import
Ran 1 test in 0.005s
FAILED (failures=1, errors=1)
```

### 2. Suite health (serial, nothing else on the box)

```
$ python3 -m unittest tests.test_project_state
Ran 15 tests in 0.116s        OK      (wall 0.21s; 2nd pass 0.119s)

$ python3 -m unittest tests.test_project_state tests.test_change_spec tests.test_structure tests.test_manifest_package
Ran 120 tests in 10.748s      OK      (wall ~10.0s, twice: 10.09s / 9.93s)

per module:  test_project_state 15 OK 0.114s | test_change_spec 30 OK 0.151s
             test_structure 19 OK 0.364s     | test_manifest_package 56 OK 8.910s   (15+30+19+56 = 120)

$ python3 -m unittest discover -s tests -t .        # whole suite, pristine copy
Ran 759 tests in 402.809s     OK (skipped=1)       (wall 6m43s)
```

Matches `tasks.md` ("120 coupled tests OK") and `review-response.md` ("Ran 15 tests OK"). The
15/120/759 runs are order-dependent only in the pre-existing `sys.path` sense above (a whole
module or the 4-module set always passes; a lone method does not). No new order dependence
introduced by round 3. Hermeticity re-checked: no test invokes `systemctl`/`curl` — the only
hits are fixture strings in policy/hook tests
(`tests/test_policy_shell_targets.py:20,38`, `tests/test_workflow_artifacts_adversarial.py:106`),
so the wall-clock pin reads the checked-in capture, never the live host.

## Mutation matrix

Each mutant = its own copy + one surgical text edit (a helper aborts unless the pattern hits the
expected count, so a no-op cannot masquerade as "survived"). Control `CTL` (no edit) =
`Ran 15 tests … OK`, i.e. harness sound. `rc` is the unittest exit code. Assertion text is
verbatim, trimmed.

### Required matrix — every one KILLED

| # | Mutation | Result | Line | Reported assertion |
|---|---|---|---|---|
| M1a | `services.primary.active_enter_timestamp` 12:41:51→12:41:5**2** | **KILLED** `failures=1` | 769 | `(role='primary')` `AssertionError: '2026-09-14 12:41:52 UTC' not found in 'Restart=no\nMainPID=698333\n…` |
| M1b | `…secondary…` 08:05:29→08:05:2**0** | **KILLED** `failures=1` | 769 | `(role='secondary')` `AssertionError: '2026-09-15 08:05:20 UTC' not found in '…` |
| M1c | `…omni…` 23:33:33→23:33:3**4** | **KILLED** `failures=1` | 769 | `(role='omni')` `AssertionError: '2026-09-16 23:33:34 UTC' not found in '…` |
| M1e | `…omni…` shifted a whole hour (22:33:33, still valid UTC) | **KILLED** `failures=1` | 769 | `(role='omni')` `…'2026-09-16 22:33:33 UTC' not found in …` |
| M2a | dossier capture: omni `ActiveState=active`→`inactive` | **KILLED** `failures=1` | 765 | `(role='omni')` `AssertionError: 'Id=adaptive-l5-omni.service\nActiveState=active\nUnitFileState=enabled' not found in '…ActiveState=inactive…` |
| M2b | dossier capture: **drop the omni block** | **KILLED** `failures=1` | 765 | `(role='omni')` same `…not found in 'Restart=no\nMainPID=698333…` (capture now ends after grok) |
| M3a | drop `active_enter_timestamp` from **omni** | **KILLED** `errors=1` | 767 | `(role='omni')` `KeyError: 'active_enter_timestamp'` — reported *as a typed subtest*, so the role is named; it is an uncaught KeyError, not an assertion, but it is clear and the rest of the method still runs |
| M3b | drop it from **primary** | **KILLED** `errors=1` | 767 | `(role='primary')` `KeyError: 'active_enter_timestamp'` |
| M4 | reorder omni block: `UnitFileState` moved **after** `ActiveEnterTimestamp` (timestamp still matches) | **KILLED** `failures=1` | 765 | `AssertionError: 'Id=adaptive-l5-omni.service\nActiveState=active\nUnitFileState=enabled' not found in '…ActiveState=active\nActiveEnterTimestamp=Wed 2026-09-16 23:33:33 UTC\nUnitFileState=enabled…` → the adjacency claim is load-bearing, not decorative |
| M5 | `runtime_observations.evidence` → post-108 dossier (same `source_base`, 2-unit capture, no `ActiveEnterTimestamp` at all) | **KILLED** `failures=3` | 769, 769, 765 | `(role='primary')` `'2026-09-14 12:41:51 UTC' not found in 'MainPID=698333\nId=adaptive-l5.service\n…'`; `(role='secondary')` likewise; `(role='omni')` adjacency missing. Line 746 (`source_base`) did **not** fire, so the new loop alone catches the un-claim |
| M6 | capture: omni only `UnitFileState=disabled` | **KILLED** `failures=1` | 765 | `AssertionError: 'Id=adaptive-l5-omni.service\nActiveState=active\nUnitFileState=enabled' not found in '…UnitFileState=disabled…` |

### Extra mutants — where the pin stops working

| # | Mutation | Result | Evidence |
|---|---|---|---|
| **M7** | capture: omni `ActiveEnterTimestamp` → `Thu 2026-09-17 09:00:00 UTC`, `ExecMainStartTimestamp` untouched (state still says `23:33:33Z`) | **SURVIVED** `Ran 15 … OK` | `2026-09-16 23:33:33 UTC` still present via `ExecMainStartTimestamp` → the assert never binds the *property name* |
| **M9** | state: omni's stamp replaced by **primary's** (`2026-09-14T12:41:51Z`), capture untouched | **SURVIVED** `Ran 15 … OK` | substring matched inside a different unit's block → no unit↔timestamp binding |
| M10 | state omni stamp as `…T23:33:33+00:00` (offset instead of `Z`) | **KILLED** `failures=1` | line 768 `self.assertTrue(stamp.endswith("Z"))` → `AssertionError: False is not true` (uninformative message; format-sensitive) |
| **M11** | add a **fourth** service (`adaptive-l5-fourth.service`, `installed_sha` 40×0, stamp `2020-01-01T00:00:00Z`, profile/model consistent) | **SURVIVED** `Ran 120 … OK` | `services` = `['primary','secondary','omni','fourth']`; loop tuple is hardcoded, so a new executor is unpinned by construction |
| D1 | capture: **primary** `ActiveState` → `deactivating` | **KILLED** `failures=2` | one defect, two reports: line **757** *and* line **765** — the new loop's primary/secondary `assertIn` is a strict duplicate with zero independent power |
| S3 | **delete `services.omni` entirely** | **KILLED** `errors=1` | line 763 `KeyError: 'omni'` (outside the subTest, so untagged, and the method aborts) — **improvement** on the previous head, where this was silent |
| S7 | rename omni's `unit` in state | **KILLED** `failures=1` | `'Id=adaptive-l5-omni-x.service\n…' not found` — **improvement** (previous M12 unit-rename was silent) |
| S8 | omni `model` wrong | **KILLED** | `'qwen3.5-omni-plus-2025-01-01' != 'qwen3.5-omni-plus-2026-03-15'` (the `.values()` loop) |

### Silence re-derivation (coupled 4-module set; ★ = also run against the full 759-test suite)

| # | Mutation | Result |
|---|---|---|
| **S1** ★ | state omni `selected_profile` `qwen-omni-intl` → `qwen-omni` (mainland — same `model_id` in `HTTP_PROFILES`) | **SURVIVED** `Ran 120 … OK` / `Ran 759 … OK (skipped=1)` |
| S1d | same swap in the **dossier** | **SURVIVED** `Ran 120 … OK` |
| **S2** ★ | state `services.omni.acceptance.profile_digest` → 64×0 | **SURVIVED** `Ran 120 … OK` / `Ran 759 … OK` |
| S2d | dossier `omni.activation.profile_digest` → 64×0 | **SURVIVED** `Ran 120 … OK` |
| S2j | state omni `acceptance.job_id` → `bogus-job-id` | **SURVIVED** `Ran 120 … OK` |
| S2s | state omni `usage_input_units` 769 → 1 | **SURVIVED** `Ran 120 … OK` |
| **S11** ★ | dossier top-level `observed_at` re-dated alone (the exact N1 defect class) | **SURVIVED** `Ran 120 … OK` / `Ran 759 … OK` |
| S12 | state `runtime_observations.observed_at` changed alone | **SURVIVED** `Ran 120 … OK` |
| S9 | state omni `acceptance.live_url` `null` → `https://landing.example.invalid/x` | **SURVIVED** `Ran 120 … OK` |
| S3d | dossier `omni` block renamed to `omni_unused` (i.e. evidence un-claims its own omni record) | **SURVIVED** `Ran 120 … OK` |
| S4 | omni `live_enabled` → `false` | **SURVIVED** `Ran 120 … OK` |
| S5 | omni `installed_sha` → 40×0 | **SURVIVED** `Ran 120 … OK` |
| S6 | omni `active_state`→`inactive` + `unit_file_state`→`disabled` **in the state** | **SURVIVED** `Ran 120 … OK` |

Static corroboration (so the silences are structural, not sandbox artifacts):
`grep -rn omni tests/*.py` → exactly **one** hit (`test_project_state.py:762`, the new loop's
tuple);
`grep -rn "runtime_observations" tests/*.py` → only `test_project_state.py` 742/744/745;
`grep -rn service_observation tests/*.py` → only lines 758/766/769;
`grep -rn installed_sha tests/*.py` → only 751/753/775 (all primary/secondary). The two
git-object tests (`test_retained_33…`, `test_local_git_objects_corrobate…`) early-`return` in a
shallow copy but touch none of those keys.

## Test honesty / coupling design (judgement, not measurement)

1. **Duplication.** For `primary`/`secondary` the new `assertIn` (765–766) is the same predicate
   as 757–758 against the same string; D1 shows it double-reports. Only omni's adjacency check and
   the three timestamp checks are new. A reader counting "five subTests / three units pinned"
   over-reads the added power by 2/3 for the unit half. It does not *hide* a hole (nothing that
   was covered becomes uncovered), so this is a clarity issue, not a correctness one.
2. **Wall-clock coupling.** Asserting a boot timestamp against a *checked-in* capture makes the
   test a transcription checker, not a liveness checker: restarting a unit changes nothing in the
   repo, so the test stays green while the record silently goes stale (verified reasoning: no test
   shells out to `systemctl`). The break appears at the **next re-capture**, when the dossier and
   all three `PROJECT_STATE` stamps must be edited in lockstep — plus the format hair-trigger in
   M10 (`…+00:00`, the spelling the sibling key `acceptance_observed_at: "2026-09-14T03:31:08+00:00"`
   already uses in the same object, so the loop enforces a spelling the file itself does not
   follow). None of that is disclosed: greps for `restart`/`active_enter_timestamp` across
   `tasks.md`, `review-response.md`, `change-spec.yaml`, `test-plan.md`, `evidence/README.md`,
   `README.md`, `START_HERE.md` return only NRestarts/INV-002 prose — no mention of the test
   coupling. `test-plan.md` still describes only "three-service loop incl. omni model equality"
   and never mentions the added loop; `INV-001` calls it "one added assertion".
   The coupling itself is defensible for a records wave (it is the state↔evidence agreement the
   re-review wanted, and it is inside INV-002's "re-observation proves them equal" clause) — but
   its cost should be stated once, in the package.
3. **Sufficiency.** Re-review finding 4 asked for *either* the omni assertion *or* explicit
   scoping, and named two halves: "nothing pins the omni systemctl block **or** omni
   state↔dossier equality". Round 3 delivers the first (M1c/M2a/M2b/M4/M6/M5/S7/S3 all killed —
   genuinely new power versus `e7692fc0`) and openly defers the second. **Call it a partial
   close, not a closed leg.** The prior PASS stands on its own terms; this head strictly improves
   it, so the gate result is PASS.

## Findings

1. **SUGGESTION / high — the timestamp pin binds neither the systemd property nor the unit, so
   the defect class that FAILED round 2 is still undetectable.** `state.services.omni.active_enter_timestamp`
   is checked as a bare substring of the capture (`stamp[:-1] + " UTC"`). Scenario: an author
   records `ExecMainStartTimestamp` (or another unit's `ActiveEnterTimestamp`) into
   `active_enter_timestamp` — M7 and M9 both `Ran 15 … OK`. That is precisely round-2 finding 8
   ("`activated_at` was the probe time, not the activation time"), now unreproducible-but-green.
   `review-response.md`'s "pinned, not just asserted" is accurate for *absent* stamps and
   overstates for *misattributed* ones. Fix is one line:
   `self.assertIn("ActiveEnterTimestamp=" + <weekday-agnostic suffix>, evidence["service_observation"])`
   scoped to the block for that unit (split `service_observation` on `\n\n`, match `Id=<unit>` block).
2. **SUGGESTION / high — the deferred equality assert is a live falsifiable hole today.**
   `state.services.omni.acceptance` vs `evidence.omni.activation` agree on nothing that a test
   reads: S2/S2d/S2j/S2s/S9/S3d/S5/S4/S6/S1/S1d survive the coupled set, and the headline ones
   (S1 intl→mainland — the entire point of #86 — S2 digest, S11-adjacent observed_at) survive the
   **full 759-test suite**. A future edit can zero `profile_digest`, flip the profile to the
   mainland endpoint, or set `live_url` non-null and the record still ships green. The deferral is
   disclosed, so this is not a gate failure — but "closed the test leg" should not be claimed
   while it stands.
3. **SUGGESTION / medium — `observed_at` state↔evidence agreement is unpinned while the package
   claims it was pinned by this edit.** S11 (dossier-only re-date) and S12 (state-only re-date)
   both survive 120 and 759. N1 was a *round-3-introduced* defect that the same round's prose
   says is now pinned; only the values were fixed, not the invariant. One assert closes it:
   `self.assertEqual(runtime["observed_at"], evidence["observed_at"])`.
4. **SUGGESTION / medium — the loop's unit pin is redundant for two of three roles and
   hardcoded to three roles.** D1 double-reports (757 + 765). M11: a fourth executor added to
   `services` is invisible to the unit/timestamp pin because the tuple is literal
   `("primary","secondary","omni")`. Also `live_enabled` (asserted for primary/secondary at 759)
   and `assertIsNone(live_url)` (756) are *not* asserted for omni (S4, S9 survive). Prefer
   iterating `runtime["services"].items()` in a single merged loop — then a new unit cannot be
   added without being pinned, and the duplicate assert disappears.
5. **NICE TO HAVE — undisclosed brittleness + stale test-plan wording.** See "Test honesty" #2:
   M10's `False is not true` (no hint that it is a `Z`-suffix rule), the lockstep requirement on
   the next re-capture, `test-plan.md` not mentioning the added loop, `INV-001`'s "one added
   assertion" for 3 roles × 3 asserts, and the fact that the whole pin lives on a substring
   guarantee (`Id=`/`ActiveState=`/`UnitFileState=` adjacency) that systemd's print order provides
   today — M4 proves it fails if that order changes, so a future `systemctl show -p` field list
   edit becomes a test-edit, which is fine but should be written down.
6. **NICE TO HAVE — two misnamed claims about the deferred/renamed keys.** `review-response.md`
   proposes asserting `dossier.omni.acceptance`; the dossier key is `omni.activation`, so the
   follow-up as worded cannot be written against the real shape. The round-3 commit message says
   `activated_at` "becomes `active_enter_timestamp` on all three services", but `activated_at`
   exists nowhere in base `2f66ba6` (`git show 2f66ba6:PROJECT_STATE.json | grep -c activated_at`
   → 0) and nowhere at HEAD: for primary/secondary this is a new key, not a rename.
7. **NICE TO HAVE — pre-existing order dependence still makes the method non-runnable alone.**
   Verified identical on base (line 760) and HEAD (line 770); the loop runs before the import, so
   coverage is unaffected, but a reviewer running the single method sees an unrelated ERROR.
   Moving `sys.path.insert(0, str(ROOT/"factory"/"src"))` to the top of the method (as
   `test_m4_roadmap_…` already does at 796–798) costs one line.

Positive deltas proven this round (versus the `e7692fc0` map): omni's recorded boot stamp is now
state↔capture bound (M1c), omni's unit name is bound (S7), deleting `services.omni` is caught
(S3), dropping the omni capture block is caught (M2b), a stale evidence pointer is caught (M5,
which the old loops could not: line 746 passes because `source_base` is identical), and the
adjacency guarantee is exercised (M4/M6).

## Commands and evidence

```
# pristine snapshot + git-ful copy (never in the repo)
git -C /home/pall/grok-projects/adaptive-grok-build-omni-rec archive HEAD | tar -x -C /tmp/r3-base
cd /tmp/r3-base && git init -q . && git add -A && git commit -qm snapshot     # 179M, 336 .py

# control + module/coupled/whole-suite health (serial)
python3 -m unittest tests.test_project_state                       # Ran 15 OK
python3 -m unittest tests.test_project_state tests.test_change_spec tests.test_structure tests.test_manifest_package  # Ran 120 OK
python3 -m unittest discover -s tests -t .                         # Ran 759 OK (skipped=1), 402.809s

# execution proof
python3 /tmp/r3-subtest-probe.py /tmp/r3-base                      # 5 subTest entries: 2 old + 3 new

# one mutant per copy, guarded edits, module (or coupled set) run
printf '%s\n' M1a M1b M1c M1e M2a M2b M3a M3b M4 M5 M6 | xargs -P6 -I{} bash /tmp/r3-run.sh {}
printf '%s\n' M7 M9 M11 D1 S1 S1d S2 S2d S2j S2s S3 S3d S4 S5 S6 S7 S8 S9 S11 S12 \
  | xargs … bash /tmp/r3-run.sh {} tests.test_project_state tests.test_change_spec tests.test_structure tests.test_manifest_package
cd /tmp/r3-S1 && python3 -m unittest discover -s tests -t .        # ★ survivors re-run whole suite (S1/S2/S11)

# hermeticity / structural greps  (all in /tmp copies)
grep -rn omni tests/*.py ; grep -rn "runtime_observations\|service_observation\|installed_sha" tests/*.py
grep -rn "systemctl\|curl " tests/*.py                             # 0 / fixtures only
git -C /home/pall/grok-projects/adaptive-grok-build-omni-rec status --porcelain   # empty before/after
```

Artifacts kept: `/tmp/r3-logs/<mutant>.log` (full unittest output for all 33 runs),
`/tmp/r3-mutate.py` (guarded mutation table), `/tmp/r3-run.sh`, `/tmp/r3-subtest-probe.py`,
`/tmp/r3-base` (pristine git-ful snapshot). The per-mutant working copies were deleted after
measurement; every number above is reproducible with `bash /tmp/r3-run.sh <name> [modules…]`.

## Limits

- **Measured:** subTest execution, 32 mutants run one at a time — **16 KILLED / 16 SURVIVED**, plus
  a green no-op control (`CTL`), each with the exact assertion text above; 15/120/759 counts and
  timings (serial), isolation and order dependence at both HEAD and base, hermeticity greps
  (`grep -rn omni tests/*.py` → 1 hit, line 762; `grep -rn systemctl tests/*.py` → 0 hits),
  structural absence of consumers for `installed_sha`/`live_enabled`/`acceptance`/`observed_at` of
  omni, and `git show 2f66ba6:PROJECT_STATE.json | grep -c activated_at` → 0. The worktree is
  byte-clean before and after (`git status --porcelain | wc -l` → 0, HEAD `3c379ca…`).
- **Reasoned, not measured:** the restart/lockstep failure narrative (depends on how the next
  record wave edits the two files); the `HTTP_PROFILES` mainland/intl `model_id` equality that
  makes S1 silent (read from `factory/src/adaptive_factory/landing_http.py:60-63`); INV-002 clause
  reading.
- **Not done (out of scope / forbidden):** `scripts/grok_verify.py`, PR/receipt creation, anything
  against the live host (`systemctl`, sockets, journals), `.env`/`provider.conf`/`tokens/` reads,
  any write outside `/tmp`. I did **not** re-verify the dossier's live truth — the previous rounds
  did that by hand and it remains a reviewer-honesty property.
- **Sandbox caveats:** copies carry a synthetic single-commit history, so `test_retained_33…` and
  `test_local_git_objects_corrobate…` early-`return` (they assert nothing about
  `runtime_observations`; the 759-test runs were green in the same copies, so those skips are not
  masking any kill I reported). `test_manifest_package` dominates the coupled-set time and
  inflates under parallel load (11–24s vs 9.8s serial) — only the serial numbers above should be
  quoted.
- Mutants are one-at-a-time; no interaction effects probed. I did not enumerate every reachable
  mutation of the omni leaves (e.g. `usage_output_units`, `provider_requests`,
  `endpoint_health.*`, `pilot.*`, `incident.*`) — the previous map already showed those consumers
  absent and my structural greps corroborate it.

## Summary

The round-3 loop is real and worth the line it adds: it runs for all three roles, kills every
mutation of the property it names (wrong/missing/absent timestamp, falsified or dropped omni
capture block, broken field adjacency, `disabled` unit file state, stale evidence pointer, renamed
unit, deleted omni entry), and the suite is green at 15 / 120 / 759. Two claims around it are too
strong: the pin does not bind which systemd property or which unit a timestamp came from (M7, M9),
and it does not pin the `observed_at` agreement the response says it pins (S11, S12). The
qwen-omni-intl→qwen-omni swap and every `state.services.omni.acceptance` ↔ `omni.activation`
divergence remain silent in the **whole** suite, so the re-review's test leg is **partially**
closed — the systemctl-block half delivered, the state↔dossier equality half still owed (and now
explicitly scoped, which is the alternative the re-review accepted). Verdict **PASS**, contingent
on the package correcting "pinned, not just asserted" to "state→capture transcription for the
recorded boot stamp", disclosing the wall-clock/lockstep coupling, and keeping the follow-up wave
as a tracked item rather than a closed leg.
