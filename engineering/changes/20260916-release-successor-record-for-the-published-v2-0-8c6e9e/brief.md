# v2.0.18 release successor record (SR)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Why

`v2.0.18` was tagged and released on 2026-09-16T13:52:24Z (tag object `31d3171f651ea77e29de58d4affc58d008f1c7a5` → merge `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`), but the tree's `local_candidate` still says `pending_tag_and_release` with `merge_commit=null` and `published_release` still names `v2.0.17`. That is now false on the filesystem; this wave makes the record match reality.

## Outcome

`published_release` binds the v2.0.18 tag/artifact/check facts, v2.0.17 is archived (not rewritten) into `prior_published_releases`, `local_candidate` becomes the published record with the child's own merge identities — the only values the successor is permitted to write — `active_delivery`/`trust_ci.last_success`/`post_v2_0_17_landing` advance, and every coupled test literal moves in the same commit. `operational_activation` stays false: no provider install, host mutation, cohort or deployment is claimed.
