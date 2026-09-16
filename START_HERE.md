# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

Snapshot: **2026-09-16**. Repository `main` was observed at `fc8d9e6f11bb188ee514784d3b6f614a6da72803` (PR #107, release-sync merge); fetch refs before assuming it is still the tip.

- **Released:** product `2.0.17`, tag [`v2.0.17`](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.17), published `2026-09-16T01:17:14Z`, target `c86b1a1989ace899a4450bde558fcd8adc00e4e2`, tag object `5c6687ed97e1c365597bf27047016eb07411f28b`, ZIP `770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616`. The earlier `v2.0.16` release stays immutable; nothing in this tree rebuilds a published artifact. Product identity `2.0.18` is now the **unpublished candidate** recorded in `current_unreleased_change` and `local_candidate`: its ZIP and sidecar are now tracked bytes built from the merged release-sync tree, while its tag and GitHub Release do not exist; each publication step requires its own exact delegated grant.
- **Source:** M0-M9 implementation is delivered. The seven-slice L5 production runtime landed through PR #75, with a [delivery ledger](engineering/reviews/l5-delivery-stack.json); the durable Qwen→Grok→OpenAI→Claude→OpenRouter failover arrived through PR #91 and the workflow artifact adapters plus the `workflow_sources` upstream version contract through PR #93 (change `20260915-update-third-party-workflow-components-superpowe-1b0c02`), all of them inside the observed source named above. Source defaults keep provider execution off.
- **Installed runtime:** on Claw, Qwen primary `adaptive-l5.service` at `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` and Grok secondary `adaptive-l5-grok.service` at `61a05da2bd0c9fb09db5307f53ebc99e4e94040d` were active and enabled. Both have authenticated `artifact_ready` evidence; Grok took **29.852 s** with `live_url=null`. Read the [dated runtime observation](engineering/runbooks/l5-runtime-observation-2026-09-15.md) for exact boundaries.
- **Next unmet outcomes:** a full external pilot with maintainer acceptance, an exact-profile M8 qualifying cohort and activation, and general M9 operational qualification. The live L5 result proves bounded artifact generation, without proving these outcomes or factory publication of a public site.
- **Merge authority:** App-owned `adaptive-trust-ci/verified@06ecf1c875bc`, GitHub App ID `4694114`, on the exact up-to-date PR head. The deployed Trust CI service is separate from L5; repository tests and runtime success do not replace it.
- **Other work:** PR #12 is delivered; PR #19 delivered the optional SEO side project. No pull request is open at this observation: PR #33 (parallel local Python verification) was closed without merging on 2026-09-16T07:21:05Z with its diagnosis recorded on the pull request, PR #15 was closed unmerged on 2026-09-15T20:02:30Z, and PRs #13, #64 and #94 are merged into the observed source. Their displayed checks are historical observations, not fresh merge eligibility. Preserve the unresolved work inventory in [`PROJECT_STATE.json`](PROJECT_STATE.json).

Machine-readable handoff: [`PROJECT_STATE.json`](PROJECT_STATE.json). `runtime_observations` records installed services, `published_release` binds the immutable release, `operational_qualification` records unproven outcomes, and `delivered_change_history` archives completed preparation, including every pull request merged after the publication. `current_unreleased_change` and `local_candidate` describe the `2.0.18` candidate and assert that its artifact bytes do not exist yet; the published `v2.0.17` candidate record is archived verbatim under `delivered_change_history.v2_0_17_release_preparation.published_local_candidate`; `operational_activation` remains false, and each new task opens its own change package. A release chain's own commits are **not** landing rows: the release-sync and artifact-child commits are identified by `current_unreleased_change` and `local_candidate`, and the publication itself by `published_release`/`active_delivery`, while `delivered_change_history.post_v2_0_17_landing` lists only what landed on `main` between publications. One explicit exception is recorded rather than hidden: row #81 is the v2.0.16 successor, which that chain chose to log as a landing row; the v2.0.17 successor (#100) is not in the ledger and is referenced only through the release records.

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
3. Inspect `PROJECT_STATE.json`, its dated source/runtime/release observations, the open-work inventory and [runtime runbook](engineering/runbooks/l5-production-runtime.md). Historical milestone branches and release-preparation records are evidence, not current continuation instructions.
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

1. Continue from fetched source and the dated state model. M0 is delivered and live; M1-M9 are delivered repository source. Keep their historical exact-head evidence and migrations `001`-`018` intact.
2. Preserve tag-bound ZIPs and sidecars for `v2.0.16`, `v2.0.15`, `v2.0.14` and `v2.0.13`; the machine-readable release records carry their hashes. Documentation successors do not rebuild released artifacts.
3. Treat the installed Qwen and Grok service SHAs separately from the latest source and release tag. Source defaults remain off; these observed instances were explicitly enabled. New provider, installation, publication or hosting effects require their own exact authority.
4. To continue the external pilot, inspect the [delivered pilot package](engineering/changes/20260905-feature-implement-a-single-operator-codex-github-0ce2d6/brief.md) and [pilot runbook](engineering/runbooks/design-partner-pilot-v2.0.15.md), refresh the target baseline and policy, then record the full result and maintainer acceptance. Earlier blocked attempts and fake/local tests cannot substitute for that outcome.
5. Do not mark M8 active without its factual qualifying cohort and activation record. General M9 qualification requires signed inputs, the applicable environment/provider deployment, exercised recovery and human production authority. The bounded L5 runtime observation does not supply those gates.
6. Refresh exact head/base and required external checks before extracting or delivering retained PR work. After every protected-main merge, update the dated state and recheck branches whose base changed. Never promote a historical success into current authority.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
