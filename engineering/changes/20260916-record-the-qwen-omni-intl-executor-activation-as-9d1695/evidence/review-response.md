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
| 8 — `activated_at` was the probe time; three services, three key sets | `PROJECT_STATE.json` now carries `active_enter_timestamp` on **all three** services (`2026-09-14T12:41:51Z`, `2026-09-15T08:05:29Z`, `2026-09-16T23:33:33Z`), each equal to the live `ActiveEnterTimestamp`, and `runtime_observations.observed_at` is the actual re-capture time `2026-09-17T01:55:37Z` (N1 closed by the same edit). Adding the two older units' entries is inside INV-002's own clause — re-observation proves them equal — and is pinned, not just asserted: `test_project_state` now checks each state timestamp against the verbatim capture. |
| 9 — SIG-001 leaned on `NRestarts=0` for a `Restart=no` unit | SIG-001 and AC-003 now rest on `Result=success`, `ExecMainStatus=0` and the single start per unit, all captured in the record itself; `NRestarts` is kept only as part of the verbatim block, with the reason it cannot be non-zero stated in `README.md`, `START_HERE.md` and the spec. |
| 6 — README still said "both installed SHAs" / "Qwen and Grok" | The proven-runtime row names all three SHAs including the omni pilot job, and the live-execution sentence names all three configurations; the table header is dated to this re-capture, and the source row is labelled as the release-bound `observed_main_sha` record so it cannot be read as a fresh `main` observation. |
| 4 (leg) — the coupled assertion covered two of three units | One added loop pins all three units **and** their recorded boot timestamps inside the captured block. The larger `state.omni.acceptance == dossier.omni.acceptance` assert (and the `qwen-omni-intl` mainland-swap check the test review called sharpest) stays a separate test wave — that one needs new comparison machinery, while this one only reads the capture that already exists. |
| N2/N3 (nice to have) | Package `evidence/README.md` now discloses all three capture windows; the inherited `merged_source_not_installed` key keeps its cross-dossier name (leaf diffs across post-94/post-99/post-108 depend on it) and gains `merged_source_not_installed_units` + `merged_source_not_installed_scope` so key+array alone can no longer yield the false predicate; `carried_forward` now lists `qwen_current_configuration`, which is byte-identical to post-108. |

Verification for this round: `tests.test_project_state` → **Ran 15 tests OK**, including the new
three-unit/timestamp loop (checked falsifiable — a wrong `active_enter_timestamp` is not present in
the capture, so the assert fires); the dossier and `PROJECT_STATE.json` re-parsed as JSON; stale-echo
sweep re-run over the retired sentences; live `systemctl show` re-captured at `01:55:37Z` and stored
verbatim; nothing promoted — the six qualification flags, `operational_qualification`,
`source_defaults` and the template remain as base.
