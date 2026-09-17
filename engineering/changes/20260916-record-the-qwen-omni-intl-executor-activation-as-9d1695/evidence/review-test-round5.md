PASS

# Round-5 delta test review — 6633e32

Object: worktree `/home/pall/grok-projects/adaptive-grok-build-omni-rec`, HEAD `6633e32` ("fix(delivery): point the routing base at the commit the wave sits on"), parent `35d44e6`, base `2f66ba6`.
Delta under review (measured, `git diff --numstat 35d44e6..6633e32`): 3 files — `tests/test_project_state.py` (`6 0`: 4 comment lines at :821-824, the `TERMINAL_STATES` import at :825, one `assertNotIn` at :826), the package `route.json` (`base_commit` `05b69c7…` → `2f66ba6…`, 1 line), and `evidence/review-response.md` (the F5 row rewritten, 1 line). Worktree tracked-clean before and after.
Method: one mutant per hard-link copy of a `git archive 6633e32` snapshot under `/tmp/rec5/m/` (snapshot built with `git init -q . && git add -A && git commit -qm snapshot` so `test_structure` can run); nothing was ever written to a repo. Every mutant is guarded twice — the edit must produce a non-empty unified diff on at least one declared file, and an empty diff raises `NO-OP MUTATION (guard tripped)`: **0 guard trips across 51 mutants**, so no no-op masqueraded as a survivor. Gate = `python3 -m unittest tests.test_project_state`; a test method stops at its first failed assert, so the quoted assertion is the one that actually fired first. Totals: battery 1 = 32 mutants (15 KILLED / 17 SURVIVED), battery 2 = 19 mutants (15 KILLED / 4 SURVIVED). `control5 integrity: CLEAN`.

Provenance note (not a re-adjudication): the round-4 deliverable `/tmp/rec-delta-test.md` was never written to disk — that review was interrupted after its battery and delivered only as a message. Where this report refers to "my round-4 finding 3 / finding 4", they are mapped by content to the round-4 artifact IDs I measured (`/tmp/rec-mut/results.txt`: 76 mutants, 47 KILLED / 29 SURVIVED, 0 guard trips) and **every one of them was re-executed at `6633e32`** below (R13/R20–R32, T02–T11), so no verdict here rests on a number carried over from an older head.

## 1. Kill matrix — the new guard (battery 1, 32 mutants)

