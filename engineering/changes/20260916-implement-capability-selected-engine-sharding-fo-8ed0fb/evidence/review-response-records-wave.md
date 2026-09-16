# Review response — records wave (paperwork on top of #113)

Code review **PASS** and test review **PASS** on `8c54320`; reports kept as siblings
(`review-code-records-wave.md`, `review-test-records-wave.md`) because `review-code.md`/`review-test.md`
are the merged PR #113 evidence this wave's transitions cite — overwriting would destroy cited proof.

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Important (code) — bootstrap docs (`START_HERE.md:14`, `GROK_BUILD_HANDOFF.md:306`, `DARK_FACTORY_ROADMAP.md:98`) still framed #33 as unretaken and the inventory stopped at #108, contradicting the resolution this same commit writes; repo precedent (627a16 AC-005) reconciles bootstrap docs in the inventory-flip commit | **Fixed in-wave**: all three surfaces now state the #113 delivery (`35cbbe0f…`), the post-publication landings #111–#113, and #104's narrowed remainders (anyOf blind spot, declaration policy). The reviewers' independent mutation proof shows the pinned literal still bites; the `observed_main_sha` requirement in those sections is untouched. |
| 2 | Suggestion (code) — `retaken_and_delivered` + `unique_scope "Parallel local Python verification"` readable as "parallel shipped" | **Fixed**: resolution gains the explicit clause that true parallelism stays conditional on an importable pytest+xdist; elsewhere the degrade is disclosed. |
| 3 | F1/F2 (test) — no adversarial arm for the flipped entry; merge SHA not offline-checkable | **Fixed**: `test_retained_33_entry_records_the_delivered_retake` asserts status/resolution content and the preserved historical fields, and, when the `35cbbe0f…` object is fetched locally (guarded like the existing `cat-file -e` pattern), asserts its subject names `(#113)`. |
| 4 | F5 (test) — the pinned literal is machine-generated; hand-edits will drift | **Fixed**: `GENERATED` comment added above the entry; regeneration is the documented procedure. |
| 5 | F3/F4 (test) — nothing pins bootstrap prose to inventory (accepted: docs are human surfaces, reviewers verify live); `retained_unresolved` now holds a delivered item (naming) | Accepted with rationale: renaming the key would churn five readers for a label; the entry's own `status` disambiguates and the adversarial arm above pins it. |
| 6 | F6 (test) — binding caveat: counts quoted bind to `8c54320`, worktree moved mid-window | **Addressed by design**: everything lands in ONE commit; the single final `grok_verify --mode pr` and all receipts bind that head; receipts are recorded only after it passes. |

Limits: external truth (PR state, check verdicts, merge SHAs) is not test-pinnable; both reviewers
re-derived it live and the App-owned exact-head check on the final head remains the only merge authority.
