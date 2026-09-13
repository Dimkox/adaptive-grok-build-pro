# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- The seven-slice L5 production runtime is delivered on `main`: PR #75 merged the union of slices #65-#71 at `2026-09-13T17:35:51Z` as `eb9df64bca333f30ec58f8c725a021360e22ed92`, whose tree `1c8d72a50c0631c0222d111de1403ace4347aab2` is identical to the externally attested G head `e6a813e4c16543f262ced2d9ea353caaad9452d1`. Slice A landed separately as `ede668603156b48432c2209e0242b85e17837d0e` (#65), #66-#70 closed as landed-by-content and #71 as superseded by the union; each exact head carries its own passing `adaptive-trust-ci/verified@06ecf1c875bc`, including the union head `ac7ae2def67a267c227ab5703843337d4bb6f4be` (check run `103760385178`, completed `2026-09-13T17:33:02Z`). Resume from [the delivery ledger](engineering/reviews/l5-split-delivery.md) and its [machine-readable form](engineering/reviews/l5-delivery-stack.json), both landed by PR #72 as `e737dd5c338793e274285d657354e74ecc812f89`, plus [the G package](engineering/changes/20260913-l5-split-g-final-base-offline-recovery-and-assem-2a890b/brief.md) and its evidence policy. Frozen monolith `f31406e970d67f7cd59694da5de88915adb0fa68` and PR #49 are reconstruction history. This landing is source only: no runtime was installed, no provider or service was activated, no public site exists and no release artifact was produced.

- Product identity `2.0.16` is the release candidate awaiting its tag: the release-sync commit raised `VERSION`, `CHANGELOG.md` and `PROJECT_STATE.json`, and the artifact child delivers the `2.0.16` ZIP+sidecar bytes; no `v2.0.16` tag or GitHub Release exists yet, and both will bind to the merged artifact-child commit under exact delegated grants. The latest published repository release is tag-bound `v2.0.15`, whose tag target is `fd51dcfed6b33f4a8707c0db602328146df17cc9`, published at `2026-09-05T20:17:20Z` with ZIP SHA-256 `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7`; published `v2.0.15`/`v2.0.14`/`v2.0.13` artifacts are immutable.
- Current work is that `v2.0.16` release-sync — one identity/state catch-up to the landed tree, then tag and publication under exact delegated authority — plus the post-landing follow-ups: PR #33 (parallelize local Python verification), issue #59 (`grok_verify` writes into the tree it verifies, so a bare `uv run` re-resolve trips its own source-stability guard and hides manifest/lock drift) and issue #61 (the deploy inventory must never publish internal documents such as `SERVER-SETUP.md` and `ASSETS.md`), whose production-scope prohibited-member guard landed with PR #77; the remaining `deploy_inventory_policies` fitness rule stays a follow-up.
- The pilot vertical published as `v2.0.15` is route `0ce2d62a018e`, delivered to `main` through PR #27 from `feature/design-partner-pilot` with exact predecessor `6f3b6ed2853b7a6f78804888cffca578d4dc9448`: the separate `pilot/` component binds issue #1 and any candidate to `Dimkox/ai-dark-factory-landing@699010380f4f90a0193a9c22090c35e6aded7d2c`. Its built-in CLI is default-unavailable and exposes only `prepare`, `publish-branch`, `publish-proposal` and read-only `status`; a closed pinned config selects one Codex app-server `gpt-6-astra` turn through opaque host ChatGPT auth, while deterministic private workspace recovery and SQLite intents make ambiguous external effects observation-only. Focused fake evidence covers the direct composition, and the artifact child that shipped `v2.0.15` passed the App-owned exact-SHA gate itself (head `9fcc9d943c74260c02a920a59490143f91cb38b2`, check run `101365945968`); the separately authorized real model/branch/PR attempt has not occurred and stays blocked by the landing target advancing to `80d6215`.
- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- At the `2026-09-04T16:58:48Z` publication snapshot, protected `origin/main` and tag `v2.0.14` pointed to `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`; this is not a perpetual current-ref assertion. The historical PR #22 / `v2.0.13` merge remains `8599d45f4f28285381b05a53feb3059de92eb2a8`. Protected merges require `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1-M3 are implemented, reviewed and delivered to `main` through PR #22. Their earlier PR #4/#8 partial delivery and PR #10/#11 predecessor-stack acceptance remain historical evidence; exact M1/M2 head `022411b05924618cfde0cb97b8c8aff4955e6013`, M3 head `1e73ff9b91d9b711cafccad7ccccb1a992d5e84d` and aggregate `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` are ancestors of the checked release head.
- M4-M9 are likewise implemented and delivered to `main` as repository product source through PR #22, preserving migrations `001`-`018`. Execution and delivery remain disabled by default, and no persistent deployment or production authority is present. The later L5 landing added bounded HTTP/media live executors (`factory/src/adaptive_factory/landing_live_executors.py`, `landing_http.py`, `landing_media.py`) plus the inert `factory/runtime/install-claw.sh` and `factory/runtime/adaptive-l5.service.in` templates, so network capability and systemd activation exist as source but stay unavailable: `landing_live_enabled` defaults to `False` in `factory/src/adaptive_factory/settings.py`, the installer was never executed and no unit is installed, enabled or started.
- PR #12 merged at `2026-09-12T04:36:41Z` as `4eb16d2ca20091dd017a82f58906671510497bc5`, so its isolated human-approval CLI imports and tests are on `main`. PR #13 remains open with `adaptive-trust-ci/verified@06ecf1c875bc` and GitGuardian both `SUCCESS` on head `9bdffde938b35fefe18b12f77a369b69af80e726`, and its repository-scoped Trust CI profiles are still absent from `main`. PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`; the cause was not inspected or inferred. Stale PR #21 was closed as superseded at `2026-09-05T12:07:24Z` after PR #22/#24 delivery; its Trust CI and GitGuardian `FAILURE` conclusions remain preserved historical facts.
- PR #22 checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9` passed `adaptive-trust-ci/verified@06ecf1c875bc` as check run `100955508827` with attestation `74f1bbb2-3098-4d35-a42f-d49351d81c4a`, then merged at `2026-09-04T08:31:49Z` as main commit `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.
- Route `9f67efd2575c` was delivered as additive non-milestone repository work through PR #24: checked head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` merged at `2026-09-04T16:56:37Z` as `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`, tree `618df086920c92179aa0e22a8c8d4ad30ebd9230`, and release `v2.0.14` was published at `2026-09-04T16:58:48Z`. No repository-release action remains for that published tree; the current repair is separately tracked, the provider/publisher defaults are still unavailable, and operational provider, hosting, live/indexed-site, M8 cohort/activation and real M9 qualification require separate evidence and authority.

