# #55: immutable release artifact policy decision

## Facts that constrain the change

`packages/` currently contains 19 tracked ZIPs totaling 64,529,937 bytes. `.gitignore` explicitly calls these tracked release artifacts while `dist/` is scratch. `PROJECT_STATE.json` binds published releases to `packages/...zip` and sidecar paths; `packages/README.md` explains the exact artifact identities. `tests/test_manifest_package.py:1418–1460` reads the published ZIP from the worktree and verifies the immutable digest and sidecar. The release workflow has delivered source parent plus artifact-only child commits. Existing tags, published assets, state records and hashes must remain immutable. Deleting `packages/` without a replacement artifact locator would break current-state verification and fresh-clone reproducibility.

## Exact user decision needed before implementation

Choose the future artifact source of truth:

| Policy | Consequence |
| --- | --- |
| **A. Keep tracked artifacts** | Preserve the present clone-verifiable model and accept Git growth. Improve documentation and avoid redundant ignored scratch copies where possible. |
| **B. Future releases use immutable GitHub Release assets; preserve historical tracked ZIPs** | Stops future blob growth without rewriting history. Verification must fetch/inspect release assets by exact tag, name, digest and provenance; offline checks need an explicit `unavailable`, not a false pass. Old `PROJECT_STATE.json` paths remain valid. This is the bounded migration choice. |
| **C. Remove all tracked ZIPs from future source trees** | Reduces working-tree size more, but published state and tests must migrate every historical artifact locator. Old commits retain blobs; history rewrite is a separate destructive operation and is outside this packet. |

Recommendation for design review is **B**, contingent on user selection and reliable access to immutable release assets. The user has not yet selected a policy, so no artifact removal, `.gitignore` change, or release-flow change is authorized by this research packet.

## If B is selected: bounded delivery design

1. Define a versioned artifact locator in `PROJECT_STATE.json` for future releases: repository, tag, asset name, SHA-256, sidecar SHA-256 and exact merged commit. Keep old records and published bytes untouched.
2. Update verifier and tests to check the locator schema and digest, with offline fixture assets in focused tests. The online release check must fail or report unavailable if an asset cannot be fetched; it may never claim bytes were verified based only on a JSON hash.
3. Change future packaging to produce `dist/` candidates, publish assets only after exact merged commit, external Trust CI and delegated release authority, and record immutable asset IDs/hashes. Stop adding future ZIPs under `packages/`; update `.gitignore`, `packages/README.md`, main README, release runbooks, and source-parent/artifact-child design accordingly.
4. Exercise rollback by preserving previous release assets and verifying old local-path records still resolve. Keep a forward-recovery path if an asset upload succeeds but state update fails; no tag or asset mutation after publication.

Likely touched files: `PROJECT_STATE.json` (future record only), `scripts/package_stack.py`, `scripts/verify_manifest.py`, `tests/test_manifest_package.py`, `.gitignore`, `packages/README.md`, `README.md`, release runbooks. Required evidence: exact ZIP/sidecar hashes, tag/merge identity, asset existence and digest, source/tree fingerprint, external policy check and delegated publication. No history rewrite or host cleanup is included.
