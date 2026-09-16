# Release plan — v2.0.17 artifact child

This commit delivers bytes only. After it merges:

1. Tag `v2.0.17` as an annotated tag whose target is this pull request's exact merged commit, message `Adaptive Grok Build Pro v2.0.17; protected PR #<A>; assembled post-#91 source with adapters, profiles and deterministic artifact`.
2. Publish the GitHub Release for that tag with a hand-written body (not generated notes), `isPrerelease=false`, latest, and two assets: the ZIP and its sidecar.
3. `SR` records the merge commit, tree, checked head, pull request, `published=true`, `published_at`, tag object and digests, and closes the candidate record.

Tag push and Release publication are named production actions: each needs its own exact delegated grant bound to repository, route, change, HEAD, tree fingerprint and TTL, and neither substitutes for the App-owned exact-head check. Any commit or tree change invalidates a grant.

Rollout touches no runtime: no installation, no restart, no provider activation; `operational_activation` stays false through this chain.

Go/no-go: go when the exact-head App check is SUCCESS and bytes reproduce; no-go if `published` is true before the tag exists, if the two builds differ, or if the ZIP was produced from anything other than the merged release-sync tree.