| # | Mutant (one per copy) | Verdict | Assertion that fired (verbatim) |
| --- | --- | --- | --- |
| R00 | green no-op control (copy, zero edits) | **GREEN** | `Ran 15 tests in 0.159s / OK` |
| R01 | `omni.acceptance.state` **and** dossier `activation.state` → `artifact_ready` | KILLED | `:826 AssertionError: 'artifact_ready' unexpectedly found in frozenset({'needs_human', 'artifact_ready', 'cancelled', 'provider_unavailable', 'rejected'})` — `FAILED (failures=1)`; the leaf-equality assert at :819 passed (both files edited in step), so the kill is attributable to the new guard alone |
| R02 | both leaves → `needs_human` | KILLED | `:826 AssertionError: 'needs_human' unexpectedly found in frozenset({…})` |
| R03 | both leaves → `rejected` | KILLED | `:826 AssertionError: 'rejected' unexpectedly found in frozenset({…})` |
| R04 | both leaves → `provider_unavailable` | KILLED | `:826 AssertionError: 'provider_unavailable' unexpectedly found in frozenset({…})` |
| R05 | both leaves → `cancelled` | KILLED | `:826 AssertionError: 'cancelled' unexpectedly found in frozenset({…})` |
| R06 | state leaf only → `artifact_ready` | KILLED | `:819 AssertionError: {'job_id': 'omni-activate-20260916-e7d0f72b[225 chars]None} != {'http_status': 200, …}` (leaf equality; the guard is never reached) |
| R07 | dossier leaf only → `artifact_ready` | KILLED | `:819 AssertionError: {…[221 chars]None} != {'http_status': 200, 'job_id': 'omni-activa[225 chars] 191}` |
| R08 | state leaf only → `needs_human` | KILLED | `:819` dict-equality (as R06) |
| R09 | dossier leaf only → `needs_human` | KILLED | `:819` dict-equality |
| R10 | state leaf only → `rejected` | KILLED | `:819` dict-equality |
| R11 | dossier leaf only → `rejected` | KILLED | `:819` dict-equality |
| R12 | pilot block semantically untouched (prose sentence appended to `pilot.note`); `pilot.state`/`db_row.state` left `artifact_ready` | **SURVIVED (legitimate)** | `Ran 15 OK` — the legitimate terminal pilot value does not trip the guard |
| R13 | `pilot.state` **and** `db_row.state` → `rejected` (pair consistent) | **SURVIVED** | green; 759 OK suite-wide (§4) |
| R14 | `pilot.state` alone → `rejected` (`db_row.state` kept) | KILLED | `:806 AssertionError: 'rejected' != 'artifact_ready'` (pilot↔row equality) |
| R15 | `primary.acceptance.state` → `rejected` | KILLED | `:755 AssertionError: 'rejected' != 'artifact_ready'` (base-era literal pin — it pins a *terminal* value) |
| R16 | `secondary.acceptance.state` → `needs_human` | KILLED | `:755 AssertionError: 'needs_human' != 'artifact_ready'` (same pin, `role=secondary` subTest) |
| R17 | both omni leaves → `normalizing` (real job state, non-terminal) | **SURVIVED** | green |
| R18 | both omni leaves → `succeeded` (invented label) | **SURVIVED** | green; 759 OK suite-wide (§4) |
| R19 | both omni leaves → `Normalized` (case variant of the recorded value) | **SURVIVED** | green |
| R20 | append a contradictory second omni block to `service_observation` | **SURVIVED** | green |
| R21 | all three `observed_at` moved consistently inside 2026-09-17 | **SURVIVED** | green |
| R22 | `qwen-omni-intl` → `qwen-omni` in **both** files | **SURVIVED** | green; 759 OK suite-wide (§4) |
| R23 | omni `installed_sha` → 40 zeros in **both** files | **SURVIVED** | green; 759 OK suite-wide (§4) |
| R24 | omni `ExecMainStartTimestamp` changed alone inside the capture | **SURVIVED** | green |
| R25 | omni `NRestarts=0` → 9 inside the capture | **SURVIVED** | green |
| R26 | `activation.endpoint_health.live` 200 → 503 | **SURVIVED** | green |
| R27 | `incident.clean_start` rewritten (the value that narrates the omni boot stamp) | **SURVIVED** | green |
| R28 | `limits[]`: the "No external maintainer-accepted pilot" line deleted | **SURVIVED** | green |
| R29 | dossier `omni` gains `activation_copy` (a full duplicate activation block) | **SURVIVED** | green |
| R30 | `route.json.base_commit` reverted to the stale `05b69c7…` | **SURVIVED** | green; 759 OK suite-wide (§4) |
| R31 | omni block carries two `ActiveEnterTimestamp` lines, wrong value **last** | KILLED | `AssertionError: False is not true : omni: state boot stamp 2026-09-16T23:33:33Z is not the unit's ActiveEnterTimestamp` |
| R32 | omni block carries two `ActiveEnterTimestamp` lines, wrong value **first** | **SURVIVED** | green |

Delta attribution, measured (not reasoned): the identical R01 edit applied to a `35d44e6` snapshot stays green — `35d44e6 control: Ran 15 tests / OK` and `35d44e6 + both-files artifact_ready: Ran 15 tests / OK`. The guard is load-bearing for exactly this mutation class.

## 1b. Battery 2 — `observed_at` in both directions, re-gating cost, capture side (19 mutants)

