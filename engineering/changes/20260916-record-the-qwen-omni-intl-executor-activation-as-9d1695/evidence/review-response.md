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
