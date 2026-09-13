# Seven-PR L5 split: baseline and route audit

Read-only audit in `/home/pall/grok-projects/adaptive-grok-build-pro-l5-production`. Source freeze: `f31406e970d67f7cd59694da5de88915adb0fa68`; source Git tree: `b1cfbfd92be13b43480adab9874ed78e67f5e948`. Locally known `origin/main`: `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`. No network calls, source/config changes, route changes or Git mutations were performed by this analysis. Only this report was written.

## Baseline facts

- The source worktree was clean at the frozen commit. Its branch is `feat/l5-production-completion`.
- The locally known remote-main commit is an ancestor of the source; merge-base equals `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`. `git rev-list --left-right --count BASE...SOURCE` returned `0 13`. Source history includes merge `2a0de0f` incorporating the later main line into the original `a730ee9`-based L5 work.
- Local `refs/heads/main` is stale at `be752872f3e5a9d6fe179872d9c8bdaec4338238` in `/home/pall/grok-projects/agbp-main`. Do not use that branch as the split baseline. The parent is independently refreshing origin/main.
- There are 165 added/modified paths from locally known main to the source: 124 additions and 41 modifications; no deletions or mode changes. They divide into 59 implementation/configuration/contract/test paths, nine shared documentation/handoff paths (including factory/README.md), and 97 paths in the original L5 change package.
- No delta exists under `trust-ci/`, `.github/`, `AGENTS.md`, `VERSION`, `factory/contracts/openapi/`, or the provider-evidence v1 schema. The old route's trust/implementation separation failure includes work before current main; copying the actual main-to-source delta does not carry those trust-ci changes.

## Unrelated-change assessment and parity target

No unrelated product delta was found in the actual main-to-source comparison. Files outside landing module names are supporting changes: the boundary evaluator/schema/regression changes serve the L5 I/O repair; semantic tests enumerate the added evidence-v2 schema; factory test bootstrap exposes sibling delivery/governance code for operator tests; general server/settings/API hunks add default-off L5 composition and landing-only routing. PROJECT_STATE/README/START_HERE/memory additions all describe L5.

The source freeze must remain intact as archival provenance. The final reconstructed stack must preserve all 59 implementation/configuration/contract/test path contents and modes listed in the manifest below, unless a separately justified, tested correction is recorded. Existing frozen files outside that delta must remain at the current-main state. The nine shared docs need truthful per-slice/final state and links, so byte differences caused by fresh route/change identities are expected and should be explained. Do not copy statements claiming monolith readiness into fresh slice records.

The 97 original change-package paths are historical evidence bound to the old route/head, not fresh evidence for any child. Preserve their provenance through the frozen source commit and source-delta manifest; if copied into delivered history, clearly retain their historical status. New slice packages and receipts add legitimate files beyond source-tree equality. Full-tree equality with the monolith is therefore not the completion criterion: exact implementation projection plus explicit documentation/evidence differences is.

If refreshed main advances, preserve every unrelated main change. Compare `OLD_BASE..NEW_MAIN` against the 59-path implementation projection. Any overlap requires a deliberate three-way integration; do not overwrite a current-main file with the frozen source blob merely to satisfy parity. Record overlap resolutions and rerun the affected tests. The source tree is a feature-content target, not authority to revert newer main.

## Reconstruction boundaries

Keep the approved A-G ordering from `engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-delivery-split.md`:

| Slice | Content | Critical shared hunks |
| --- | --- | --- |
| A | Boundary exception semantics, qualified imports, evolving I/O completeness tests | Architecture-model test optional-field assertion belongs here; its evidence-v2 catalog additions belong to C. Do not predeclare future source paths. |
| B | Sealed source epoch and old/new retained layouts | Retention source-layout hunks only; v2 reader/disposition hunks wait for C. Include source-derived fixture corrections. |
| C | Add v2 evidence/readers, preserve v1 | Catalog/semantic tests and model contract registration must travel with schema. Reader acceptance precedes HTTP v2 writes. |
| D | HTTP/media/Qwen, SQLite lifetime, existing server/settings composition | Runtime builder extraction, normalizer shared decoder, source preflight, explicit credentials, pypdf lock/package data and final defensive fixes. New offline config dependency must already exist when imported. |
| E | Dedicated Unix host and landing-only API | Host entrypoint and config/test patch seam; no backup entrypoint yet. |
| F | Filesystem publication and issuer-compatible exact authorization | Three delivery modules, contract, offline factory adapter, governance script, specific urllib.parse rule exception and grant regressions. |
| G | Backup/recovery and complete operational templates/docs | Requires F's lock/DB protocol and E's host config. Add backup entrypoint and installer only when their imported targets exist. |

