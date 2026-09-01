# Architecture analysis — truthful milestone state reconciliation

Route: `944abd96ddb3`  
Observed: 2026-09-01 after `git fetch --all --prune`  
Baseline: `origin/main@1c06299894279a88b881defa3f19b004fa742223`

## Finding

The repository currently collapses four different facts into the word “complete.” That is the root of the stale bootstrap: a milestone can have implementation and local review on a stacked branch without either being merged into its predecessor or delivered to `main`. Pull-request merge state and Git ancestry, not a change package's local `ready` state, determine integration and delivery.

The live protected-branch contract observed from GitHub is:

- required check: `adaptive-trust-ci/verified@06ecf1c875bc`;
- required GitHub App ID: `4694114`;
- strict/up-to-date required status checks: enabled.

These facts supersede the stale `6737355947c2` epoch in `PROJECT_STATE.json`, `START_HERE.md`, and `README.md`.

## One state model

`PROJECT_STATE.json` should represent a timestamped observation, not an aspiration. Give every milestone these independent fields and require an exact evidence reference for every non-empty state:

```json
{
  "id": "M2",
  "implementation": {
    "status": "not_started | partial | complete",
    "commit": "exact source SHA or null",
    "change_package": "repository-relative path or null"
  },
  "review": {
    "status": "not_reviewed | stale | passed",
    "commit": "exact reviewed SHA or null",
    "evidence": ["repository-relative report paths"]
  },
  "stack_integration": {
    "status": "not_applicable | open | failed | merged",
    "base_branch": "immediate predecessor branch or null",
    "pull_request": 10,
    "merge_commit": "exact merge SHA or null"
  },
  "main_delivery": {
    "status": "not_delivered | open | blocked | delivered",
    "pull_request": null,
    "merge_commit": null
  },
  "external_gate": {
    "status": "not_run | action_required | failure | success | stale",
    "name": "adaptive-trust-ci/verified@06ecf1c875bc",
    "head_sha": "exact checked SHA or null"
  }
}
```

Definitions:

- `implementation.complete`: the scoped product exists at the named source commit. It says nothing about review, merge, deployment, or production operation.
- `review.passed`: all route-required local reviews passed the same named commit/tree. Any later source change makes this `stale` until rerun.
- `stack_integration.merged`: GitHub records the milestone PR merged into its immediate predecessor branch and the merge commit is reachable from that branch. This is not delivery.
- `main_delivery.delivered`: GitHub records a PR merged to `main` and the resulting commit is reachable from the currently fetched `origin/main`. A successful check on an open PR is not delivery.
- `external_gate`: exact-SHA merge eligibility only. It never promotes another field by implication.

Top-level state should include `observed_at`, `observed_main_sha`, `policy_epoch`, and an `active_delivery` object. `completed_milestones` should mean only `main_delivery.delivered`; use a separate `implemented_milestones` list only if a summary is still desired. Subsequent milestone delivery PRs must update this state atomically with delivery-facing documentation.

## Truthful snapshot

| Item | Implemented | Reviewed | Merged to predecessor stack | Delivered to `main` | Evidence / qualification |
| --- | --- | --- | --- | --- | --- |
| M0 | complete | passed plus live operational proof | not applicable | yes | PR #5, merge `069fe822`; repairs PR #6/#7 are also on `main` |
| M1 | complete | passed | not applicable/root milestone | yes | PR #8 merged to `main` as `e81ae727`; the remote milestone branch later accumulated descendants and must not be mistaken for the PR #8 delivery head |
| M2 | complete | passed on recorded exact source | yes | no | PR #10 merged into `milestone/m1-typed-intent-evidence` as `c23fd49`; PR #16 repair merged into M2; current accepted aggregate is reachable at `origin/milestone/m2-executable-architecture@67714a1` |
| M3 | complete | passed | yes | no | PR #11 merged into M2 as `67714a1`; no PR has delivered that aggregate to `main` |
| M4 | complete on branch, with newer local repair | stale for latest local head | no | no | PR #17 remains open against M2 at remote head `8e65041`; its Trust CI check failed. Local `cf0219b` adds two unpushed commits, so old reviews/checks cannot authorize that newer tree |
| M5 | not started | not reviewed | no | no | roadmap only |
| M6 | not started | not reviewed | no | no | roadmap only |
| M7 | not started | not reviewed | no | no | roadmap only |
| M8 | not started | not reviewed | no | no | roadmap only; `milestone/a-plus-autopilot` is design documentation, not implementation |
| M9 | not started | not reviewed | no | no | roadmap only |
| SEO side project (outside M0–M9) | complete | passed | PR #18 merged into a non-main staging branch | no | PR #19 is open to `main` at `ecc85d9`, mergeable/clean, with successful current-epoch Trust CI; success is eligibility, not delivery |

