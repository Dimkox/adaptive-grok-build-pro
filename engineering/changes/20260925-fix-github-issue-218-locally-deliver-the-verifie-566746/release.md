# Release plan — issue #218 clean squash delivery

## Current preparation

The one-child delivery candidate includes the immutable source projection plus the thirteen-path post-source contour enumerated in `architecture.md` and this package. Historical projection, full-verifier PASS runs, and review failures remain dated evidence. The e824fb15 review wave failed on repeated-count ordering, endpoint/worktree resource bounds, and package contradictions; those reports are preserved without overwriting previous reviews.

1. Finish the bounded repairs and adversarial focused regression matrix.
2. Validate the exact source-relative contour, typed spec and current local scope/design decision against the user's instruction to continue #227 through #0. This record grants no external operation.
3. Run one preliminary full verifier with `--no-record`.
4. Run all four route reviews against the same frozen snapshot with a timebox; stop expanding a review once a blocking reproducible finding is established.
5. Persist every report; finish all tracked package/history/accounting updates; transition to `ready`.
6. Amend the sole candidate so its sole parent remains `cb9af4073...`; do not add a second delivery commit.
7. Run final recording verification on the clean exact HEAD. After its current verification PASS receipt exists, record the passing review receipts and require read-only zero-gap `grok_status`.

The write-owner repair handoff does not perform steps 3–7 or mark the package ready. New product changes invalidate affected reviews and prior verification.

## Go/no-go and publication boundary

Local go requires exact provenance/contour, completed focused and full verification, passing independent reviews and fresh receipts in the mandated order. Ambiguous ordering, budget exhaustion, findings, missing reports, source mutation or stale evidence is no-go.

On September 26, local annotated tag `v2.0.19` resolves to tag object `4e5d1505433f7a2d5faa71db31c0b4d964f77897` and target `cb9af4073ba6c3d515145164d771c75ebdfa3224`. September 24 release descriptions are dated historical observations. Remote tag publication, GitHub Release and latest remote release have not been queried. No publication, artifact rebuild or version bump is requested.

No runtime rollout or feature flag is needed. Observe the candidate SHA/tree, scan completeness, limit diagnostics and receipt status. Any future PR/merge/publication requires separate exact authorization and App-owned Trust CI for the exact up-to-date head plus separately required approvals. #219/deployed policy/holdout remain outside scope. Rollback is abandonment before delivery or a reviewed revert afterward; no production mutation was performed.
