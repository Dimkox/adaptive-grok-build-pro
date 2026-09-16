# build(release): deliver deterministic v2.0.18 ZIP and sidecar from the merged release-sync tree

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260916-build-and-deliver-the-deterministic-v2-0-18-zip-f03c54`
Route: `f03c541d1848` (base `fc8d9e6` = the release-sync merge)
Risk: high

## Problem

The release-sync commit `R` made `2.0.18` the candidate identity and asserted that no artifact bytes exist. A release needs tracked bytes that a tag can bind to, and those bytes must be reproducible from a named commit rather than from a live working tree.

## Outcome

`packages/` holds the `v2.0.18` ZIP and sidecar, built twice from the exact merged release-sync tree `fc8d9e6f11bb188ee514784d3b6f614a6da72803` in private `0700` staging with identical digests, and `local_candidate` records them as delivered while publication stays unclaimed.

## Scope

### In scope

- the two tracked artifact files, their `packages/README.md` row;
- `local_candidate` flips and the currency fields that must follow them (`observed_at`, `observed_main_sha`, dossier path);
- a fresh dated runtime observation dossier bound to this base;
- the coupled test literals in `tests/test_project_state.py` and `tests/test_manifest_package.py`.

### Out of scope

- tag `v2.0.18`, GitHub Release publication, and the post-publication documentation successor `SR`;
- identity surfaces (this commit does not bump any version literal);
- installation, restart or activation of the L5 services.

## Constraints

- Reproducibility: build only inside a clone checked out at `fc8d9e6…`; the two digests must match.
- Data/privacy: `.env`, private keys and credential stores are excluded by the packager and were not read.
- Self-limitation: the child cannot record its own merge identity, so `merge_commit`, `tree`, `checked_head` and `pull_request` stay null for `SR`.
