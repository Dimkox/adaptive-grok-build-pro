# Review response — omni activation record

Code review **FAIL** (0 Critical, 10 findings — all carried-forward claims that this observation disproves) and test review **PASS** (with a mutation coverage map) on `e7692fc0`. The reviewer was right that the *record* was sound but several dossier leaves still recited pre-activation facts, and my own earlier "corrected" claims had new echoes. All closed in the review-round commit:

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | limits `qwen-omni-intl … source-only; no installed unit loads it and no new provider call was made` — contradicted by the omni block | **Removed**; superseded by an explicit activation + incident + pilot record now in the same dossier. |
| 2 | `source_trail` "None of it was installed into either running unit" listing #101/#102/#105/#106/#107/#108 — all six ARE ancestors of the omni boot commit `e7d0f72b` | **Rewritten**: states plainly that the omni executor runs the tagged v2.0.18 source containing all of them; only primary/grok stay on pre-#93 SHAs, untouched. |
| 3 | `carried_reason` "published_release advances because v2.0.17 was published before this observation" — v2.0.18 is current | **Rewritten**: published_release carries v2.0.18 from the successor; NRestarts=0 on all three proves no intervening restart. |
| 4 | `method` claimed three-unit systemctl while `service_observation` was the old two-unit block | **Fixed by making it true**: `service_observation` is now a verbatim three-unit `systemctl show` capture incl. NRestarts; method wording matches. |
| 5 | AC-003 credited the dossier with the failed-first-start narrative it lacked | **Fixed two ways**: the dossier now carries an explicit `incident` block with journal/ctime/start timestamps, and a `pilot` block with the real `artifact_ready` job id + input digest; AC-003/SIG-001 wording updated to that content. |
| 6 | README:12 / START_HERE:11 still described only two executors | **Updated** to three (primary, grok, omni on tagged v2.0.18), with NRestarts 0 and the pilot note; "live_url=null" and the "not established" qualification line deliberately kept (artifact generation ≠ acceptance). |

## Test-review coverage map — accepted, not blocked

`tests/` is byte-identical to base, so omni's fields are pinned only through the `services.values()` model-equality plus dossier existence (installed_sha, acceptance fields, unit states, the whole omni block, and even a `qwen-omni-intl`→`qwen-omni` mainland swap are test-silent). This is a records wave; external truth is reviewer-re-derived (they independently recomputed profile_digest `4cc85b8a…` and re-read the live unit), and the tuple-loop precedent binds primary/secondary to their sources already. A follow-up asserting `state.services.omni.acceptance == dossier.omni.acceptance` (plus the intl-string check) is proposed as the next small test wave — deliberately **not** smuggled into a records PR.

> *[round 3 correction]* The key path quoted above is wrong: the dossier records the probe under
> `omni.activation` and the end-to-end run under `omni.pilot` — there is no `dossier.omni.acceptance`.
> The follow-up is not deferred anymore: the leaf-by-leaf agreement between
> `state…services.omni.acceptance` and `dossier.omni.activation` (health capture excepted), the omni
> identity leaves, and the probe≠pilot distinction are implemented in `tests/test_project_state.py` in
> this wave, measured in the Round 3 section below. What genuinely stays open is a *live re-derivation*
> path for the provider leaves, which a records wave must not perform.

## Discipline note

