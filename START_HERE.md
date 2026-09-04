# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- Product source identity is the local unpublished source-ready candidate `2.0.14`; latest published release `v2.0.13` remains immutable at ZIP SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`. Ready-state checkpoint `R` (this bookkeeping commit) is the package source parent and contains no `2.0.14` product pair; artifact child `A` is exactly `R` plus `packages/adaptive-grok-build-pro-v2.0.14.zip` and its `.sha256` sidecar, whose tracked presence and binding are authoritative in `A`.
- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- Protected `origin/main` is currently `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`; the historical PR #22 / `v2.0.13` merge remains `8599d45f4f28285381b05a53feb3059de92eb2a8`. It requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1-M3 are implemented, reviewed and delivered to `main` through PR #22. Their earlier PR #4/#8 partial delivery and PR #10/#11 predecessor-stack acceptance remain historical evidence; exact M1/M2 head `022411b05924618cfde0cb97b8c8aff4955e6013`, M3 head `1e73ff9b91d9b711cafccad7ccccb1a992d5e84d` and aggregate `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` are ancestors of the checked release head.
- M4-M9 are likewise implemented and delivered to `main` as repository product source through PR #22, preserving migrations `001`-`018`. Execution and delivery remain disabled by default, and no operational provider, persistent deployment, network capability, systemd activation, or production authority is present.
- PRs #12/#13 remain old-epoch `ACTION_REQUIRED`; their unique lazy CLI import/tests and repository-scoped Trust CI profiles are absent from `main`. PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`; the cause was not inspected or inferred. PR #21 remains open at `571cad7877431ac5ab5779b53fe9f7effd6859ce`, with Trust CI `FAILURE` and GitGuardian `FAILURE`; neither result is diagnosed or dismissed here.
- PR #22 checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9` passed `adaptive-trust-ci/verified@06ecf1c875bc` as check run `100955508827` with attestation `74f1bbb2-3098-4d35-a42f-d49351d81c4a`, then merged at `2026-09-04T08:31:49Z` as main commit `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.
- Current work is route `9f67efd2575c` on `feature/l5-multimodal-landing-factory`: the composite local source gate and four route-selected reviews pass, and this commit records ready checkpoint `R`. If the declared pair is absent, next build it twice in private no-local clones from `R` and create child `A` with exactly those two paths; if present, the tree is `A` and proceeds to its artifact-bound gate. The provider and publisher are unavailable by default; no network, target mutation, hosting action, live/indexed claim, or production effect is authorized. M8 cohort/activation and real M9 operational qualification remain separate gaps.

Machine-readable handoff: [`PROJECT_STATE.json`](PROJECT_STATE.json).

## Bootstrap from a clean clone

1. Start on the default branch and read, in order:
   - `START_HERE.md`
   - `PROJECT_STATE.json`
   - `AGENTS.md`
   - `decisions.md`
   - `mistakes.md`
   - `DARK_FACTORY_ROADMAP.md`
   - `README.md`
2. Run `git fetch --all --prune` before reasoning about active branches or pull requests.
3. Inspect `PROJECT_STATE.json`, its separate local `2.0.14` candidate and published `v2.0.13` records, the active L5 change package, and open PRs #12, #13, #15 and #21 before continuing work. Treat M4-M9 predecessor branches as historical integration evidence; protected-main delivery remains PR #22 merge `8599d45f4f28285381b05a53feb3059de92eb2a8`.
4. If starting a different software-development task, create/resolve the local route first. `.grok-stack/runtime/active-route.json` is runtime state and may legitimately be absent in a fresh clone; do not fabricate it.
5. Follow `AGENTS.md`: one write owner, route-selected analysis/review agents, local verification as evidence, pull-request-only delivery, and external Trust CI as merge authority.
6. Never add GitHub Actions.
7. Never bypass the exact-SHA App-owned Trust CI check.

## What is intentionally not in Git

A clean clone contains all source, contracts, roadmap, durable change artifacts, runbooks, public operational facts, and agent handoff needed to understand and continue development. It intentionally does **not** contain secrets or machine-local runtime material, including:

- `.env` files and credentials;
- GitHub App private keys;
- human approval private keys;
- Trust CI signing keys or trust-store private material;
- PostgreSQL runtime state;
- temporary approvals/receipts under runtime directories;
- host-local Docker/socket overlays and other machine-specific deployment scratch.

Do not try to reconstruct missing secrets from repository history or chat. Public/operator-safe deployment facts belong in `engineering/runbooks/`; secrets remain outside Git.

## Live Trust CI orientation

The source and runbooks for the independent merge authority are under `trust-ci/` and `engineering/runbooks/`. The live CI host is `claw`; its public inbound GitHub App webhook reaches the service through the documented Tailscale Funnel, while the API listener itself is loopback-bound on the host. These are operator-safe facts only; credentials are not repository content.

Before changing Trust CI behavior, read the current deployed-policy/holdout constraints in `AGENTS.md` and the activation/rollout runbooks. Repository code cannot itself alter deployed trust material.

## Current milestone delivery handoff

Use one repository-level delivery ledger and one consolidated continuation route. Existing branches are evidence and integration inputs; their names, local `ready` files and GitHub `MERGED` labels do not prove protected-main delivery.

1. Treat the exact M4-M9 lineage named above as repository product delivered by PR #22, not as operational activation or production deployment.
2. Treat the corrected M8 checkpoint `a937ac8d200a4e143c295fabd482b19bc8cc4286` as the exact M9 predecessor; it restores the frozen M4 control contract and separates the additive M6 semantic API without changing migrations `001`-`018`.
3. Keep the published ZIP bound to tag `v2.0.13` and SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`; documentation-only successors do not rebuild it.
4. Preserve PR #22's exact checked-head/App-check/merge evidence as historical delivery authority; local receipts remain preflight evidence only.
5. Do not describe M8 as active until the exact-profile factual cohort and activation record exist, and do not describe M9 as operational until signed inputs, an environment, exercised recovery and human production authority exist.
6. Treat L5 landing output only as a deterministic local artifact candidate. The exact landing source clone stays read-only, the default provider/publisher stays unavailable, and production requires separate provider, Trust CI, signing, hosting, rollback and explicit external-action authority.
7. Retain open PRs #12, #13, #15 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; extract unique work through clean successors without claiming those successors exist. PR #17 is a closed exact duplicate of #21, and PR #19 is already delivered with its predecessor staging path archival.
8. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