| # | Mutant | Verdict | Assertion that fired |
| --- | --- | --- | --- |
| T02 | `PROJECT_STATE.observed_at` **only** → 55 min **older**, same day | KILLED | `AssertionError: '2026-09-17T01:00:00Z' != '2026-09-17T01:55:37Z'` |
| T05 | same field **only** → 5 min **newer**, same day | KILLED | `AssertionError: '2026-09-17T02:00:37Z' != '2026-09-17T01:55:37Z'` |
| T03 | same field only → older **and** dated 2026-09-16 | KILLED | first `Regex didn't match: '^2026-09-17T\d{2}:\d{2}:\d{2}Z$' not found in '2026-09-16T13:56:33Z'`, then the equality |
| T04 | same field only → newer **and** dated 2026-09-18 | KILLED | first the same date-pin failure on `2026-09-18T01:55:37Z`, then the equality |
| T06 | `runtime_observations.observed_at` only → older, same day | KILLED | `AssertionError: '2026-09-17T00:30:00Z' != '2026-09-17T01:55:37Z'` |
| T07 | dossier `observed_at` only → older, same day | KILLED | `AssertionError: '2026-09-17T01:55:37Z' != '2026-09-17T00:30:00Z'` |
| T08 | state **and** dossier moved, runtime left stale | KILLED | `AssertionError: '2026-09-17T01:55:37Z' != '2026-09-17T03:00:00Z'` |
| T09 | legit future wave: all three → `2026-09-18T10:00:00Z`, pin untouched | KILLED | `Regex didn't match: '^2026-09-17T…' not found in '2026-09-18T10:00:00Z'` |
| T10 | same wave **plus** the pin literal moved to `2026-09-18` | **SURVIVED (green)** | `Ran 15 OK` — one line re-gates; there is no second hidden date pin |
| T11 | all three reverted **consistently** to the base `2026-09-16T13:56:33Z` | KILLED | date pin only (the equalities all hold) — the pin still bites in the stale direction |
| T12 | omni `ActiveEnterTimestamp` in the capture changed alone | KILLED | `omni: state boot stamp 2026-09-16T23:33:33Z is not the unit's ActiveEnterTimestamp` |
| T13 | grok/omni `ActiveEnterTimestamp` lines exchanged in the capture | KILLED | two failures: `secondary: …` and `omni: … is not the unit's ActiveEnterTimestamp` |
| T14 | dossier `activation` gains a leaf | KILLED | `:819` dict-equality (`[240 chars] 'x'`) |
| T15 | dossier `activation` loses `profile_digest` | KILLED | `:819` dict-equality (`[135 chars] 191}`) |
| T16 | README header re-capture date → another day | **SURVIVED** | green |
| T17 | START_HERE `Snapshot: **2026-09-17T01:55:37Z**` reverted | **SURVIVED** | green |
| T18 | `runtime_observations.runbook` → nonexistent path | **SURVIVED** | green |
| T19 | `runtime_observations.evidence` → nonexistent path | KILLED | `FileNotFoundError: … '/tmp/rec5/m/T19-…/engineering/changes/nope.json'` |
| T20 | state `omni.acceptance` loses the `state` leaf | KILLED | `:819` dict-equality (the guard cannot be dodged by deleting the leaf) |

## 2. Is `TERMINAL_STATES` the right vocabulary? (measured)

