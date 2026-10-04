# Architecture — v2.0.12 ship

## Current behavior

Published identity is `v2.0.11` on `c54fd01`. Feat is ~200 commits ahead with uncommitted K16 docs/toolchain. Trust CI GitHub App check is not live. `main` is unprotected.

## Proposed behavior

One ship commit on `feat/trust-ci-control-plane` with product identity **2.0.12**. Rebase onto `origin/main`. Push the feat branch only. Rebase-merge PR #2. Tag and GitHub-release the merged SHA.

## Decisions

- User direct order is source-of-truth #1 for commit, push, merge, and release.
- VERSION bump is required; do not retag `v2.0.11`.
- Trust CI service identity stays 2.1.0.
- Merge method is `--rebase`. Never `git push origin main`.
- Bootstrap exception: merge without App-owned check because the check cannot exist until a later deploy and forging it is forbidden.
- Pins, PEMs, leftover `20260817-вычисти*` stay out of git.

## Risks

- GitGuardian failure on the current PR head is not Trust CI and is not a required check; ignore for merge.
- Rebase onto `8a2f95c` may conflict on `mistakes.md`; keep the working 2026-08-23 entry, drop the hook-dump.
- Grant fingerprint invalidates after any tree change; protected writes are one batch; production grants are minted after the ship commit.