The 13 source-only commits mix these units, so whole-commit cherry-picking is not a coherent split. Source path copying plus selected final shared-file hunks is required. Keep final parity checkpoints for architecture/system.yaml, architecture/rules.yaml, pyproject, retention/runtime, shared tests and docs: these are intentionally edited by multiple slices.

## Genuine new routes and exact predecessors

`scripts/grok_route.py` exposes task, --session, --show, --complete, --cancel and --json. It has no --base flag. It calls `build_route()` and stores a new active route. Runtime state lives under each worktree's `.grok-stack/runtime` (`util.runtime_dir()`), not the shared Git common directory; a new worktree therefore isolates runtime files as well as source edits.

`build_route()` at `.grok-stack/adaptive_grok/router.py:293` accepts `base_commit_override` and `base_fingerprint_override`. Its default base uses `git_default_base()` (`util.py:119`), which chooses origin/main before main and HEAD. Therefore simply invoking the CLI in a stacked child worktree does not automatically choose the preceding child commit.

For A at the actual current-main commit, normal CLI creation is correct:

```bash
python3 scripts/grok_route.py 'Implement L5 slice A: exact module boundary exceptions and baseline I/O inventory' --session l5-split-a --json
python3 scripts/grok_change.py start --title 'L5 slice A boundary enforcement'
python3 scripts/grok_status.py
```

For a genuinely stacked B-G worktree initially checked out at its exact predecessor, the existing Python API can create a fresh route bound to that predecessor. This is not mutation of the monolith route. Resolve and verify the predecessor before editing the child, use a distinct task/session, and preserve its natural tree fingerprint:

```python
from pathlib import Path
from adaptive_grok.router import build_route
from adaptive_grok.state import set_active_route
from adaptive_grok.util import git_head, tree_fingerprint

root = Path.cwd()
predecessor = git_head(root)  # Must equal the documented clean predecessor SHA.
route = build_route(
    root,
    'Implement L5 slice B: advance sealed source epoch and preserve retained layouts',
    'l5-split-b',
    base_commit_override=predecessor,
    base_fingerprint_override=tree_fingerprint(root),
)
set_active_route(root, route.to_dict())
```

Run with the checkout's `.grok-stack` on PYTHONPATH, then use `scripts/grok_change.py start`. `start_change()` creates a new package, canonical typed spec, route snapshot and draft state; it links the worktree's active route/change. Record predecessor, source freeze, selected path/hunk manifest and user-approved scope in that new package. Follow draft -> scoped -> approved -> implementing -> verifying -> reviewing -> ready only when each step is factually satisfied.

Do not call `update_route(base_commit=...)` on route `8632a3272f03`, copy its old receipts/grants, set source fingerprint artificially, or mark the old route complete to obtain a green child. New route role selection is authoritative: the parent reports that slice A's normally generated route `d20205a1a318` selected `integration_implementer`; use that selected sole writer, not the old route's general_implementer.

## Comparison and verification caveat

The new route base controls architecture fitness: `_architecture_check()` in verification.py:80-106 calls `select_architecture_comparison_base(route)` and evaluates that actual diff. The selector in architecture_diff.py:280 uses the exact route base when its architecture model exists. This permits a genuine child to measure its real predecessor diff without changing budgets.

Separately, `_git_range_selection()` in verification.py:374 considers both the route base and a locally selected PR target. `_select_local_pr_target()` prefers origin/HEAD, then configured/default main/master refs; it does not inspect a stacked GitHub PR's base branch or ordinary branch upstream. The changed-file inventory unions these ranges. This is a scope/inventory caveat, not proof that architecture fitness still uses the cumulative main range. Do not alter shared origin/HEAD or init.defaultBranch to disguise it. Document the actual PR target and inspect full verifier outputs for each genuine slice; once predecessors merge, the next base can be created normally from refreshed main.

