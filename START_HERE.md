# Fresh-agent bootstrap

The current published release is `v2.1.1`, published 2026-10-03T09:11:19Z from PR #238 at `97a7581238022356b2de8d193a9bd8363fc92dc3`. Release ZIPs and checksums are GitHub Release assets. It integrates A-E/H and the local heartbeat/watchdog; F durable evidence and separate G current-authority behavior remain required successors. The old core source candidate and exact prior `2.1.0` custody remain dated provenance in `PROJECT_STATE.json`. Current cleanup PR #241 supersedes PR #239 and requires fresh verification, independent review and external exact-head Trust CI. BB, rotator, VibeVM, FPF, prediction and Linux setup remain default-off and not live-qualified; U4/macOS remains excluded.

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## First action: measure resources and schedule independent work

**Step zero, before all other startup work:** complete and record CPU/capacity discovery before inspecting backlog/routes, planning dependencies, spawning agents or running heavy commands. Store the snapshot locally first and attach it to the active package after routing. Follow the [mandatory startup algorithm](AGENTS.md#mandatory-startup-algorithm-measure-then-dispatch):

1. Measure physical/online logical topology (`lscpu`, `nproc --all`), current capacity (`nproc`) and affinity. Resolve actual cgroup membership/mounts, effective cpuset and finite quota, including ancestor limits.
2. If permitted and appropriate, run a bounded child-only affinity-widening probe over verified CPU IDs, then inspect the child's affinity and limits. Derive effective CPU capacity from allowed online CPUs, cpuset and quota; unknown bounds require a conservative choice. Record timestamp, commands/results, bounds and chosen capacity in the active package, and remeasure when the environment changes.
3. Only after recording effective capacity, inspect the repository handoff/backlog/routes, build dependencies and dispatch all independent route-permitted work in parallel after its prerequisites. Spread eligible heavy child work over measured capacity without oversubscribing it. The observed host had **14 physical cores / 28 logical CPUs**; default affinity could expose 22, while `taskset -c 0-27 nproc` exposed 28 in a verified child. These are dated September 26 observations, not permanent guarantees.
4. Count agent slots separately: the current platform exposes **one controller + 12 child slots**, route `max_parallel_analysis=10` is a separate routing cap, and test workers are separate processes. Use only route-selected agents. Then keep one writer per isolated task/route/branch/worktree; independent isolated writers may run concurrently. Verification and delivery gates follow implementation.
5. Treat an explicitly delegated exact isolated-branch push before verification as **UNVERIFIED transport only**, with its exact local action/resource grant and unverified handoff label. Direct push to protected/shared branches remains forbidden. Merge requires a PR, App-owned exact-head Trust CI and all required approvals.

## Second mandatory startup step: select the verification scope

After the capacity snapshot and route/dependency scheduling above, record the trusted exact base/HEAD plus staged, unstaged and untracked inventory/statuses. Run bounded committed-HEAD observations before the independent selected reviews; observations create no verification receipt or scope admission. Persist all complete reports, commit and freeze, then invoke `python3 scripts/grok_verify.py --mode pr` once as the final qualifying local gate using the verified CPU allocation. The merged issue #205 / PR #207 [closed selector](.grok-stack/adaptive_grok/verification_scope.py) selects scope inside that run before its heavy checks; use the actual agreed PR base, not a shortened range that hides changes.

Its closed focused inventory admits the named docs/state paths, tracked `packages/**` release bytes, and exactly five binding test modules: `tests/test_structure.py`, `tests/test_project_state.py`, `tests/test_manifest_package.py`, `tests/test_workflow_sources.py` and `tests/test_repo_router.py`. For that admitted inventory, `docs-state-focused` skips the replaced full-discovery runner, coverage and `factory-postgres-exit`, not factory-unit or the other selected checks. All other executable changes (including factory/database/schema/contract/selector changes), non-admitted paths or ambiguous inventories require the full suite; "factory unaffected" is not a separate shortcut. Historical measurements were **629 s serial Core coverage versus about 14 s for the five focused modules**, not the complete verifier or a future timing guarantee.

Record exact base/head, dirty paths, profile/reason, changed-path digest and all skipped checks. Do not call skips passes or reuse: references to prior component evidence must retain their original exact Git identities and scope and be explicitly marked historical/reused; they grant no additional skips or current completion. `--full-scope` forces full. After exact delegated UNVERIFIED branch transport, the single final local gate and external App-owned exact-head Trust CI run in parallel; required approvals and protected PR delivery remain mandatory. Ten minutes is an unconfirmed target, and Core/PostgreSQL overlap is not implemented; see [the complete startup rule](AGENTS.md#second-mandatory-startup-step-select-verification-scope-before-heavy-work).

## Current project state

Historical core observation (pre-publication snapshot **2026-10-03**): historical `main` was `3f41be92161fef451a2dfa7451eb458ce8f022b3`, and the core comparison base was `63799f8760d3a55028d83ab5ff0116ececf8f7d1`; accepted packaging identity was unknown in that dated record. The known published identity is now bound separately by `published_release`: PR #238 and target `97a7581238022356b2de8d193a9bd8363fc92dc3`. Prior `2.1.0` custody was built twice from source `e5856acfd4bc7a186f40a740b54ec86459462db5` / tree `0dfa04f3ec3ea9c7a04c723e9d127603fc72999b`; fetch refs before assuming remote state.

- **Published release:** `v2.1.1` binds PR #238 head `4c5be3ab2370792e71bfa43a031d7f074cfb78f5` and merged/tag target `97a7581238022356b2de8d193a9bd8363fc92dc3`. App-owned check `111167969839` succeeded on that PR head; ZIP SHA-256 is `f5116c5e1303232ae883ed7a3aa804b71f0b5654d2c385924653b5ffd2d631c1`. Publication does not establish deployment or activation. Historical `2.1.0` custody retains its original hashes.
- **Source:** M0-M9 implementation is delivered. The seven-slice L5 production runtime landed through PR #75, with a [delivery ledger](engineering/reviews/l5-delivery-stack.json); the durable Qwen→Grok→OpenAI→Claude→OpenRouter failover arrived through PR #91 and the workflow artifact adapters plus the `workflow_sources` upstream version contract through PR #93 (change `20260915-update-third-party-workflow-components-superpowe-1b0c02`), all of them inside the observed source named above. Source defaults keep provider execution off.
- **Historical runtime (September 15–16):** on Claw, Qwen primary `adaptive-l5.service` at `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` and Grok secondary `adaptive-l5-grok.service` at `61a05da2bd0c9fb09db5307f53ebc99e4e94040d` were active and enabled. Both have authenticated `artifact_ready` evidence; Grok took **29.852 s** with `live_url=null`. Read the [dated runtime observation](engineering/runbooks/l5-runtime-observation-2026-09-15.md) for exact boundaries.
- **Latest runtime operation (September 19):** primary Qwen is accepted at `f12807c2b75750072ba768fc95ed492362ae6489` / `qwen-omni-intl`: one POST, `artifact_ready` in 4.991 s, usage 766/195, separate zero-POST readback. Grok stays accepted at `26a0d3d`; separate Omni remains unchanged. All three units are active/enabled. Read the [successful continuation record](engineering/runbooks/l5-primary-continuation-2026-09-19.md). The earlier failure/rollback remains historical, not the current installation.
- **Next unmet outcomes:** a full external pilot with maintainer acceptance, an exact-profile M8 qualifying cohort and activation, and general M9 operational qualification. The live L5 result proves bounded artifact generation, without proving these outcomes or factory publication of a public site.
- **Merge authority:** App-owned `adaptive-trust-ci/verified@06ecf1c875bc`, GitHub App ID `<redacted-app-id>`, on the exact up-to-date PR head. The deployed Trust CI service is separate from L5; repository tests and runtime success do not replace it.
- **Active delivery:** refresh actual PR #241 cleanup state on `feat/qg01-gate-artifact-admission` using the [cleanup package](engineering/changes/20261004-fix-pr-239-public-cleanup-verifier-blockers-arch-6af9e6/brief.md) and `PROJECT_STATE.json.current_continuation`; its confirmed repairs are already in this tree and PR #239 is superseded. The separate [PR #240 dependency](https://github.com/Dimkox/adaptive-grok-build-pro/pull/240) is merged at actual comparison base `6dbbc7dbe81812d919851c2300db6f4917033d43`. If PR #241 is merged, record delivery and treat unchanged source as a no-op without reopening or reverifying; if open, complete frozen independent review, persist complete reports, run one final full verification on the report-containing head, and require fresh receipts, external exact-head Trust CI and approvals. Neither an old check nor a historical next-action field authorizes another `v2.1.1` artifact/tag/release.

Historical planning links: the [core package](engineering/changes/20261002-assemble-2-1-1-factory-source-with-heartbeat-and-ffb3d8/brief.md) and [release-wide ledger](engineering/changes/20261002-assemble-2-1-1-factory-source-with-heartbeat-and-ffb3d8/release-scope-ledger.md) retain the dated conditional design, not current delivery instructions. F/G successors and external pilot qualification remain unaccepted. PR #173 and PR #12 remain historical delivered work; the optional SEO side project was delivered through PR #19.

Machine-readable handoff: [`PROJECT_STATE.json`](PROJECT_STATE.json). `fresh_clone.continuation_record` selects `current_continuation`; `active_delivery`, `current_unreleased_change` and `active_source_delivery` are labelled historical, so their old next-action fields are not instructions. `published_release` binds immutable `v2.1.1`; the prior `v2.0.19` record is preserved verbatim in `prior_published_releases`. `local_candidate` is explicitly historical pre-publication provenance. `historical_v2_1_0_artifact_custody` preserves all three original custody/delivery records exactly. Historical source, delivery and runtime records remain dated evidence and do not imply operational activation.

The earlier [dated backlog](engineering/changes/20260921-research-open-backlog-map-each-item-to-its-sourc-d54d3a/issue-queue.json) remains historical; the latest recorded counts and scope live in `PROJECT_STATE.json` (its nested issue inventory is dated separately). The [accepted CI ingress operation](engineering/changes/20260921-fix-production-trust-ci-webhook-ingress-and-rest-68274/evidence/operational-acceptance.md) restored actual GitHub intake; [PR #173 delivery](engineering/changes/20260921-fix-the-combined-source-delivery-of-issue165-int-cf2384/evidence/pr173-delivery.json) records the later external result. Separate #158 source has focused and complete Trust CI suite evidence but still needs current-main integration, the full route gate, reviews and eventual separately authorized live acceptance.

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
3. Continue from `PROJECT_STATE.json.current_continuation` after fetching remote state, then inspect its dated source/runtime/release observations, the open-work inventory and [runtime runbook](engineering/runbooks/l5-production-runtime.md). Historical milestone branches and release-preparation records are evidence, not current continuation instructions.
4. If starting a different software-development task, create/resolve the local route first. `.grok-stack/runtime/active-route.json` is runtime state and may legitimately be absent in a fresh clone; do not fabricate it.
5. Follow `AGENTS.md`: measured parallel-first scheduling, one write owner per isolated task/route/branch/worktree, route-selected agents, local verification as evidence, and PR-only merge through external Trust CI and required approvals. Explicitly delegated pre-verification branch transport remains labelled UNVERIFIED.
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

The source and runbooks for the independent merge authority are under `trust-ci/` and `engineering/runbooks/`. The live CI host is `<ci-host>`; its public inbound GitHub App webhook reaches the service through the documented Tailscale Funnel, while the API listener itself is loopback-bound on the host. These are operator-safe facts only; credentials are not repository content.

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