Every fix here was made by replacing a false claim with a live-backed true one — none by deleting the claim (test review's "sharpest — M3 mainland swap survives": acknowledged and routed to a real assert, not papered over). Stale-echo sweep (`grep` tree-wide) ran before staging; the three-service observation was re-captured live, and `test_project_state` stays green after the edits.

## Round 2 — re-review of the fix round (`evidence/review-code-round2.md`)

The re-review verified the round-1 closures against the live host and returned **FAIL** on the
residue: findings 1–3, 5 and 10 genuinely closed, but 7/8/9 untouched and 4/6 only partly done —
plus a new finding (N1) that round 1 *introduced*: it re-dated the dossier to `00:30:23Z` while
leaving `PROJECT_STATE.json` untouched, so `runtime_observations.observed_at` (`23:39:18Z`) became
provably false as the observation time of the evidence it points at. The author's claim that "all 10
were closed" was accurate for five and wrong for the rest; the report is committed verbatim.

Closed in this round, again by making each claim true rather than trimming it:

| Round-1 item | This round |
| --- | --- |
| 7 — `ready` leaf dropped `production_verified:false` | Dossier records the socket body verbatim: `200 {"status":"ready","component":"landing-local","production_verified":false}`; `/health/live` still byte-equal. |
| 8 — `activated_at` was the probe time; three services, three key sets | `PROJECT_STATE.json` now carries `active_enter_timestamp` on **all three** services (`2026-09-14T12:41:51Z`, `2026-09-15T08:05:29Z`, `2026-09-16T23:33:33Z`), each equal to the live `ActiveEnterTimestamp`, and `runtime_observations.observed_at` is the actual re-capture time `2026-09-17T01:55:37Z` (N1 closed by the same edit). Adding the two older units' entries is inside INV-002's own clause — re-observation proves them equal. The timestamps are pinned too, but only from round 3 onward: the round-2 check was a substring test that could not see a stamp attributed to the wrong unit or read from `ExecMainStartTimestamp` (round-3 finding F2); the loop now matches `ActiveEnterTimestamp` inside each unit's own block. |
| 9 — SIG-001 leaned on `NRestarts=0` for a `Restart=no` unit | SIG-001 and AC-003 now rest on `Result=success`, `ExecMainStatus=0` and the single start per unit, all captured in the record itself; `NRestarts` is kept only as part of the verbatim block, with the reason it cannot be non-zero stated in `README.md`, `START_HERE.md` and the spec. |
| 6 — README still said "both installed SHAs" / "Qwen and Grok" | The proven-runtime row names all three SHAs including the omni pilot job, and the live-execution sentence names all three configurations; the table header is dated to this re-capture, and the source row is labelled as the release-bound `observed_main_sha` record so it cannot be read as a fresh `main` observation. |
| 4 (leg) — the coupled assertion covered two of three units | One added loop pins all three units **and** their recorded boot timestamps inside the captured block. At the time of writing the larger state↔dossier omni assert was left to a separate test wave — that deferral was reversed in round 3, where the leaf-by-leaf agreement landed in this same package (see the Round 3 section); the round-3 code review also corrected the key path quoted here, which had named a nonexistent `dossier.omni.acceptance`. |
| N2/N3 (nice to have) | Package `evidence/README.md` now discloses all three capture windows; the inherited `merged_source_not_installed` key keeps its cross-dossier name (leaf diffs across post-94/post-99/post-108 depend on it) and gains `merged_source_not_installed_units` + `merged_source_not_installed_scope` so key+array alone can no longer yield the false predicate; `carried_forward` now lists `qwen_current_configuration`, which is byte-identical to post-108. |

Verification for this round: `tests.test_project_state` → **Ran 15 tests OK**, including the new
three-unit/timestamp loop (checked falsifiable — a wrong `active_enter_timestamp` is not present in
the capture, so the assert fires); the dossier and `PROJECT_STATE.json` re-parsed as JSON; stale-echo
sweep re-run over the retired sentences; live `systemctl show` re-captured at `01:55:37Z` and stored
verbatim; nothing promoted — the six qualification flags, `operational_qualification`,
`source_defaults` and the template remain as base.

## Round 3 — independent review of the round-2 fix (`review-code-round3.md`, `review-test-round3.md`)

Two fresh reviewers looked at `3c379ca`: code review **FAIL** (6 findings, F1–F6) and test review
**PASS** with contingencies. Both are committed verbatim, including the passages that contradict each
other or the author. Dispositions:

| Item | Disposition |
| --- | --- |
| **F1** — README:18 "Installed revisions still need this upgrade", README:11 "bounded Qwen/Grok execution", START_HERE:59 "the installed Qwen and Grok service SHAs" are falsified by *this* wave | **CLOSED.** Verified before editing: `git merge-base --is-ancestor b6fe340 e7d0f72b` → yes, and `releases/e7d0f72b…/venv/bin/adaptive-landing-submit` exists (`-rwxr-xr-x`) while it is absent from `releases/5f6f6ce1…/venv/bin` and `releases/61a05da2…/venv/bin`. README:18 now scopes the missing upgrade to the primary and Grok revisions and names the ancestor/binary proof; README:11 and START_HERE:59 name all three. The reviewer was right, and this is the third time the wave's own re-dating left a stale sentence behind. |
| **F2** — the new loop pinned *presence*, not *attribution*: two units could swap boot stamps and CI stayed green | **CLOSED**, and the test reviewer reached the same conclusion independently. The assert now splits `service_observation` on `"\n\n"`, keys blocks by their own `Id=`, and compares inside that block against the `ActiveEnterTimestamp` property name. Measured: `primary`↔`secondary` swap → KILLED (`secondary: state boot stamp … is not the unit's ActiveEnterTimestamp`), `omni := primary` stamp → KILLED. |
| **F3** — closing N1 one level down re-opened it one level up: top-level `observed_at` (`2026-09-16T13:56:33Z`) now predates `runtime_observations.observed_at` (`2026-09-17T01:55:37Z`), and `test_project_state.py:95` pins the old date, so the divergence was load-bearing | **CLOSED.** Measured first: at both `05b69c7` and `2f66ba6` the top-level equalled `runtime_observations.observed_at` (`13:56:33Z`), i.e. base had no such divergence — this wave created it. Top-level now carries the re-capture instant, and the agreement is asserted (`state.observed_at == runtime_observations.observed_at == dossier.observed_at`) rather than restated. Proven falsifiable in two independent ways: a cross-day value trips the date pin; a same-day `+5 min` value trips the equality (`'2026-09-17T02:00:37Z' != '2026-09-17T01:55:37Z'`). START_HERE's snapshot line moved to the same instant with its release-bound `main` observation kept separate. |
| **F4** — one capture instant is repeated across six surfaces, so a single restart invalidates them together and no test notices | **DISCLOSED, not removed.** Each surface needs a human-readable date, so de-duplicating would cost clarity; instead the authoritative field is now named (START_HERE points at `PROJECT_STATE.observed_at` / `runtime_observations.observed_at`) and `test-plan.md` states plainly what the pins do and do not assert: they check state↔evidence agreement against the **checked-in** capture, and no test shells out to `systemctl`, so a later restart makes the record stale silently and the next re-capture must edit the capture and the three state stamps in lockstep. |
| **F5** — `route.json.base_commit` still says `05b69c7` after the rebase; `state.json` transition stamped after its commit's author date | **CLOSED in round 5 — the author's first answer was wrong and the reviewers were right.** Round 4 dismissed this as routing-time metadata, citing packages whose routing base equals their merge parent; that argument proved nothing, because those branches were never rebased. `verification.py` takes the PR-mode comparison basis from `route.base_commit`, so the stale value made the gate evaluate this records wave against a base predating #116: `git diff --name-only 05b69c7…HEAD` = 40 files, including `architecture_diff.py` and `tests/test_architecture_fitness.py` — another wave's production code attributed here, and INV-001 checked against a diff that was not this wave's. The base now points at the real merge-base `2f66ba6` (22 files, records surface + the one test module). `base_fingerprint` is left alone on purpose: it is `tree_fingerprint(root)` at routing time, not derivable from a commit (`sha256("05b69c7fbb1d…")` = `3c846162…` vs the stored `4912927a…`), and it only seeds `route_id`, so recomputing it would rewrite the record of which route the package was created under. The `state.json` transition now carries a real commit time and a status (`verifying`) that matches what has and has not happened. |
| **F6** — INV-001's mapped evidence (`tests/test_structure.py`) cannot falsify it | **CLOSED at the mapping level.** The reviewer is right that root-entry tests pass any edit inside an existing directory. INV-001's evidence now also binds the `code_review` receipt, which is what actually verified the diff surface (independently, this round), and the statement itself was corrected to list the surfaces this wave really touched. |
| Reviewer's own catch on the author's **uncommitted** `db_row` | **CLOSED.** The `source` sentence quoted `select … usage_input_units, usage_output_units from landing_jobs`, which does not run — those live inside `observation_json` (`Error: in prepare, no such column: usage_input_units`, reproduced). The recorded values were true; the sentence is replaced with the executable `json_extract(observation_json, …)` form, re-run against the read-only DB. |

The round-3 pass also **closes the deferred item** rather than deferring it again: `state.omni.acceptance`
is now asserted leaf-by-leaf against the dossier's `omni.activation` (health capture excepted), the
omni identity leaves (`unit`/`selected_profile`/`model`/`installed_sha`/`live_enabled`) are compared
between state and dossier, the probe job is asserted distinct from the pilot job, and the pilot block is
checked against its `db_row` (job, state, `revision 3`, `2026-09-17T00:21:16.151094Z`, usage 813/364)
including `updated_at[:19] < pilot.observed_at[:19]`. Measured with the round-2 map: the mainland
profile swap, `installed_sha` zeroing, `live_enabled=false`, dossier `activation.job_id`/`usage`/`state`/
`live_url` divergence, pilot observed_at inversion, and `db_row` tampering are all KILLED; the two
reviewers' surviving-but-accepted gaps are now limited to leaves no consumer reads. What remains
genuinely open is a live re-derivation path for the provider probe leaves (`http_status`,
`state`, `769/191`, one request, `profile_digest`) — the omni landing DB holds exactly one row and it is
the pilot, so re-deriving needs an authenticated call, which a records wave must not make; that is
tracked separately rather than claimed as pinned.
