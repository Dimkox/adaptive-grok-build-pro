# Review response — v2.0.18 successor record (SR)

Security review PASS (2 Suggestion, 3 nice-to-have) and release review **FAIL** (2 Important, 3 Minor, 2 nice-to-have) on `28de12c`. Both independently re-derived every published fact from live sources and found the **record** correct; the FAIL was coverage of untested current-state surfaces. All closed in the review-round commit.

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Important/AC-004 — `packages/README.md` still named v2.0.17 "latest published" and v2.0.18 "tag pending" (the exact two lines #100 flipped); no test reads the file, so 119 stayed green | **Fixed**: header line now binds v2.0.18 (published_at, target, both digests) with v2.0.17 kept as the immutable predecessor; the v2.0.18 row reads `(published 2026-09-16T13:52:24Z)`. Recurrence recorded in `mistakes.md` with the durable rule (mirror precedent by `git show --name-only`, hand-verify untested surfaces). |
| 2 | Important — R/A `tasks.md` rows the SR was promised were not ticked (#100 advanced tasks lines, not state.json) | **Fixed**: A's three open rows and R's deferral row now carry delivered facts (#108 merge, App run `104809218211`, tag object, grant id, SR route/package). `state.json` files intentionally stay at precedent lifecycle points, as the reviewer's own precedent check established. |
| 3 | Suggestion — AC-002's test evidence overstated coverage (5 of ~22 identity fields pinned; V2017_* constants dead) | **Fixed**: prior[0] now also pins sidecar digest, tag_object, attestation, published_at, merged_at, pull_request — the previously dead constants are live, and re-stamping any archived identity fails the suite; AC-002 text updated to what the test actually guarantees. |
| 4 | Minor — stale "candidate" self-description in README source row and HANDOFF #106 line | **Fixed** both. |
| 5 | Minor — duplicate `requirement` assertTrue; dropped `zip_source_note` assert | **Fixed**: dedup, restored the note assert A had. |
| 6 | Minor — dossier `service_observation` lost blank-line separators (not verbatim stdout) | **Fixed**: regenerated verbatim from a live read-only `systemctl show`; substring assertions re-verified. |
| 7 | Minor — the published GitHub Release body cited PR #107's check run as "PR #108 lineage" | **Fixed externally**: `gh release edit v2.0.18` now names run `104809218211`/attestation `8172a5bc…` for #108 and labels `104782126773` as the release-sync's run; in-tree values were already correct. |
| 8 | Nice-to-have — spec tier red vs precedent yellow | **Kept red**: this route profile is release/high-risk end-to-end and the gate validates; recorded here so the deviation is intentional, not drift. |

## Limits

The reviews confirmed the record but no PR existed at their time; the exact-head App check on this successor PR remains the only merge authority, and the final `grok_verify` run must bind the head that contains these dispositions and both reports.