Machine-readable handoff: [`PROJECT_STATE.json`](PROJECT_STATE.json).

Historical pilot continuation (separate from current L5 delivery): the original `2405b013` artifact received failing reviews; CSP, test-discovery and command read-isolation repairs are tracked in the active package's bounded review-repair handoff. Primary `/root` is the user-approved sole fallback writer after the agent-thread ceiling. Preserve original full-verifier/targeted-recovery evidence, verify only affected components on the rebuilt exact artifact child, and reuse the three independent reviewers. The first live attempt is separately blocked by landing `main` advancing to `80d6215`; no model turn has been consumed and the old profile must not overwrite newer analytics.

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
3. Inspect `PROJECT_STATE.json`, its `l5_production_preparation` and historical `current_unreleased_change`, the delivered design-partner pilot package, published `v2.0.15`, prior `v2.0.14`/`v2.0.13` history, the landed [L5 delivery ledger](engineering/reviews/l5-split-delivery.md), and the recorded open-work inventory before continuing. Treat M4-M9 predecessor branches as historical integration evidence; their `v2.0.13` protected-main delivery remains PR #22 merge `8599d45f4f28285381b05a53feb3059de92eb2a8`.
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
3. Keep each published ZIP bound to its release tag: `v2.0.15` / `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7`, `v2.0.14` / `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264` and historical `v2.0.13` / `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`; documentation-only successors do not rebuild any of these artifacts, and a `2.0.16` ZIP does not exist until it is deliberately built and tagged.
4. Preserve PR #22's exact checked-head/App-check/merge evidence as historical delivery authority; local receipts remain preflight evidence only.
5. Do not describe M8 as active until the exact-profile factual cohort and activation record exist, and do not describe M9 as operational until signed inputs, an environment, exercised recovery and human production authority exist.
6. Treat L5 as landed `main` source plus a distinct Stage 3/5 single-operator local runtime still awaiting its `v2.0.16` tag, not an operational site. The landing source clone stays read-only, provider and publisher defaults stay unavailable, the installer and service templates stay inert, and live model use, cPanel, hosting, production and other external effects require separate evidence and authority.
7. Retain open PRs #13, #15, #33 and #64 plus the local work identified in `PROJECT_STATE.json`; PR #77 delivered the post-landing hardening to `main` as `1a8c891`; extract unique work through clean successors without claiming those successors exist. PR #12 is delivered to `main` as `4eb16d2ca20091dd017a82f58906671510497bc5` and PR #14 is closed, both retained as history; PR #72 delivered the L5 evidence ledger and PR #75 the runtime itself. PR #17 is a closed exact duplicate of now-superseded PR #21, and PR #19 is already delivered with its predecessor staging path archival.
8. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