Each slice needs focused regression checks, the prescribed `python3 scripts/grok_verify.py --mode pr`, route-selected independent reviews, current fingerprint-bound receipts and its own exact-head external Trust CI result. Existing monolith successes cannot be transferred. A later rebase or changed predecessor requires renewed evidence.

## Exact frozen delta manifest

The following rows are generated from `git diff --raw --abbrev=40 --no-renames BASE SOURCE`. Git blob IDs bind exact contents, modes bind executable status, and all-zero old IDs identify additions. The manifest includes archival documents as well as implementation so nothing is silently omitted from the source freeze. Classification P is implementation/configuration/contracts/tests; D is shared docs/handoff; H is the historical L5 change package.

```text
class status source-mode source-blob base-mode base-blob path
P M 100644 622069a4777125711bc7a8e0c879ad205e935dd5 100644 218becc002f2142b120d0740b1796c74118351c2 .grok-stack/adaptive_grok/architecture_fitness.py
D M 100644 34092775a7f4da93ef48534e45c6eda5e1a20a3e 100644 308080a7742d224c6eff7a1cbc5c6f2768544a58 PROJECT_STATE.json
D M 100644 4a1e9ca4d71bbbe2942ee327fbb5d2e6e48d3298 100644 b6f1b7cb7c51d56f3a2ba7b298823eddf3150ac9 README.md
D M 100644 65cc3fd261fe1ec71eff6580d2c2ea7d1c31c988 100644 de6d00c97ba13e4d2c02cf3492bbb34dc6b92cb8 START_HERE.md
P M 100644 1ac466a110a13c0913fe5043b727ddab29c7fb18 100644 b1390807acf0fd69f3cb58298ecb885e531173f3 architecture/rules.yaml
P M 100644 264a540c46cccb830b7f6edfd28fa8f6f38792c8 100644 337c5d99d28e5bf89d842d8d8a18bb7f6986b101 architecture/system.yaml
D M 100644 1e573ba28082846518cd520cf6aeb39a99b16694 100644 48730e36421f76d61b2d3c422a003092fbf86458 decisions.md
P A 100644 77296e30976fa5c11ebcb3876fac4f77eb0090d3 000000 0000000000000000000000000000000000000000 delivery/contracts/jsonschema/landing-publication-request.v1.schema.json
P A 100644 70b43abc0c55908286082a62fa9ca7c07a4d2a00 000000 0000000000000000000000000000000000000000 delivery/src/adaptive_delivery/landing_filesystem.py
P A 100644 1a4fbe0f129f7e5de2c5dac84043354c26a59807 000000 0000000000000000000000000000000000000000 delivery/src/adaptive_delivery/landing_publication.py
P A 100644 eba47143979c6a9f51d2320c90b113eee9df9d0b 000000 0000000000000000000000000000000000000000 delivery/src/adaptive_delivery/landing_publication_contracts.py
D A 100644 013973540e18f266c6da92ab46a9e82d9bdce542 000000 0000000000000000000000000000000000000000 docs/superpowers/plans/2026-09-12-l5-production-runtime.md
H A 100644 c6e0aacf2c1afce6bc57c760a7d1a798d33181c7 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/architecture-continuation-plan.md
H A 100644 0b5952e0ed99766ddba1f33d333097ef84abb45a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/architecture.md
H A 100644 254330a462867bb8135d95b38d620c47dc0046d2 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/brief.md
H A 100644 6ef066b72f042380f775eecce70006a493455090 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/change-spec.yaml
H A 100644 79cef33e3bc46ab0f24df3a1319b2e121871f0d8 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/README.md
H A 100644 54d3375e020530b2bd103108d3578bbcdb32e69d 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/analysis-architect.md
H A 100644 3f88b3dc88d6ba6c25e5f867b6fb3ebf82db4ab1 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/analysis-docs_researcher.md
H A 100644 91f9cdb61987c31b2353d30bc6a9fbe2fe0f5c1a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/analysis-integration_architect.md
H A 100644 cf86ee63152ef7c403695749974074939466488c 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/analysis-repo_explorer.md
H A 100644 3b47e4aa457a524390bf68c832958b8dc0fd2cf4 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/analysis-task_analyst.md
H A 100644 e99b17d28a1e27507df37a95bfe697a46bf6d08f 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-authority-identity-red.out
H A 100644 4ca3b20defa531cfd7e1b60960619ed735019ad2 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-authority-red.out
H A 100644 d320ede7bfb4f7ae3fe4bef33cd7de0fcfa97a73 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-boundary-red.out
H A 100644 54701cd2da20c7b4ee7cee8b5253938d881d1004 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-code-review.md
H A 100644 0e4d8b86451d382544a67accc1dbe715305bddbe 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-continuation-slice.json
H A 100644 e95f52cbedd4f43bc8b791c8f95d08c8ff5e378b 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-continuation-verification.md
H A 100644 6441119ed8d2a68dab710e99f6878462ae691ab9 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-core28-final.out
H A 100644 a8f6ce84c6baf6bf203ce8942f17de33b490d095 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-delivery28-verified.out
H A 100644 7e0f5ca875a81daed755a2f4f1acef3551c3cf22 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-evidence-v2-red.out
H A 100644 3942f303cd77fe042f974f85dcee9776a3cb906a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-factory28-verified.out
H A 100644 a76eceb09b1c378fc58e8feeeabc22f23369f50b 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-final-focused.out
H A 100644 f09c0ba3c307896842f523bc4043a2e915f0b2c9 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-frozen-source-complete.json
H A 100644 3eee197b3aba8d206e364d487fc4d8f182ab23ea 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-full-verifier-complete.json
H A 100644 560903a1786aa43bbc434fb254503ea7b3d54c31 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-implementation-report.md
H A 100644 18124cd4507ce5a1731b9945675c3d24807cfd74 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-io-inventory-red.out
H A 100644 07cb38b7f8e1f36365c2d9bd7d4ac53a6b424831 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-namespace-final-green.out
H A 100644 66d551d9b3d7ea152ce19de171e908cfbb88064a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-package-root-spoof-red.out
H A 100644 bb1893b6550927bdb9ebbf58e1f86a75320d3036 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-pr-complete-fitness.json
H A 100644 8c5313f128e3bd9bd41aa7556ca97f8dd4c376af 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-publication-alias-remote-red.out
H A 100644 412afb462a4f225b37497a1f770b6edae4800161 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-remote-double-suffix-red.out
H A 100644 852c348c059c61ed608eb6e6c6003b12cbba90ae 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-route-complete-fitness.json
H A 100644 8fdaa50050dcc714ec82deab151d952b26396979 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-schema-catalog-green.out
H A 100644 5085c6a7bc2e634f53ef68c11487a9b5dc9f4d1a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-test-review.md
H A 100644 87000be58b579797a12cd926a4a3532fee3a0539 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/architecture-verification-interrupted.json
H A 100644 a4e888400f8e53ff591cb1af670071caccf277dc 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-analysis-architect.md
H A 100644 0a2c77b5e4e0957f3165f3e9596e1f75e7c3e8d9 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-analysis-docs_researcher.md
H A 100644 58e9eb895c15233975b0831604c5458fa0f05e70 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-analysis-integration_architect.md
H A 100644 16a216cc5aee0f1e50c36c7d7ebf159630a89109 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-analysis-repo_explorer.md
H A 100644 89dde4b6548232acca148e6be4c1ebe0e6bead87 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-analysis-task_analyst.md
H A 100644 5f76e1662c98012e8d4db566aed62c72dc5e8713 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-boundary-design.md
H A 100644 f27e13d10343c1f6ddf39b6f40ffea36690ace6f 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-budget-analysis.md
H A 100644 0e32abba9b18241b3a08419501fef8c4a2ebac2a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-delivery-split-estimates.json
H A 100644 4a86b3a01ebcc8f66743ebd5c91ccf19f2c34301 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-delivery-split.md
H A 100644 5df7e8cdbebaf2879d8af5e747fc93685808f071 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-integration-analysis.md
H A 100644 976ce5fb1733b0df14510a13b45a37c09400c5f3 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-publication-alias-red.json
H A 100644 66fa65bbb3afecf47113188cafda873a6001dbb2 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/continuation-repo-analysis.md
H A 100644 24dbd0b85c5c175ea6bc2cb1972f69fb5e7ff175 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/executor-followup-analysis.md
H A 100644 05e0afcd5790ff0ebba60b1e552c4bc88059236f 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-code-review.md
H A 100644 5ba2808450908d47dece88e2c288295f837d5611 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-continuation-verification.md
H A 100644 ffd678c0038a0b349f1425d9cf6914989844b1db 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-coverage.json
H A 100644 4556f2eb9e6dd7edc7d5d35eb1466e729aa57f7a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-final-tests.txt
H A 100644 ff7938bb6c725a3fb106f99b9000cff529265832 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-fitness-followup.json
H A 100644 4f597639a1dfc98303618d6c89603f0df7430c98 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-full-verifier-before-followups.json
H A 100644 f839c97964a6b59949baa9b790e7e81bac603957 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-red-confirmed.txt
H A 100644 70ea14cea9377eb040380402d29064764209a9ec 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-slice-evidence.json
H A 100644 139f8983bd934851c7c4e78c2275bd0f301568af 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/host-test-review.md
H A 100644 c35f44bbc3a2281f8d973ac524c81c936609b917 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/implementation-progress.md
H A 100644 b3d77d7c461ec45db864522c698096292883cc53 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-analysis.md
H A 100644 ebd68a2acecb6af60a99c1c84214393bd3ca196c 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-code-review.md
H A 100644 f84c73e168404823d8e0de8e4af87f437922ef36 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-connector-focused28.out
H A 100644 2ed0c604dc8d2b0e1fa87d1afefd66beb1906d9c 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-connector-slice.json
H A 100644 db3357fa6fd6994d0aa56b4a82b693c1d2a581ab 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-factory28-final.out
H A 100644 7068ef1718ac7527eb1c5650559a30d31cd65e26 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-final-live-probe.json
H A 100644 ccac919624739547bebf77c7d6de204e50c4e41a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-live-probe.json
H A 100644 41d514b4576b0d52f3f0d3d92966bd0e70348647 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-region-green.out
H A 100644 d7f9098d5f561c96437be77eb64710b7ce7f84aa 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-region-red.out
H A 100644 7a2c14b64b316d6167af4cf15fadf4ca2866ee7a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/qwen-test-review.md
H A 100644 0de0cd531b1cf3f92771a957aafa38131313f98c 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-architecture-analysis.md
H A 100644 194898f010e27db5d85c3c559c80e95ed87352ec 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-backup-red-confirmed.out
H A 100644 8de8e4cdc3831e2696f78df21032c7c3fd4bdb3e 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-backup-red.out
H A 100644 2dba1537f1119d66d5698e992402756d74868581 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-code-review.md
H A 100644 f6ce7e8fa509cdddb45bb310b884c490aad06cf5 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-factory28-final.out
H A 100644 bf334fb9a8eb1a96d4bb6ea02c21c075b5fa91d6 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-final-live-probe.json
H A 100644 a7dd0c4e77091c84eccacf39b7a14bd3ab6598e6 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-first-four-green.out
H A 100644 b2cad1e42f45454a54d876d636974c7fa71e335e 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-full-verifier.json
H A 100644 93a49037a791c3bc3ca7c7024ea0c4f0baea65cd 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-harness-red.out
H A 100644 acf66138810bb6c6e60df9acbed1ae013646be38 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-pdf-docx-red-confirmed.out
H A 100644 6616eb485e3efe5548bd3c57f0e98ce9698b7713 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-pdf-docx-red.out
H A 100644 b888097e5601ece57acf4e0f5751b0e2b8056147 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-priority-slice.json
H A 100644 b33336f2b8dafd3b4f71e75e8631f3ae4a997092 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-priority-verification.md
H A 100644 cefed2f5e2936fd7bdf9bf0accaee39edb478b54 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-sse-unicode-red.out
H A 100644 13b76cd7c1bdcaf760fa8bcb1478fa2241176ae3 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-test-review.md
H A 100644 77f281bc03f79df3941674e66590bd61fd069c08 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/evidence/security-unicode-red.out
H A 100644 07f585470c5fcd40001be84966167722d97354f3 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/git-delivery.md
H A 100644 1c562f134053b32113077d27083f5b253392f631 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/host-continuation-plan.md
H A 100644 c568dfec90abf5ff7b0a1cde91b1dac76be89e4a 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/production-followup.md
H A 100644 8d5c4ca0cd1fc8a207ffb0172e5d93dfd702f1eb 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/pull-request-body.md
H A 100644 25c73e8f82e5c95ba07475f01441368dc570f6d2 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/qwen-connector-plan.md
H A 100644 dc585cb587a1dd158b44e5b3d74e4345f6b37ef4 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/release.md
H A 100644 2087688b78959a06799871882a7d2ffdad8bc0e8 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/requirements.md
H A 100644 6363289697b7a0a1020f03e3b897bc2f75ac8aa8 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/rollback.md
H A 100644 6f74e458d97e3c24d77b7e17e8e978e14a682b91 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/route.json
H A 100644 f3bc2dfba9bf832538bec245727b9598cb191938 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/security-priority-plan.md
H A 100644 de52a2fcec63d9b0f0101e5de5cbe57b0da28dce 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/six-point-continuation.md
H A 100644 d6e4e685c8c28b9d8ee2f59923398515d5354592 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/state.json
H A 100644 4a67dae7b681aece525d041b5bd5108b76c62bf5 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/tasks.md
H A 100644 c5fc6e654893c846de014aecb6a81229d32ef3c7 000000 0000000000000000000000000000000000000000 engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/test-plan.md
D A 100644 43c75c9ad05e6b728f13e8ad36a3b47e85ad7a46 000000 0000000000000000000000000000000000000000 engineering/runbooks/l5-filesystem-publication.md
D A 100644 f2b4ecccceba8e5375f86e27e557ac06afe19a0e 000000 0000000000000000000000000000000000000000 engineering/runbooks/l5-production-runtime.md
D M 100644 1cd19ad0fefa2fc69dcaf34fb759a07a5e41f238 100644 0dd5f8234c0005f5ff8747607524989f2ca04ff6 factory/README.md
P A 100644 ee40c1860df65aad00effcb12ed06aab169a415a 000000 0000000000000000000000000000000000000000 factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json
P M 100644 1470d1925f164425878923d8958792e765bc26f8 100644 f240635ec4f651bd739b43a3c47265d6955f3097 factory/pyproject.toml
P A 100644 ebf78186e934cad9f565fa8eddd3083063ec3ebe 000000 0000000000000000000000000000000000000000 factory/runtime/adaptive-l5.service.in
P A 100644 d8bcd8325addccde05edbad49d6b0f688b10e621 000000 0000000000000000000000000000000000000000 factory/runtime/install-claw.sh
P A 100644 46076857760ff2e5145a951e6209a99883bec777 000000 0000000000000000000000000000000000000000 factory/runtime/landing-host.example.json
P M 100644 21358680db1ba20160973b9a8b12b93625855380 100644 7621b6b75b26cc0de62e35ae74f571bce6b2bace factory/src/adaptive_factory/api.py
P M 100644 e7aad41d1f2f4aee8fa4163e6f6fbfddacb11b77 100644 7187c3e519841ec0a395666c1b3b8718348a1c71 factory/src/adaptive_factory/landing_artifact.py
P M 100644 b4d85b9accd00054076cd5a1027cede37075606d 100644 b9229acacee2b0f946d1ef523ecd6ec036470cec factory/src/adaptive_factory/landing_artifact_retention.py
P A 100644 bd7b42909512fde6b53382516d29adb19de0c1d5 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_backup.py
P M 100644 2409a1ef92d90e03d00740a9ca79b33695d64739 100644 1f5ebbd4b882e8bb76edead7d6062b6e8bfb65cc factory/src/adaptive_factory/landing_contracts.py
P M 100644 7535e4d10fc2d6cdfd4ebd4aeb4c8912cbe61994 100644 fe5b02759b5df6a10da55f72554eb3b4ab37ef02 factory/src/adaptive_factory/landing_evaluation.py
P A 100644 747ab6a6cc77b22dd481a445ca0fb647002de51e 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_host.py
P A 100644 b844bca2240c767d1e4a57a70dc4a54b2196f5a6 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_host_config.py
P A 100644 c8730a8ffcb65f003d4eae73ef4f3c9ad22bb41c 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_http.py
P M 100644 c50a638e545276b407c196f3ce23995038b28e62 100644 9bb595bcaf64b02e0d983687f3ed94efdb468528 factory/src/adaptive_factory/landing_intake.py
P M 100644 45f70c92cb2ae9ee33e2163e80707a12d45d1021 100644 a41501f1f123e9ecc6bd999e429eb751d39e34c5 factory/src/adaptive_factory/landing_live_executors.py
P A 100644 2f9e1d1e16df61410add428a3e4d7042274f49ec 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_media.py
P M 100644 600f646e4e0d4141667d2a540989f91c3cf20fbe 100644 ded63bdd55ebed1da6ffc7a559c623594af8871f factory/src/adaptive_factory/landing_normalizer.py
P M 100644 61b3b6f1ea1e6574a536a1cae605b8d045edfd72 100644 b33c87bd62778160dace9729edf29ddf67b50ded factory/src/adaptive_factory/landing_provider.py
P A 100644 d110abbf00ed2ca6995018c2e426adbf0b4fe3c1 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_publication_cli.py
P M 100644 bcf35122a71274093f48e599bc086a0d83b6dd3b 100644 541b5d1da82c02f09da1b3be803582efcf88dc89 factory/src/adaptive_factory/landing_renderer.py
P M 100644 1fadba9a1eb298b303dd0e5d2a53c3ed6ee8a664 100644 b388192e3142a953e1c431c64c663455e78d7b55 factory/src/adaptive_factory/landing_runtime.py
P A 100644 f4908c812c7212a5dbc3e6462839720401881da9 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_server.py
P M 100644 face482d20776fa44d7faeaed2940ed994edaf33 100644 4248af00578cf30c6dce03103f2466c848972d48 factory/src/adaptive_factory/landing_service.py
P M 100644 8bfbcc02b2218fb4192cad0351e0d559fe365019 100644 f6bee01b0847de5b6e1368214145f6342995165a factory/src/adaptive_factory/landing_sqlite_store.py
P A 100644 e6010225c29e9e9b30221e253d6303d04010e723 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/landing_sse.py
P A 100644 611c9cae0cb37633bf05a6d4f5e341fd6c61dffd 000000 0000000000000000000000000000000000000000 factory/src/adaptive_factory/resources/landing_pdf_worker.py
P M 100644 a4f08e80c7b22bf0dd1263129022edff02a497f3 100644 73d585f6bd5da85b835871f1f917b6170bbca4ce factory/src/adaptive_factory/server.py
P M 100644 37e11ca1057ca7188670aabf3b0283c3f860241b 100644 7b3f45468bc546799dd84153d92e2e6ad19fa0a7 factory/src/adaptive_factory/settings.py
P M 100644 7017c81dfe7030fa4b428ba0e0be22991886dbea 100644 d85175bd8849e9cd892758aa77d7deb58784c961 factory/tests/__init__.py
P M 100644 e2bd51971fa55fd5d7021837382732deb9bf322f 100644 6b7c83e8a60ec3cd4594a3f550da2d17f61adebe factory/tests/test_landing_api.py
P M 100644 63e470577fbaa17fc58b86b0d61303a583edb1f4 100644 c187807030ea65aae0d28b38ffa92ecaac401fc8 factory/tests/test_landing_artifact.py
P A 100644 a442229838ebcc64ea86524fc9a583dbfef7452c 000000 0000000000000000000000000000000000000000 factory/tests/test_landing_backup.py
P M 100644 7d5009f84a2de41079b591f285875fc26a201c7f 100644 0aeb8ac56c222e1e6d3f2e33c9f0225f3b2b634f factory/tests/test_landing_contracts.py
P A 100644 aceabde2a29222bcfa6a0546da82b2c2c2e17a75 000000 0000000000000000000000000000000000000000 factory/tests/test_landing_host.py
P M 100644 fc0c5df5bfb32cd18f7fb6652e4dd1abdcffaaf4 100644 df222672a350c8ebe4c511ff70826843a984b5b4 factory/tests/test_landing_live.py
P M 100644 088f7937b5ffa1a3e593da413a5d1109509398ed 100644 37bf77c6478a7fff943b38550ba81d07b776d610 factory/tests/test_landing_live_executors.py
P A 100644 ae6cfd56e4e9def06f30ebf02dc0dc48b99d79d3 000000 0000000000000000000000000000000000000000 factory/tests/test_landing_media.py
P M 100644 b3c7b78d375809ed052f14da348e3eb34f3846a8 100644 4e204c3e030e72257dd9733a329f3a5fcf1ef949 factory/tests/test_landing_normalizer.py
P A 100644 49e8c50f64987095cb1cb531561aa7032e9b68b8 000000 0000000000000000000000000000000000000000 factory/tests/test_landing_publication_cli.py
P M 100644 722a966ea75a8d32a60b2f4d759d6f5ad4834f56 100644 cf8270ea1f84b5db3f89978b0a3ed307b8c5ffec factory/tests/test_landing_renderer.py
P M 100644 15e0f33d9fbd18f9368c20d34d274dee0d62bc77 100644 7edad20d8bc27f10d1fb1c9e96974fda47aaaec9 factory/tests/test_landing_sqlite_store.py
P A 100644 098755d0f9a5e5659cdf1e06652701dd6bcad19a 000000 0000000000000000000000000000000000000000 factory/tests/test_landing_sse.py
P M 100644 a76a02298b25ceaf0f924c81082ab0a792e470b9 100644 b079e204a4b209103f55a32e3cda2fc216170382 factory/tests/test_semantic_bridge.py
P M 100644 563777238363c49ee2f87ead089cbd602d9264ee 100644 9420ab5b24675ad999cff943ece5c43f8bdd7d98 factory/tests/test_semantic_contracts.py
P M 100644 f64198f489ec7da0d29664010a37d12bbd2195ee 100644 f69494f9c11780091ef687385b8d5589e5dd82f2 factory/tests/test_server.py
P M 100644 960a957febe25461730c46366c492f1584394b85 100644 985c3f2c7188d9281056baa95882cf3ede47a0b1 factory/uv.lock
D M 100644 1aa556a945c7d1c4cc6eb83c2b2c71ea05f32ce5 100644 d16fbc91d748b44ada0d23f9ef8b7323ce168a3c mistakes.md
P M 100644 df813e5837b3cd9700dff0b82725c9c7d42f24ea 100644 4f703a7af55b4c8e4c8de7acdc45c17d96e7ff3a schemas/architecture-rules.schema.json
P A 100644 86a91bcfc4603c315bf808a15e799c9c2c576536 000000 0000000000000000000000000000000000000000 scripts/grok_landing_publish.py
P M 100644 7649ba9c5d55654f7cc05583ea8833eb1d7191cd 100644 dc32f2e38978ff93c235eb7dced068dd1b36ff61 tests/test_architecture_fitness.py
P M 100644 5bd53c70caf33070a9b1a171088015a94930df3b 100644 b8d22e980352e91bcfa14e40dc9dcc6d50b22c24 tests/test_architecture_model.py
P A 100644 207267f60b54e08bb9d4c803c4cc3a5b47415723 000000 0000000000000000000000000000000000000000 tests/test_landing_architecture_boundaries.py
```

Implementation projection: 59 sorted paths; canonical JSON SHA-256 `8370b2045bf110e1aebd5181af958e20261f6a895dd075365824a46401c0ed2a`. Keys per row: path, source_mode, source_blob; JSON uses sort_keys=True and separators=(comma, colon).

Durable fact: Actual-main-to-source parity excludes no unrelated product delta here, and the original trust-ci separation failure must not be reproduced by selecting the obsolete route base. New child routes bind genuine predecessors; exact source-blob parity and fresh child evidence are separate completion checks.
