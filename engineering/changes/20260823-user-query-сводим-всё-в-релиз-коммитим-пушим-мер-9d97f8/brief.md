# Release v2.0.12 from feat/trust-ci-control-plane

Change ID: `20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8`
Created: 2026-08-23T21:30:42+00:00
Risk: high
Complexity: high-risk
Domains: generic
Route: `9d97f8dcae59`
Write owner: none (parent)

## Problem

`v2.0.11` is already published on `c54fd01`. The feat tree plus the dirty Trust CI docs/toolchain slice is a new product surface. The user ordered commit, push, merge, and release.

## Outcome

Product identity **2.0.12** is committed on `feat/trust-ci-control-plane`, pushed, rebase-merged through PR #2, tagged `v2.0.12`, and published as a GitHub Release. Trust CI service identity stays **2.1.0**. No GitHub Actions. No invented App-owned check. No host deploy and no branch protection in this slice.

## Scope

### In scope

- Bump VERSION/CHANGELOG/README/packages zip to 2.0.12.
- Commit the dirty K16 docs/toolchain/tests/change-package tree (not leftover `20260817-вычисти*`, not pin env/PEMs).
- Rebase onto `origin/main` (`8a2f95c`).
- Push `feat/trust-ci-control-plane`, mark PR #2 ready, `gh pr merge --rebase`.
- Tag and GitHub Release `v2.0.12` of the merged SHA.

### Out of scope

- GitHub App, webhook, Trust CI host deploy, `compose up`, `branch-protect`.
- Forging `adaptive-trust-ci/verified@*`.
- `git push origin main`.
- Committing GHCR digests or secrets.

## Constraints

- Backward compatibility: PR-only delivery; local receipts stay advisory.
- Data/privacy: no pins, PEMs, or `.env` in git.
- Operational: bootstrap merge is a named exception because main is unprotected and the App check cannot exist until a later deploy.
- Human gates: user text «мое прямое указание» is scope and production-action approval.
