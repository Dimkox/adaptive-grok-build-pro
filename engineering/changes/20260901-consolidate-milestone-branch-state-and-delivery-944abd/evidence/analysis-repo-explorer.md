# Repository and pull-request ancestry inventory

Date: 2026-09-01 UTC  
Route: `944abd96ddb3`  
Repository: `Dimkox/adaptive-grok-build-pro`  
Mode: read-only inventory after `git fetch --all --prune`

## Executive finding

`origin/main` is `1c06299894279a88b881defa3f19b004fa742223`. It contains M0 and the early M1 slices merged by PRs #4 and #8, but it does **not** contain the later full M1 implementation, M2, M3, M4, or the SEO side project.

The milestone work after PR #8 formed a stack whose merges targeted predecessor branches rather than `main`:

```text
origin/main 1c062998
  PR #8 -> main: M1 design/plan only, squash e81ae727

milestone/m1-typed-intent-evidence
  PR #10 -> this branch: full M1 implementation + M2, merge c23fd49

milestone/m2-executable-architecture
  PR #11 -> this branch: M3, merge 67714a1
  PR #17 -> this branch: M4, still open at 8e65041
```

Consequently, GitHub's `MERGED` state for PR #10 and PR #11 means merged into their stacked base branches, not delivered to the protected default branch.

## Evidence method

