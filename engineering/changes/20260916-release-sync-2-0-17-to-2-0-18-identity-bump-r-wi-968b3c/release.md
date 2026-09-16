# Release plan — v2.0.18 (stage R)

- Base: `d146ca455d615683765b443b747f55aa4dbad436` (PR #106 merge, observed 2026-09-16).
- This commit is the identity bump only: ZIP, sidecar, tag and GitHub Release for v2.0.18 do not exist and are asserted absent by `local_candidate`.
- Order per pinned doctrine: R merges on its exact-head App check → artifact child A builds both delta paths from the merged R tree → tag push and GitHub Release publication each need their own explicit delegated grant → successor SR records publication.
- The v2.0.17 record stays published and immutable.