```
failover TERMINAL_STATES       : ['artifact_ready', 'cancelled', 'needs_human', 'provider_unavailable', 'rejected']
failover STATES                : TERMINAL ∪ {accepted, evaluating, generating, normalizing}
landing_service._TERMINAL_STATES: ['artifact_ready', 'needs_human', 'provider_unavailable', 'rejected']
difference (failover - service) : ['cancelled']
'normalized' in TERMINAL_STATES: False | in STATES: False | in landing_observation.CATEGORIES: True
```
- "the shipped state machine" is not one machine: `landing_failover_contracts.py:7` (5 members, the set the test imports) and `landing_service.py:534` (4 members, the set that actually drives `_TRANSITIONS`) differ by `cancelled`. The comment "Vocabulary comes from the shipped state machine, not from a test-local set" is defensible but cites the failover-receipts set (`terminal` flag, `landing_failover_contracts.py:46,59`), not the job-machine set.
- The guarded value is not drawn from that machine at all: `normalized` is absent from `STATES` and present in `landing_observation.CATEGORIES` (`landing_observation.py:10-13`), produced by `landing_http.py:302` / `landing_live_executors.py:747`. So the assert is a **five-word blacklist over a value from a different vocabulary**, not a conformance check — measured: R17 (`normalizing`), R18 (`succeeded`), R19 (`Normalized`) all green. `assertIn(state, CATEGORIES)` or an equality against `normalized` would kill all three; `assertNotIn(…, TERMINAL_STATES)` cannot.
- **Not over-broad as written, and it had to be this narrow.** Every legitimate `state` leaf in this wave whose value lies inside `TERMINAL_STATES` (all outside the guard's scope, quoted from a scan of both files): `runtime_observations.services.primary.acceptance.state='artifact_ready'`, `…secondary.acceptance.state='artifact_ready'`, dossier `grok.smoke.state='artifact_ready'`, `qwen_historical_acceptance.socket_acceptance.state='artifact_ready'`, `omni.pilot.state='artifact_ready'`, `omni.pilot.db_row.state='artifact_ready'`. Generalising the guard across `state` leaves would fail the suite today (R15/R16 confirm primary/secondary are pinned *to* a terminal value). A third vocabulary sits under the same key name: `source_trail.omni_executor_activated.state='active+enabled'` (in neither set).
- `normalized` reachable-but-wrong elsewhere: yes — `PROJECT_STATE.json:1629`, `l5_production_preparation.historical_qwen_probe.state='normalized'`, is asserted by no test (`grep -rn "historical_qwen_probe" tests/*.py` → no hits), and the same block's legitimate `source_template_profile="qwen-omni"` is why the mainland/intl distinction in §5-1 is subtle rather than cosmetic.

## 3. Suite health, isolation, order dependence (serial)

| Run | Result | Time |
| --- | --- | --- |
| `python3 -m unittest tests.test_project_state` (control5) | `Ran 15 tests` **OK** | 0.131 s |
| coupled four (`test_project_state`, `test_structure`, `test_manifest_package`, `test_change_spec` — the set `test-plan.md` names) | `Ran 120 tests` **OK** | 9.886 s |
| whole suite `python3 -m unittest discover -s tests -t .` (git-ful copy) | `Ran 759 tests` **OK (skipped=1)** | 397.856 s (wall 6 m 38 s) |
| `ruff check tests/test_project_state.py` | `All checks passed!` | — |

Order dependence — **unchanged; the new import alters neither direction of it**:
- Isolated single method, plain env → `ModuleNotFoundError: No module named 'adaptive_factory'` at `tests/test_project_state.py:789` (the pre-existing `from adaptive_factory.landing_http import HttpLandingProfile`); `Ran 1 test / FAILED (errors=1)`. Identical to what I measured at `35d44e6`: same failing line, and the new import at :825 is downstream and never reached, so isolated runs are neither better nor worse.
- Isolated method with `PYTHONPATH=factory/src` → `Ran 1 test / OK` (0.086 s): the guard passes once the path exists.
- Independence probe: in a copy where the other two `adaptive_factory` imports *and* their consumers were stubbed out, the isolated method then failed with `ModuleNotFoundError` at the **new** import line — so `TERMINAL_STATES` is a second, independent `sys.path` dependency of the method; it adds no new failure to any currently-green invocation.
- The `factory/src` insert lives at `tests/test_project_state.py:849-851`, inside `test_m4_roadmap_matches_typed_state_machine_and_local_scope`, which the loader runs at index **8** of 15 while the guarded method runs at index **13** — an intra-module (alphabetical-order) dependence, not a cross-module one: no file under `tests/` other than this module inserts `factory/src` (the others insert `.grok-stack`).

## 4. Whole-suite silence for the decision-relevant survivors

Each mutant re-run as the **full** suite in its own copy; six ran concurrently and the unmutated control ran in the same batch as the baseline, so the comparison is like-for-like (`Ran 759 tests / OK (skipped=1)` for all six):

| Mutant | rc | suite |
| --- | --- | --- |
| R00 control (no mutation) | 0 | 759 OK (skipped=1) — 393.5 s |
| R13 pilot.state+db_row.state → `rejected` | 0 | 759 OK (skipped=1) — 393.3 s |
| R18 both leaves → `succeeded` | 0 | 759 OK (skipped=1) — 392.2 s |
| R22 mainland profile swap in both files | 0 | 759 OK (skipped=1) — 394.5 s |
| R23 omni `installed_sha` → zeros in both files | 0 | 759 OK (skipped=1) — 393.2 s |
| R30 `route.json.base_commit` reverted to the stale value | 0 | 759 OK (skipped=1) — 393.0 s |

## 5. Residual findings (severity; "evidence" = the record's own text presents it as proof)

1. **HIGH — the omni identity can be relabelled consistently (R22, R23; suite-silent).** The wave's central claim is "the omni unit boots the tagged `v2.0.18` source `e7d0f72b…` under the international profile", yet `omni.installed_sha` and `omni.selected_profile` are pinned only *across* the two files — never to a literal, nor to `observed_main_sha`, `published_release.merge_commit`, or `evidence.source_base`. Zeroing both `installed_sha` values, or moving both profiles to mainland `qwen-omni` (identical `model_id`, `landing_http.py:60-63`, so the model-vs-code check structurally cannot see it), leaves 759 green. Primary/secondary do have literal anchors (`qwen_historical_acceptance.merged_and_installed_sha`, `grok.merged_commit`). One line each closes it. This is the same failure mode the new guard's own comment names — "two files agreeing is not the same as being true" — applied to two leaves the guard does not reach.
2. **HIGH — the pilot job's state is unpinned in value (R13; suite-silent).** `assertEqual(pilot["state"], row["state"])` checks agreement only, while `revision` (3), `updated_at`, and both usage figures *are* literal-pinned; `state` is therefore the single hole in the block AC-003 offers as end-to-end delivery evidence ("the first end-to-end pilot job reaching artifact_ready"). Plain correction of my round-4 wording: "`pilot.state` alone is mutable" is **not** reproducible — R14 (lone `pilot.state`) is KILLED at :806. What is mutable is the *pair*. Everything else about that finding is unchanged at `6633e32`.
3. **MEDIUM — the new guard is a 5-word blacklist (R17/R18/R19).** Any other label passes, including a real non-terminal job state and a case variant, so "a relabelled probe" is blocked for five strings only (§2).
4. **MEDIUM — `observed_at` ordering is still unasserted (R21; my round-4 finding 3: still OPEN).** Answering the "both directions" question by measurement at this head: a **one-sided** stale top level is caught in every direction — older-same-day (T02), newer-same-day (T05), older-cross-day (T03), newer-cross-day (T04), runtime-only (T06), dossier-only (T07), and state+dossier vs stale runtime (T08) — so the two new equalities are sufficient for *agreement*. They are not sufficient for *plausibility*: moving all three stamps consistently to another time inside the pinned day is green (R21, `09:00:00Z`), and nothing requires `observed_at ≥` the facts it reports (`db_row.updated_at 00:21:16Z`, `pilot.observed_at 00:30:23Z`, omni boot `2026-09-16T23:33:33Z`, `published_at 2026-09-16T13:52:24Z`). The widened pin also costs the next wave one mandatory test edit (T09 KILLED) and no more than that (T10 green), and it still rejects a wholesale revert to the base day (T11) — so replacing the date literal with another date literal does **not** weaken the guard against any of the 7 one-sided staleness shapes tested; the residual weakness is the missing ordering assert, which was equally absent at base.
5. **MEDIUM — the capture is treated as ground truth and is itself unverified (R20, R24, R25, R31/R32).** `method`/`carried_reason` present `ExecMainStartTimestamp`, `NRestarts`, `Result`, `MainPID` as the proof that the older two units never restarted; none is asserted (R24/R25 green; round-4 C06/C08/C09 likewise). Per-block attribution is real and works in both directions (T12, T13 KILLED), but `blocks.setdefault(...)` + `break` keeps only the first block per `Id=` (R20 green), and `props` keeps the **last** duplicate key: a duplicated `ActiveEnterTimestamp` with the wrong value last is KILLED (R31), with the wrong value first is SURVIVED (R32) — the same lie is caught or missed on line order.
6. **MEDIUM — the prose the dossier offers as evidence is outside every gate (R26–R28, T16, T17).** `incident.clean_start` (the sentence that narrates the boot stamp), the `limits[]` non-promotion lines, and `endpoint_health.live` can be rewritten or deleted with 759 green; so can README's "re-capture" header date (T16) and START_HERE's `Snapshot:` stamp (T17) — the very lines round 4 edited to name `PROJECT_STATE.observed_at` as authoritative. The new comment's own claim ("`limits[]` says so in prose, and prose is outside every gate") is accurate; my measurements confirm rather than contradict it.
7. **LOW/MEDIUM — round 5's own metadata fix stays test-silent (R30, T18).** The corrected `base_commit` is genuinely right (`git merge-base origin/main 6633e32` → `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`; surface 22 files from the new base vs 40 from the old, whose extra names are `.grok-stack/adaptive_grok/architecture_diff.py`, `tests/test_architecture_fitness.py`, `decisions.md`, `mistakes.md`), and `verification.py:472,505,557,563` really does take the PR-mode comparison basis from it — but reverting it is green, and so is pointing `runtime_observations.runbook` at a nonexistent file (T18; only `evidence`, which is read, is caught: T19).
8. **LOW — the second re-point is not in the commit.** `.grok-stack/runtime/active-route.json` does carry `base_commit = 2f66ba6…` on disk, but `.gitignore:2` (`.grok-stack/runtime/*`) excludes it, so round 5's "re-pointed too" refers to untracked local runtime state no reviewer, receipt, or CI can inspect.
9. **LOW — duplicate blocks are a free channel only *outside* the pinned containers (R29 vs T14/T15).** Adding `omni.activation_copy` to the dossier is invisible (R29), while adding or removing a leaf *inside* `activation` is caught by the exact-set equality (T14/T15 KILLED).
10. **LOW — round-4 silences re-confirmed at this head** (R20/R22–R28 are their re-executions): `socket_path`, `host_config`, `base_url`, omni `control_repository`, `source_trail.*.control_sha`, dossier `published_release.commit`, `n_restarts`, `pilot.input_digest`/`input_media` — all measured mutable in the round-4 battery, none reached by round 5.

## 6. Prose vs code

- `test-plan.md`: the enumerated list "What the record loop actually pins, after rounds 3 and 4" (four bullets) **omits the round-5 guard**, so a list presented as complete now under-describes the test. That is an under-claim, not an over-claim. Its "Not asserted" paragraph is corroborated by my numbers (R20/R24/R25 green; the "lockstep" sentence matches T09/T10).
- `change-spec.yaml` INV-001 describes the test surface as "the added pins … that bind each recorded service to its own block of the captured systemctl output and the omni leaves to their dossier evidence". The new assertion binds an omni leaf to **product code vocabulary**, not to dossier evidence, and the statement's systemctl-clause coverage is confirmed true by T12/T13/R31. INV-001's "no product code … is touched" remains literally true (no `factory/` file in the diff) and its 22-file surface claim now holds against the corrected base.
- `state.json`: 6 history entries, last `2026-09-17T04:09:07+00:00`, status `verifying`, `grep -c "round 5"` → **0**; both `35d44e6` (04:10:17Z) and `6633e32` (04:19:46Z) post-date it. So the F5 sentence "The `state.json` transition now carries a real commit time" is imprecise — the stamp precedes the commit it describes by 70 s (the earlier "stamped after" defect *is* gone, but the value is a pre-commit verification time, not a commit time) — and the package state machine lags the commit under review by two.
- `evidence/review-response.md` F5 row: every checkable claim reproduced — the `verification.py` dependency, the real merge-base, 40 vs 22 files, `base_fingerprint` not being commit-derived (`sha256("05b69c7fbb1de7d7bc43f54863dd6cc95fdaa5f3")` = `3c846162ecfb…` vs stored `4912927a…`; `router.py:428-438` seeds `route_id` from it), and `base_fingerprint` deliberately left alone. The commit message's measurements reproduce exactly: both-file relabel KILLED with the quoted frozenset message, one-sided KILLED by the equality, control green, 15 OK, 120 OK, ruff clean. **No coverage claim is contradicted by my mutants** — the author's sentence is about "relabelling" the probe's state, and that is precisely what is closed; §5 items 1–3 are adjacent cases the prose does not claim.
- The test comment "The activation produced no artifact" is consistent with the record (`limits[]`, `activation.state='normalized'`, `live_url=null`), so the guard encodes a stated intent rather than inventing one.

## 7. Commands and evidence

```bash
cd /home/pall/grok-projects/adaptive-grok-build-omni-rec
git archive 6633e32 | tar -x -C /tmp/rec5/control5      # then git init -q . && git add -A && git commit -qm snapshot
git archive 35d44e6 | tar -x -C /tmp/rec5/parent35      # same, for delta attribution
python3 /tmp/rec5/r5run.py          # battery 1: 32 mutants + green control -> /tmp/rec5/results.tsv, /tmp/rec5/out/*.log
# battery 2 (T02..T20) drove the same build()/fresh() helpers over r5mutants2.M2
sed -n '/FAIL: test_runtime/,/^Ran/p' /tmp/rec5/out/R01-both-artifact-ready.log
sed -n '/FAIL: test_runtime/,/^Ran/p' /tmp/rec5/out/T12-capture-omni-aet-alone.log
cd /tmp/rec5/control5
python3 -m unittest tests.test_project_state
python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package tests.test_change_spec
python3 -m unittest discover -s tests -t .
python3 -m unittest tests.test_project_state.ProjectStateTests.test_runtime_observations_are_source_bound_without_promoting_qualification
python3 /tmp/rec5/suitecheck.py     # full-suite silence for R13,R18,R22,R23,R30 + control in the same batch
git merge-base origin/main 6633e32; git diff --name-only 2f66ba6..6633e32 | wc -l   # 22
git diff --name-only 05b69c7…6633e32 | wc -l                                        # 40
git check-ignore -v .grok-stack/runtime/active-route.json; ruff check tests/test_project_state.py
```

## 8. Limits

- Agreement, not liveness: no `systemctl`/`journalctl`/`sqlite3` was run, so I cannot say the host still matches the record — only that the tests cannot tell either way (§5-5). That boundary is now disclosed in `test-plan.md`.
- Full-suite (759-test) re-runs were executed for 5 selected survivors plus the control, not for all 21 survivors; the remaining 16 are §5's already-classified carry-overs whose module-level verdicts are re-measured at this head.
- §4's times are wall-clock under six-way contention (control 393.5 s in-batch); §3's 397.856 s is the serial figure.
- `git archive` snapshots exclude untracked/ignored files, so §5-8's `active-route.json` observation is a working-tree reading, not a reviewable commit object.
- The stub-out probe in §3 (`iso-e`) edited the copy's test source to expose the new import; that edit is a measurement instrument, not a mutation under the kill matrix.
- No repo was written: `control5 integrity: CLEAN`, and `git status --porcelain` in the worktree was empty before and after.

## 9. Summary

`6633e32` does exactly what it claims and nothing more. The new `assertNotIn(omni["acceptance"]["state"], TERMINAL_STATES)` is genuinely load-bearing: all five terminal labels set in **both** files are KILLED at line 826 while the leaf equality passes (failures=1), the identical edit is green at the parent, one-sided edits are caught earlier by the existing equality at :819, deleting the leaf is caught (T20), and the legitimate `artifact_ready` pilot stays green (R12, control). The `observed_at` widening is not a weakening — every one-sided staleness shape in both directions is killed (T02–T08), a wholesale revert to the base day is killed by the pin (T11), and the next wave's cost is precisely one line (T09 KILLED, T10 green); what remains missing is the ordering assert, and my round-4 finding 3 therefore stays **open** (R21). The `route.json` re-point is factually correct and its reasoning is now honest about the earlier wrong answer; it and the second, untracked re-point remain test-silent (R30). Suites are healthy and unchanged (15 / 120 / 759 OK, skipped=1; ruff clean), and the new import neither fixes nor worsens the pre-existing intra-module `sys.path` order dependence.

Beyond that one leaf nothing changed: the identity pair (profile, `installed_sha`) and the pilot job's `state` are relabellable consistently and silently across all 759 tests, the guard's vocabulary is a 5-word blacklist over a value that belongs to a different machine, and the capture's restart-proof fields plus the dossier's and README's prose stay outside every gate. Items §5-1 and §5-2 are the two I would want closed before this record is cited as gate-backed. None of them contradicts a package claim; the only prose defects found are `test-plan.md`'s now-incomplete pin list and `state.json` having no entry for round 5.