- Git refs were refreshed with `git fetch --all --prune`.
- Every GitHub pull request (#1 through #19) was read with `gh pr list --state all` and relevant PRs were expanded with `gh pr view`.
- Base/head/merge SHAs below are GitHub's recorded values, not inferred from local branch names.
- Delivery to `main` was checked from PR base, merge destination, commit/tree identity, `git merge-base`, `git rev-list --left-right --count`, and representative feature paths.
- PR #4, #5, #8, and #9 are squash merges: their PR-head tree equals the corresponding commit tree on `main`, even though the original PR head is not an ancestor by commit identity.

## M0-M9 authoritative delivery table

| Milestone | Branch / PR | GitHub-recorded base SHA | GitHub-recorded head SHA | PR result / check | Implemented and reviewed | Content in `origin/main` | Truthful status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | `milestone/m0-live-trust-authority`, PR #5 | `d17e95d9a99db2495c81f66053f0eebc7ae47d8d` | `9590db4db14838ab534958aaa0842f5523f043ae` | MERGED to `main` as `069fe8226addb8a1922dde3db4e753434baa3a3d`; epoch `6737355947c2` check SUCCESS | Yes; subsequent repairs PR #6 and #7 also merged to `main` | **Yes**. PR head and squash commit trees are identical. | Delivered to protected `main`; live authority facts later need epoch refresh from `6737355947c2` to current `06ecf1c875bc`. |
| M1 early typed-spec slice | `milestone/m1-typed-intent`, PR #4 | `3e140079c94e22a204b0805ac2e3b7774426f739` | `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4` | MERGED to `main` as `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` | One initial typed change-spec implementation commit | **Yes**; head and squash trees are identical. | Delivered partial M1 foundation. |
| M1 design/plan | `milestone/m1-typed-intent-evidence`, PR #8 | `069fe8226addb8a1922dde3db4e753434baa3a3d` | `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105` | MERGED to `main` as `e81ae72766972e1dda38f20bc7b3dece62319fd0`; epoch `6737355947c2` SUCCESS | Only two commits: design and implementation plan | **Yes**; head and squash trees are identical. | Delivered design/plan, despite the PR title suggesting the whole milestone. |
| M1 full implementation | Same remote branch later advanced to `c23fd49f80c7d1c74ca3393b6079a74f251a72d8`; implementation is included in PR #10's 100-commit delta | PR #10 base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105` | PR #10 head `022411b05924618cfde0cb97b8c8aff4955e6013` | PR #10 MERGED into the M1 branch as `c23fd49...`; epoch `06ecf1c875bc` SUCCESS | Yes; durable package state is `ready` and extensive independent review evidence exists | **No**. `origin/main...origin/milestone/m1-typed-intent-evidence` is `3 behind / 109 ahead`; full implementation files differ from `main`. | Implemented/reviewed and integrated into the stack, but not delivered to `main`. |
| M2 | `milestone/m2-executable-architecture`, PR #10; repair PR #16 merged into this branch first | `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105` | `022411b05924618cfde0cb97b8c8aff4955e6013` | MERGED into `milestone/m1-typed-intent-evidence` as `c23fd49f80c7d1c74ca3393b6079a74f251a72d8`; epoch `06ecf1c875bc` SUCCESS | Yes; architecture implementation and review packages exist; PR #10 also carried the post-PR-#8 M1 implementation | **No**. It never targeted `main`; current M2 remote head is later `67714a1...` after accepting M3. | Implemented/reviewed and merged one level in the stack, not default-branch delivered. |
| M3 | `milestone/m3-controlled-knowledge-debt`, PR #11 | `022411b05924618cfde0cb97b8c8aff4955e6013` | `1e73ff9b91d9b711cafccad7ccccb1a992d5e84d` | MERGED into `milestone/m2-executable-architecture` as `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`; epoch `06ecf1c875bc` SUCCESS | Yes; restacked on accepted M2 and independently reviewed | **No**. PR base was M2, not `main`; `origin/main...origin/milestone/m2-executable-architecture` is `3 behind / 147 ahead`. | Implemented/reviewed and merged into M2, not default-branch delivered. |
| M4 | `milestone/m4-durable-control-plane-accepted-m3`, PR #17 | `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` | `8e6504168462bbabad359fec3d23838c87f5ba22` | **OPEN / UNSTABLE**; GitGuardian FAILURE and `adaptive-trust-ci/verified@06ecf1c875bc` FAILURE | Source and local review package exist and package state says `ready`; GitHub exact-head gates are red | **No**. Remote branch is 164 commits ahead and 3 behind `origin/main`. | Implemented locally and opened, but neither accepted by Trust CI nor merged/delivered. Two local-only repair commits exist beyond the PR head. |
| M5 | No dedicated local/remote branch and no PR | — | — | — | No implementation/review evidence found | **No** | Roadmap/design only. |
| M6 | No dedicated local/remote branch and no PR | — | — | — | No implementation/review evidence found | **No** | Roadmap/design only. |
| M7 | No dedicated local/remote branch and no PR | — | — | — | No implementation/review evidence found | **No** | Roadmap/design only. |
| M8 | No dedicated local/remote branch and no PR | — | — | — | No implementation/review evidence found. `milestone/a-plus-autopilot` is a five-commit design/bootstrap branch with no PR, not proof of M8 implementation. | **No** | Roadmap/design only. |
| M9 | No dedicated local/remote branch and no PR | — | — | — | No implementation/review evidence found | **No** | Roadmap/design only. |

## Exact stack ancestry

### PR merge commits

| PR | Destination at merge | Merge SHA | Parents | Meaning |
| --- | --- | --- | --- | --- |
| #10 | `milestone/m1-typed-intent-evidence` | `c23fd49f80c7d1c74ca3393b6079a74f251a72d8` | `0a4dd0a...` + `022411b...` | The accepted M2 tree was merged into M1's branch after PR #8 had already merged to `main`. |
| #11 | `milestone/m2-executable-architecture` | `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` | `022411b...` + `1e73ff9...` | The accepted M3 tree was merged into M2, not into `main`. |
| #17 | `milestone/m2-executable-architecture` | none | base/head `67714a1...` / `8e65041...` | M4 correctly contains accepted M3: both current M2 and M3 remote heads are ancestors of the M4 head. |

Current branch relations:

- `origin/milestone/m2-executable-architecture` (`67714a1...`) is an ancestor of M4 remote head `8e65041...` with `0 / 17` left/right commits.
- `origin/milestone/m3-controlled-knowledge-debt` (`1e73ff9...`) is an ancestor of M4 remote head with `0 / 18` left/right commits.
- Current M1 remote `c23fd49...` and current M2 remote `67714a1...` differ by `1 / 39` because the merge destinations each gained their own merge commit; their contents form a stack but the branch heads are not a simple linear chain.

## Local versus remote branch drift

| Branch | Local head | Remote head | Local...remote counts | Assessment |
| --- | --- | --- | --- | --- |
| `main` | stale local branch `c54fd01588eb343eeecde7302fee514bf3e6090d` | `1c06299894279a88b881defa3f19b004fa742223` | local is 213 commits behind | Never use local `main` as live state; use refreshed `origin/main`. |
| `milestone/m0-live-trust-authority` | `29339bbba0bc76c7603b979c11430e2208f8e74d` | `9590db4db14838ab534958aaa0842f5523f043ae` | `12 ahead / 3 behind` | Diverged historical local branch; remote PR #5 head and main squash are authoritative for delivered state. |
| `milestone/m1-typed-intent` | `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4` | same | `0 / 0` | Synchronized historical branch. |
| `milestone/m1-typed-intent-evidence` | `25bfbe59ea188d9687b20a9caad19e7db3d031f8` | `c23fd49f80c7d1c74ca3393b6079a74f251a72d8` | `0 ahead / 88 behind` | Local worktree head is stale; remote includes PR #10. |
| `milestone/m2-executable-architecture` | `9493741dd34fdfa1e37efdc09b35e30d5535be7c` | `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` | `0 ahead / 44 behind` | Local head is stale; remote includes PR #16 and PR #11. |
| `milestone/m3-controlled-knowledge-debt` | `d4cc01fe8d6ec82cce93106191774fc32e8dbb46` | `1e73ff9b91d9b711cafccad7ccccb1a992d5e84d` | `0 ahead / 8 behind` | Local head is stale; remote is the accepted restack used by PR #11. |
| `milestone/m4-durable-control-plane-accepted-m3` | `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06` | `8e6504168462bbabad359fec3d23838c87f5ba22` | `2 ahead / 0 behind` | Local has unpublished `7520b33` and `cf0219b`; PR #17 and its failed checks remain bound to `8e65041`, not those repairs. |
| `feature/seo-landing-codex-main` | `ecc85d903d0394f99a139fd4e74a7cc452e386c6` | same | `0 / 0` | Synchronized open PR #19 head. |
| `feature/seo-landing-codex-side-project` | `514f6e35e7ae414c3703af420ac28293f868a0b7` | same | `0 / 0` | Historical PR #18 head, merged only into the already-merged repair branch. |

## SEO PR delivery truth

- PR #18 merged `feature/seo-landing-codex-side-project` (`514f6e35...`) into `fix/path-aware-shell-policy-circuit-breaker` as `341d72b3...` **after** PR #6 had already merged that repair branch to `main`. Therefore PR #18 did not deliver SEO content to `main`.
- PR #19 independently targets `main`, base `1c062998...`, head `ecc85d903d0394f99a139fd4e74a7cc452e386c6`. It is OPEN, merge state CLEAN, and both GitGuardian and `adaptive-trust-ci/verified@06ecf1c875bc` are SUCCESS.
- Until PR #19 merges, the SEO side project is tested and merge-eligible but not present in `origin/main`.

## All GitHub pull requests observed

| PR | State | Base <- head | Relevance |
| --- | --- | --- | --- |
| #1 | CLOSED, unmerged | `main` <- `hardening/trust-boundary-v2-1` | Superseded Actions-based trust boundary. |
| #2 | MERGED | `main` <- `feat/trust-ci-control-plane` | P0 Trust CI source. |
| #3 | MERGED | `main` <- `docs/dark-factory-roadmap` | M0-M9 roadmap. |
| #4 | MERGED | `main` <- `milestone/m1-typed-intent` | Early M1 typed-spec slice. |
| #5 | MERGED | `main` <- `milestone/m0-live-trust-authority` | M0 delivery. |
| #6 | MERGED | `main` <- `fix/path-aware-shell-policy-circuit-breaker` | M0-era repair. |
| #7 | MERGED | `main` <- `fix/trust-ci-workspace-integrity` | M0-era repair. |
| #8 | MERGED | `main` <- `milestone/m1-typed-intent-evidence` | Only M1 design/plan at recorded head. |
| #9 | MERGED | `main` <- `docs/fresh-agent-bootstrap` | Current stale bootstrap/status source. |
| #10 | MERGED | M1 branch <- M2 branch | Full M1 implementation plus M2 stack integration; not `main`. |
| #11 | MERGED | M2 branch <- M3 branch | M3 stack integration; not `main`. |
| #12 | OPEN/BLOCKED | `main` <- `fix/human-approval-cli` | Non-milestone repair; old epoch check ACTION_REQUIRED. |
| #13 | OPEN/BLOCKED | `main` <- `feat/trust-ci-repository-profiles` | Repository-profile feature; old epoch check ACTION_REQUIRED. |
| #14 | CLOSED, unmerged | `main` <- `policy/production-only-human-approvals` | Superseded/abandoned policy PR. |
| #15 | OPEN/BLOCKED | `main` <- `mvp/investor-ready` | Carries M1-M3-derived source plus demo, but no `factory/`; current epoch check FAILURE. It is not a substitute for milestone delivery. |
| #16 | MERGED | M2 branch <- `fix/m2-trust-ci-zombie-process-group` | M2 repair merged before PR #10. |
| #17 | OPEN/UNSTABLE | M2 branch <- M4 branch | M4; both current checks FAILURE. |
| #18 | MERGED | already-merged repair branch <- SEO side-project branch | Stacked SEO integration only, not `main`. |
| #19 | OPEN/CLEAN | `main` <- `feature/seo-landing-codex-main` | SEO delivery PR; current epoch and GitGuardian SUCCESS. |

## Reconciliation recommendations

1. `PROJECT_STATE.json`, `START_HERE.md`, and README must stop saying PR #8 is draft or that M1 implementation has not started. PR #8 merged on 2026-08-27, and the full implementation exists later in the stacked PR #10 history.
2. Represent milestone status with separate fields for `implemented`, `reviewed`, `integrated_into_branch`, and `delivered_to_main`; a single `completed` flag loses the critical stacked-merge distinction.
3. Record M0 delivered; M1 early foundation/design delivered but full M1 not delivered; M2/M3 stack-merged but not delivered; M4 open/red; M5-M9 roadmap-only.
4. Treat `origin/*` and GitHub PR recorded heads as authoritative. Do not use the stale local M1/M2/M3 heads or the two unpublished M4 commits in delivery claims.
5. Do not claim PR #17 fixed until its branch is updated and fresh exact-head checks pass. Local commits `7520b33` and `cf0219b` have no GitHub/Trust-CI authority.
6. Keep PR #19 separate from milestone state: it is green and clean but remains undelivered until merged.
7. The current live check epoch evidenced on new PRs is `adaptive-trust-ci/verified@06ecf1c875bc`; App ID remains `4694114`. Historical successful M0/M1 checks used epoch `6737355947c2` and must not be presented as the current required context.
