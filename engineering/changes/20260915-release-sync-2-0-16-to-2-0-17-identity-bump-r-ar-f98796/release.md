# Release plan — Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

## Deployment

This commit is `R`: repository identity only, no external effect. After `R` merges:

1. `A` — build `packages/adaptive-grok-build-pro-v2.0.17.zip` and its `.sha256` sidecar from the **merged `R` tree** in a `0700` private staging directory, twice, from two independent exact-SHA clones; require byte-identical digests before anything is committed. Deliver exactly those two files plus the `local_candidate` publication flip as the artifact-child pull request.
2. Tag `v2.0.17` and the GitHub Release bind to `A`'s exact merged commit. Neither is authorized by this pull request: each is a named production action requiring its own exact delegated grant, and any tree or commit change invalidates a grant.
3. `SR` — documentation successor records `merge_commit`, `artifact_child.commit`/`tree`, `published=true`, `published_at` and the joined route/branch/package identities. `A` cannot self-record its own merge identity.

Rollout is a repository publication only. No installation, service creation, provider activation, host mutation or deployment is part of this release.

## Feature flags / staged rollout

No flag and no staged rollout applies: nothing in this chain changes runtime behavior. Source defaults stay off (`live_enabled: false`), and the installed L5 units keep running their own previously accepted SHAs until a separate, explicitly authorized operational step.

## Metrics and alerts

- `adaptive-trust-ci/verified@06ecf1c875bc` conclusion for each exact pull-request head (`R`, then `A`).
- GitGuardian conclusion on the same heads (informational; branch protection binds only the App-owned check).
- ZIP and sidecar digests recorded in `PROJECT_STATE.json`, reproducible from the tag target.
- Absence of any claim of operational activation: `operational_activation` must remain `false` in every record produced by this chain.

## Go/no-go criteria

Go for `R`: lockstep trio green in the frozen tree, `grok_verify --mode pr` PASS, `security_review` and `release_review` receipts bound to the final fingerprint, exact-head App check SUCCESS.
Go for `A`/tag/Release: `R` already merged, two byte-identical builds from the merged `R` tree, exact delegated grants for tag push and GitHub Release publication, and the App check SUCCESS on `A`'s head.
No-go: any wording that presents `2.0.17` as published, any artifact byte in `R`, any reuse of a grant after the tree or commit changed.