PR #15 (`mvp/investor-ready`) is a broad demo branch with a failed Trust CI check, not evidence that M5–M9 are complete. PRs #12 and #13 remain blocked/action-required on the older policy epoch. They must be inventoried as independent open work and must not be silently folded into the milestone delivery chain.

## Safe integration order

1. **SEO first, using its already current exact gate.** If the delegated merge grant and branch protection permit, merge PR #19 only at head `ecc85d903d0394f99a139fd4e74a7cc452e386c6`, whose current-epoch check is successful. Fetch the resulting `origin/main`; do not reuse the pre-merge main SHA in later evidence.
2. **Rebase/recreate the state-only repair on that new `origin/main`.** Resolve only documentation/state conflicts, refresh the observation and PR inventory, run the state-only acceptance checks below, obtain a fresh exact-SHA `06ecf1c875bc` check, and merge the reconciliation PR. This avoids making the currently clean SEO PR stale merely for documentation and lets the repaired handoff truthfully say whether SEO reached `main`.
3. **Deliver the accepted M2+M3 aggregate without rewriting historical milestone branches.** Create a new delivery branch from then-current `origin/main`, merge exact `origin/milestone/m2-executable-architecture@67714a1f1b87effcfabe55d5ca2770d0a68d17c1`, resolve integration conflicts in that new branch, and rerun full verification, all required reviews, and current exact-SHA Trust CI. The delivery PR must target `main` and update the new state model to mark M2 and M3 delivered only after the merge is observable.
4. **Finish M4 against the accepted stack before main delivery.** Publish the bounded local successor through the existing M4 feature branch only after confirming the intended exact head (currently local `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`), rerun every route-required review because the reviewed remote head changed, and require a successful fresh current-epoch check on PR #17. Merge PR #17 into M2 only after those gates; that establishes `stack_integration.merged`, not main delivery.
5. **Deliver M4 from the latest main.** Create a new delivery branch from then-current `origin/main`, merge the exact accepted M4 stack head/merge result, resolve only integration conflicts, rerun verification/reviews, update state, and require a new exact-SHA current-epoch check before a PR to `main`. Do not reuse PR #17's check for this different base/tree.
6. **Do not merge legacy umbrella branches as shortcuts.** PRs #12, #13, and #15 need separate disposition. Close/supersede them only through explicitly authorized GitHub actions after proving their required changes are either delivered elsewhere or intentionally abandoned.

This order preserves reviewed ancestry, avoids force-pushing shared milestone branches, and keeps each base change coupled to fresh evidence as required by the engineering contract.

## State-only PR acceptance

1. The diff is allow-listed to bootstrap/state documentation, `mistakes.md`, and this durable change package; it changes no implementation, Trust CI source/configuration, holdout, hook, routing, schema, migration, package, or GitHub Actions path.
2. `PROJECT_STATE.json` parses and contains the four independent milestone axes above, exact SHAs/PRs, `observed_at`, `observed_main_sha`, current check name, and App ID. No milestone is marked delivered without both GitHub merged-to-main evidence and current `origin/main` ancestry.
3. `README.md`, `START_HERE.md`, and `PROJECT_STATE.json` agree on the current milestone handoff and `adaptive-trust-ci/verified@06ecf1c875bc` / App ID `4694114`.
4. M0/M1 are delivered; M2/M3 are implemented/reviewed/stack-merged but not delivered; M4 is not stack-merged or delivered and its latest local tree is not claimed fully reviewed; M5–M9 remain not started. SEO remains open or delivered according to the live observation made immediately before the state PR commit.
5. The README complete core graph remains structurally complete. Updating descriptive state must not add an unconnected core node.
6. A branch/PR inventory is regenerated after the final fetch, and each open PR records base, exact head, check epoch/result, and disposition without treating branch names or local `ready` files as merge authority.
7. Because this is a state-only/no-product change, use focused JSON, documentation consistency, graph, link, and diff-allowlist checks. Per `AGENTS.md`, do not claim product verification was required or that local receipts substitute for the external exact-SHA check.

## Rollback and recovery

- Before merge: close the isolated state PR and delete only its feature branch if explicitly authorized; no product or external runtime state changed.
- After merge: prefer a forward-fix PR with newly observed facts. If the JSON/bootstrap contract itself breaks consumers, revert the state PR's merge commit through another protected PR; never rewrite `main`.
- Verify recovery by parsing `PROJECT_STATE.json`, checking bootstrap/README agreement, rechecking the graph, fetching GitHub state again, and obtaining a fresh exact-SHA Trust CI result.
- Reverting documentation cannot undo milestone or SEO merges. Product rollback remains owned by each delivery PR and must never be represented as a state-file edit.
