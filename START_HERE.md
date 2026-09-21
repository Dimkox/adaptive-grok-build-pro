# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Active issue branch — #166

This isolated successor to PR #170 adds real current-prefix migration tests. Read [the change package](engineering/changes/20260921-test-issue-166-ship-a-postgresql-current-prefix-af166e/brief.md) and `PROJECT_STATE.json.active_issue_work`. Three focused PostgreSQL tests, full PR verification and code/test/data reviews passed for the recorded product commit. Check fingerprint-bound local receipts for the final checkout before delivery; an external Trust CI check is still required.

## Current project state

Snapshot: **2026-09-21**. Repository `main` was observed at `90078959ff816068af374ad42f4bb80fdbaec866` (PR #151); fetch refs before assuming it is still the tip.

- **Released:** product `2.0.18`, tag [`v2.0.18`](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.18), published `2026-09-16T13:52:24Z`, target `e7d0f72bf834b75eb543d9424ee47c7829cc65c0`, tag object `31d3171f651ea77e29de58d4affc58d008f1c7a5`, ZIP `0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a`. The earlier `v2.0.17` release stays immutable; nothing in this tree rebuilds a published artifact, and no release preparation remains.
- **Source:** M0-M9 implementation is delivered. The seven-slice L5 production runtime landed through PR #75, with a [delivery ledger](engineering/reviews/l5-delivery-stack.json); the durable Qwen→Grok→OpenAI→Claude→OpenRouter failover arrived through PR #91 and the workflow artifact adapters plus the `workflow_sources` upstream version contract through PR #93 (change `20260915-update-third-party-workflow-components-superpowe-1b0c02`), all of them inside the observed source named above. Source defaults keep provider execution off.
- **Historical runtime (September 15–16):** on Claw, Qwen primary `adaptive-l5.service` at `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` and Grok secondary `adaptive-l5-grok.service` at `61a05da2bd0c9fb09db5307f53ebc99e4e94040d` were active and enabled. Both have authenticated `artifact_ready` evidence; Grok took **29.852 s** with `live_url=null`. Read the [dated runtime observation](engineering/runbooks/l5-runtime-observation-2026-09-15.md) for exact boundaries.
- **Latest runtime operation (September 19):** primary Qwen is accepted at `f12807c2b75750072ba768fc95ed492362ae6489` / `qwen-omni-intl`: one POST, `artifact_ready` in 4.991 s, usage 766/195, separate zero-POST readback. Grok stays accepted at `26a0d3d`; separate Omni remains unchanged. All three units are active/enabled. Read the [successful continuation record](engineering/runbooks/l5-primary-continuation-2026-09-19.md). The earlier failure/rollback remains historical, not the current installation.
- **Next unmet outcomes:** a full external pilot with maintainer acceptance, an exact-profile M8 qualifying cohort and activation, and general M9 operational qualification. The live L5 result proves bounded artifact generation, without proving these outcomes or factory publication of a public site.
- **Merge authority:** App-owned `adaptive-trust-ci/verified@06ecf1c875bc`, GitHub App ID `4694114`, on the exact up-to-date PR head. The deployed Trust CI service is separate from L5; repository tests and runtime success do not replace it.
- **Active delivery:** finish issue #155 on branch `fix/issue-155-repair-binding-rejections`, approved route `c4e47ea3ced7`, following its [continuation plan](engineering/changes/20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e/continuation.md). The local implementation names repair-child guard refusals through additive migration `021`; the corrected product passed full verification, four consecutive PostgreSQL runs and independent code/test/security/data review. The reviewed local handoff is ready for final clean-commit receipt binding and separately authorized PR publication. PR #151 merged on September 19 at 20:27:56 UTC; source repair PR #154 is also merged. Other retained PRs remain separate work. Historical delivered work includes PR #12 and the optional SEO side project PR #19.

Machine-readable handoff: [`PROJECT_STATE.json`](PROJECT_STATE.json). `latest_source_observation` names fetched main, `active_source_delivery` names the #155 continuation, and `active_operation_delivery` records the delivered PR151 operation; `latest_runtime_operation` records the newest installation outcome; top-level `observed_at`/`observed_main_sha` and `active_delivery` preserve the immutable September16 release snapshot; `runtime_observations` preserves the September 16 historical service observation, `published_release` binds the immutable release, `operational_qualification` records unproven outcomes, and `delivered_change_history` archives completed preparation, including every pull request merged after the publication. `current_unreleased_change` and `local_candidate` record the published `v2.0.18` release, including the tag object and artifact digests; the published `v2.0.17` candidate record remains archived verbatim under `delivered_change_history.v2_0_17_release_preparation.published_local_candidate`; `operational_activation` remains false, and each new task opens its own change package. A release chain's own commits are **not** landing rows: the release-sync and artifact-child commits are identified by `current_unreleased_change` and `local_candidate`, and the publication itself by `published_release`/`active_delivery`, while `delivered_change_history.post_v2_0_17_landing` lists only what landed on `main` between publications. One explicit exception is recorded rather than hidden: row #81 is the v2.0.16 successor, which that chain chose to log as a landing row; the v2.0.17 successor (#100) is not in the ledger and is referenced only through the release records.

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
4. To continue the external pilot, start with the [September 21 target investigation and successor issue draft](engineering/changes/20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e/next-pilot/README.md). The old issue targets an obsolete site, and its PR was closed unmerged. Current target `6226aa0` has a reproduced browser-audit coverage gap for two Russian pages. Route a separate successor profile/gate change around that bounded task; the [delivered pilot package](engineering/changes/20260905-feature-implement-a-single-operator-codex-github-0ce2d6/brief.md) and [pilot runbook](engineering/runbooks/design-partner-pilot-v2.0.15.md) remain historical context. Record the actual result and maintainer acceptance. Earlier blocked attempts and fake/local tests cannot substitute for that outcome.
5. Do not mark M8 active without its factual qualifying cohort and activation record. General M9 qualification requires signed inputs, the applicable environment/provider deployment, exercised recovery and human production authority. The bounded L5 runtime observation does not supply those gates.
6. Refresh exact head/base and required external checks before extracting or delivering retained PR work. After every protected-main merge, update the dated state and recheck branches whose base changed. Never promote a historical success into current authority.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
