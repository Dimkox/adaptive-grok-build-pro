# Fix the M3 branch after accepted M2 changed: merge exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3, resolve integration conflicts without changing M3 requirements, add or update regression tests if needed, run verification and reviews, and prepare PR #11 for fresh exact-SHA Trust CI; no external writes without exact delegated grants.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260831-fix-the-m3-branch-after-accepted-m2-changed-merg-41eada`
Created: 2026-08-31T18:44:53+00:00
Risk: medium
Complexity: standard
Domains: frontend, integration, api

## Problem

Fix the M3 branch after accepted M2 changed: merge exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3, resolve integration conflicts without changing M3 requirements, add or update regression tests if needed, run verification and reviews, and prepare PR #11 for fresh exact-SHA Trust CI; no external writes without exact delegated grants.

## Outcome

The M3 candidate has a two-parent lineage that contains accepted M2 commit
`022411b05924618cfde0cb97b8c8aff4955e6013`, preserves M2's bounded Trust-CI
cleanup and packaging behavior, and preserves M3's governance contracts. Fresh
local evidence is derived for the resulting exact tree; prior exact-SHA evidence
remains historical and is not reused.

## Scope

### In scope

- Merge exact accepted M2 into the preserved M3 head with a normal two-parent merge.
- Resolve the four content conflicts by semantically retaining both milestones.
- Retain the finite `10820` architecture budget and all M2 read-only/package/zombie regressions.
- Retain M3 governance schemas, candidate-only lifecycle, handoff binding, and fitness assertions.
- Correct current README/handoff wording only where the merged source makes it stale.
- Run focused characterization tests, full PR verification, and fresh independent reviews.

### Out of scope

- M4 implementation, public API/event/schema redesign, database or runtime deployment changes.
- Governance activation, deployed Trust-CI policy/holdout/image/state changes, or production writes.
- Push, PR update, merge, release, or any other external write without a separate exact grant.
- Rewriting historical M2/M3 receipts or reports to claim they prove the new head.

## Constraints

- Backward compatibility: preserve both accepted M2 behavior and all M3 governance requirements.
- Data/privacy: no data model, credential, secret, PII, or external-system change.
- Performance: retain the finite `10820` changed-line ceiling; add no runtime path.
- Operational: source-only restack; external exact-SHA Trust CI remains mandatory before PR merge.
